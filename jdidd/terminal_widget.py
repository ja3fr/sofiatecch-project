# Fichier : terminal_widget.py (Version Finale avec Tableaux Interactifs et Correction)

import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QPushButton, QLabel, 
    QMessageBox, QMenu, QButtonGroup, QTableWidget, QTableWidgetItem, 
    QHeaderView, QFileDialog, QToolBar, QTextEdit, QAbstractItemView, QPlainTextEdit, QLineEdit
)
from PyQt6.QtCore import pyqtSignal, Qt, QObject, QSize
from PyQt6.QtGui import QFont, QTextCursor, QIcon, QAction, QTextCharFormat, QColor

import re

ANSI_COLOR_MAP = {
    30: QColor("#000000"),  # Noir
    31: QColor("#c91b00"),  # Rouge
    32: QColor("#00c200"),  # Vert
    33: QColor("#c7c400"),  # Jaune
    34: QColor("#2222ee"),  # Bleu
    35: QColor("#c930c7"),  # Magenta
    36: QColor("#00c5c7"),  # Cyan
    37: QColor("#c7c7c7"),  # Gris clair
    90: QColor("#686868"),  # Gris foncé
    91: QColor("#ff6c60"),  # Rouge vif
    92: QColor("#a8ff60"),  # Vert vif
    93: QColor("#ffffb6"),  # Jaune vif
    94: QColor("#96cbfe"),  # Bleu vif
    95: QColor("#ff73fd"),  # Magenta vif
    96: QColor("#5ffdff"),  # Cyan vif
    97: QColor("#ffffff"),  # Blanc
}

ANSI_RE = re.compile(r'\x1b\[([0-9;]*)m')

def append_ansi_text(self, text):
    import re
    from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor

    # Définition de la map de couleurs...
    ANSI_COLOR_MAP = {
        30: QColor("#000000"), 31: QColor("#c91b00"), 32: QColor("#00c200"),
        33: QColor("#c7c400"), 34: QColor("#2222ee"), 35: QColor("#c930c7"),
        36: QColor("#00c5c7"), 37: QColor("#c7c7c7"), 90: QColor("#686868"),
        91: QColor("#ff6c60"), 92: QColor("#a8ff60"), 93: QColor("#ffffb6"),
        94: QColor("#96cbfe"), 95: QColor("#ff73fd"), 96: QColor("#5ffdff"),
        97: QColor("#ffffff"),
    }

    cursor = self.terminal_display.textCursor()
    
    # <<< LA CORRECTION CLÉ EST ICI
    # Déplace le curseur à la toute fin du document.
    # Cela annule toute sélection et garantit que l'insertion se fera en mode "append".
    cursor.movePosition(QTextCursor.MoveOperation.End)

    # Création du format par défaut
    fmt = QTextCharFormat()
    fmt.setFont(QFont("Consolas"))
    fmt.setForeground(QColor("#c7c7c7")) # Une couleur par défaut plus visible comme gris clair

    pos = 0
    # La boucle de traitement reste identique, elle était déjà correcte.
    for match in re.finditer(r'\x1b\[([0-9;]*)m', text):
        start, end = match.span()
        if start > pos:
            # Maintenant, cette insertion se fait au bon endroit (à la fin)
            cursor.insertText(text[pos:start], fmt)
        
        codes = match.group(1).split(';')
        if not any(codes) or codes == ['']: # Gère le cas de réinitialisation simple `\x1b[m`
            codes = ['0']
            
        for code_str in codes:
            if not code_str: continue
            code = int(code_str)
            if code == 0:  # Reset
                fmt = QTextCharFormat()
                fmt.setFont(QFont("Consolas"))
                fmt.setForeground(QColor("#c7c7c7"))
            elif code in ANSI_COLOR_MAP:
                fmt.setForeground(ANSI_COLOR_MAP[code])
            elif code == 1:
                fmt.setFontWeight(QFont.Weight.Bold)
        pos = end
        
    # Insère le reste du texte après la dernière séquence ANSI
    cursor.insertText(text[pos:], fmt)
    
    # Pas besoin de setTextCursor, car les opérations modifient déjà le document.
    # Il suffit de s'assurer que la vue est correcte.
    self.terminal_display.ensureCursorVisible()

from sequence_editor_dialog import SequenceEditorDialog
from receive_sequence_manager import ReceiveSequenceManager
from send_sequence_manager import SendSequenceManager
from SequenceEditorDialog2 import SequenceEditorDialog2

class TerminalWidget(QWidget):
    send_data_to_serial = pyqtSignal(dict)
    display_mode_changed = pyqtSignal(str)
    send_line_to_serial = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.receive_manager = ReceiveSequenceManager()
        self.send_manager = SendSequenceManager()
        
        # --- Chargement des icônes ---
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icons_path = os.path.join(script_dir, "icons")
        self.icon_lock_open = QIcon(os.path.join(icons_path, "lock_open.png"))
        self.icon_lock_closed = QIcon(os.path.join(icons_path, "lock_closed.png"))
        self.icon_add = QIcon(os.path.join(icons_path, "add.png"))
        self.icon_upload = QIcon(os.path.join(icons_path, "upload.png"))
        self.icon_save = QIcon(os.path.join(icons_path, "save.png"))
        self.icon_send = QIcon(os.path.join(icons_path, "send.png"))
        
        # --- Layout Principal ---
        main_layout = QHBoxLayout(self)
        left_panel = QVBoxLayout()
        main_layout.addLayout(left_panel, stretch=1)
        self.setup_send_sequences_panel(left_panel)
        self.setup_receive_sequences_panel(left_panel)
        
        terminal_groupbox = QGroupBox("Terminal")
        main_layout.addWidget(terminal_groupbox, stretch=2)
        terminal_layout = QVBoxLayout(terminal_groupbox)
        
        format_selector_layout = QHBoxLayout()
        self.mode_button_group = QButtonGroup(self)
        self.btn_ascii = QPushButton("ASCII")
        self.btn_hex = QPushButton("HEX")
        self.btn_decimal = QPushButton("Decimal")
        for btn in [self.btn_ascii, self.btn_hex, self.btn_decimal]:
            btn.setCheckable(True)
            format_selector_layout.addWidget(btn)
            self.mode_button_group.addButton(btn)
        self.btn_ascii.setChecked(True)
        format_selector_layout.addStretch()
        terminal_layout.addLayout(format_selector_layout)
        
        # --- DÉBUT DE LA MODIFICATION POUR L'INTERACTIVITÉ ---
        
        # 1. Le QTextEdit sert maintenant uniquement à l'affichage.
        self.terminal_display = QTextEdit()
        self.terminal_display.setObjectName("TerminalDisplay")
        self.terminal_display.setReadOnly(True)
        
        font = QFont("Consolas", 10) # On définit une police pour la réutiliser
        self.terminal_display.setFont(font)
        
        # 2. On ajoute un QLineEdit pour la saisie utilisateur.
        self.input_line = QLineEdit()
        self.input_line.setObjectName("TerminalInput") # Pour pouvoir le styler en QSS
        self.input_line.setFont(font) # On utilise la même police
        self.input_line.setPlaceholderText("Enter command here and press Enter...")
        
        # On ajoute l'afficheur (qui prendra le plus de place) et le champ de saisie en bas.
        terminal_layout.addWidget(self.terminal_display, stretch=1)
        terminal_layout.addWidget(self.input_line, stretch=0)
        
        # --- FIN DE LA MODIFICATION POUR L'INTERACTIVITÉ ---
        
        self.connect_signals()
        self.refresh_triggers_list()
        self.refresh_send_sequences_list()
    def create_file_toolbar(self, new_slot, load_slot, save_slot):
        toolbar = QToolBar(); toolbar.setIconSize(QSize(20, 20))
        new_action = QAction(self.icon_add, "New", self); new_action.triggered.connect(new_slot)
        load_action = QAction(self.icon_upload, "Upload", self); load_action.triggered.connect(load_slot)
        save_action = QAction(self.icon_save, "Save", self); save_action.triggered.connect(save_slot)
        toolbar.addAction(new_action); toolbar.addAction(load_action); toolbar.addAction(save_action)
        return toolbar
    def append_ansi_text(self, text):
        """
    Ajoute du texte contenant des codes ANSI au terminal.
    Version finale qui gère les couleurs de texte (foreground), de fond (background)
    et le style (gras), même lorsqu'ils sont combinés.
    """
        import re
        from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor

    # Map pour les couleurs de TEXTE (foreground)
        ANSI_FG_COLOR_MAP = {
            30: QColor("#000000"), 31: QColor("#c91b00"), 32: QColor("#00c200"),
            33: QColor("#c7c400"), 34: QColor("#2222ee"), 35: QColor("#c930c7"),
            36: QColor("#00c5c7"), 37: QColor("#c7c7c7"), 90: QColor("#686868"),
            91: QColor("#ff6c60"), 92: QColor("#a8ff60"), 93: QColor("#ffffb6"),
            94: QColor("#96cbfe"), 95: QColor("#ff73fd"), 96: QColor("#5ffdff"),
            97: QColor("#ffffff"),
        }
    
    # --- AJOUT : Map pour les couleurs d'ARRIÈRE-PLAN (background) ---
        ANSI_BG_COLOR_MAP = {
            40: QColor("#000000"), 41: QColor("#c91b00"), 42: QColor("#00c200"),
            43: QColor("#c7c400"), 44: QColor("#2222ee"), 45: QColor("#c930c7"),
            46: QColor("#00c5c7"), 47: QColor("#c7c7c7"), 100: QColor("#686868"),
            101: QColor("#ff6c60"), 102: QColor("#a8ff60"), 103: QColor("#ffffb6"),
            104: QColor("#96cbfe"), 105: QColor("#ff73fd"), 106: QColor("#5ffdff"),
            107: QColor("#ffffff"),
        }

        cursor = self.terminal_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Fonction pour créer un format par défaut propre
        def create_default_format():
            fmt = QTextCharFormat()
            fmt.setFont(QFont("Consolas"))
        # Couleur du texte par défaut
            fmt.setForeground(QColor("#c7c7c7")) 
        # Couleur du fond par défaut (celle du widget lui-même)
            fmt.setBackground(self.terminal_display.palette().base().color())
            return fmt

        current_format = create_default_format()
    
        pos = 0
        for match in re.finditer(r'\x1b\[([0-9;]*)m', text):
            start, end = match.span()
        
            if start > pos:
                cursor.insertText(text[pos:start], current_format)
                
            codes = match.group(1).split(';')
            if not any(codes) or codes == ['']: # Gère le cas de `\x1b[m`
                codes = ['0']
            
            for code_str in codes:
                if not code_str: continue
                code = int(code_str)

            # --- LOGIQUE DE TRAITEMENT AMÉLIORÉE ---
                if code == 0:  # Reset
                # Réinitialise TOUT au format par défaut
                    current_format = create_default_format()
                elif code == 1: # Gras
                    current_format.setFontWeight(QFont.Weight.Bold)
                elif code in ANSI_FG_COLOR_MAP: # Couleur du texte
                    current_format.setForeground(ANSI_FG_COLOR_MAP[code])
                elif code in ANSI_BG_COLOR_MAP: # Couleur du fond
                    current_format.setBackground(ANSI_BG_COLOR_MAP[code])
            
            pos = end
        
        cursor.insertText(text[pos:], current_format)
    
        self.terminal_display.ensureCursorVisible()


    def setup_send_sequences_panel(self, parent_layout):
        groupbox = QGroupBox("Send Sequences")
        parent_layout.addWidget(groupbox)
        layout = QVBoxLayout(groupbox)
        layout.setSpacing(8)
        self.send_toolbar = self.create_file_toolbar(self.new_send_sequences, self.load_send_sequences, self.save_send_sequences)
        self.send_file_label = QLabel("No files loaded")
        self.send_file_label.setStyleSheet("font-style: italic; color: gray;")
        self.add_sequence_btn = QPushButton("Add a Sequence")
        self.send_sequences_table = QTableWidget()
        self.send_sequences_table.setColumnCount(2)
        self.send_sequences_table.setHorizontalHeaderLabels(["Name", "Sequence"])
        self.send_sequences_table.verticalHeader().setVisible(False)
        self.send_sequences_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        self.send_sequences_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.send_sequences_table.setDragEnabled(True)
        self.send_sequences_table.setAcceptDrops(True)
        self.send_sequences_table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.send_sequences_table.setDragDropOverwriteMode(False)
        
        header = self.send_sequences_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # header.setStretchLastSection(True) # <-- CORRECTION : Ligne supprimée

        layout.addWidget(self.send_toolbar)
        layout.addWidget(self.send_file_label)
        layout.addWidget(self.add_sequence_btn)
        layout.addWidget(self.send_sequences_table)

    def setup_receive_sequences_panel(self, parent_layout):
        groupbox = QGroupBox("Receive Sequences")
        parent_layout.addWidget(groupbox)
        layout = QVBoxLayout(groupbox)
        layout.setSpacing(8)
        self.receive_toolbar = self.create_file_toolbar(self.new_triggers, self.load_triggers, self.save_triggers)
        self.receive_file_label = QLabel("No files loaded")
        self.receive_file_label.setStyleSheet("font-style: italic; color: gray;")
        self.add_trigger_btn = QPushButton("Add a Trigger")
        self.triggers_table = QTableWidget()
        self.triggers_table.setColumnCount(4)

        # --- CORRECTION MAJEURE ICI ---
        # L'en-tête doit avoir un premier élément vide pour la colonne du bouton
        self.triggers_table.setHorizontalHeaderLabels(["Active", "Name", "Trigger", "Answer"])
        
        self.triggers_table.verticalHeader().setVisible(False)
        self.triggers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.triggers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.triggers_table.setDragEnabled(True)
        self.triggers_table.setAcceptDrops(True)
        self.triggers_table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.triggers_table.setDragDropOverwriteMode(False)

        header = self.triggers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        


        layout.addWidget(self.receive_toolbar)
        layout.addWidget(self.receive_file_label)
        layout.addWidget(self.add_trigger_btn)
        layout.addWidget(self.triggers_table)

    def connect_signals(self):
        self.add_sequence_btn.clicked.connect(self.add_new_sequence)
        self.send_sequences_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.send_sequences_table.customContextMenuRequested.connect(self.show_context_menu)
        self.send_sequences_table.itemDoubleClicked.connect(self.edit_sequence)
        
        self.add_trigger_btn.clicked.connect(self.add_new_trigger)
        self.triggers_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.triggers_table.customContextMenuRequested.connect(self.show_context_menu)
        self.triggers_table.itemDoubleClicked.connect(self.edit_trigger)
        
        self.mode_button_group.buttonClicked.connect(self._on_display_mode_changed)

        self.send_sequences_table.model().rowsMoved.connect(
            lambda p, start, end, dest, row: self.handle_rows_moved(
                self.send_manager, start, row
            )
        )
        self.triggers_table.model().rowsMoved.connect(
            lambda p, start, end, dest, row: self.handle_rows_moved(
                self.receive_manager, start, row
            )
        )
        self.input_line.returnPressed.connect(self.on_input_line_enter)

    def handle_rows_moved(self, manager, source_row, dest_row):
        """
        Gère le déplacement d'une ligne dans le modèle de données sous-jacent.
        """
        # La destination peut être l'index APRES la fin de la liste.
        if dest_row > source_row:
            dest_row -= 1
        
        # --- CORRECTION : Utiliser les bonnes méthodes de manager ---
        if manager == self.send_manager:
            data_list = manager.get_sequences()
        else:
            data_list = manager.get_rules()

        # Récupérer l'élément déplacé et le retirer de sa position d'origine
        moved_item = data_list.pop(source_row)
        # Insérer l'élément à sa nouvelle position
        data_list.insert(dest_row, moved_item)

        # Rafraîchir l'affichage pour garantir la cohérence
        if manager == self.send_manager:
            self.refresh_send_sequences_list()
        else:
            self.refresh_triggers_list()


    def new_send_sequences(self): self.send_manager.new_set(); self.send_file_label.setText("New file (unsaved)"); self.refresh_send_sequences_list()
    def load_send_sequences(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Send Sequences", "send_sequences", "Fichiers JSON (*.json)");
        if path and self.send_manager.load_from_file(path): self.send_file_label.setText(os.path.basename(path)); self.refresh_send_sequences_list()
    def save_send_sequences(self):
        path = self.send_manager.current_file_path
        if not path: path, _ = QFileDialog.getSaveFileName(self, "Save Send Sequences", "send_sequences", "Fichiers JSON (*.json)");
        if path and self.send_manager.save_to_file(path): self.send_file_label.setText(os.path.basename(path))

    def new_triggers(self): self.receive_manager.new_set(); self.receive_file_label.setText("New file (unsaved)"); self.refresh_triggers_list()
    def load_triggers(self):
        path, _ = QFileDialog.getOpenFileName(self, "Charger Triggers", "receive_sequences", "Fichiers JSON (*.json)");
        if path and self.receive_manager.load_from_file(path): self.receive_file_label.setText(os.path.basename(path)); self.refresh_triggers_list()
    def save_triggers(self):
        path = self.receive_manager.current_file_path
        if not path: path, _ = QFileDialog.getSaveFileName(self, "Save Triggers", "receive_sequences", "Fichiers JSON (*.json)");
        if path and self.receive_manager.save_to_file(path): self.receive_file_label.setText(os.path.basename(path))

    def _on_display_mode_changed(self, button): self.display_mode_changed.emit(button.text())
    
    def refresh_send_sequences_list(self):
        self.send_sequences_table.setSortingEnabled(False)
        self.send_sequences_table.blockSignals(True)
        self.send_sequences_table.setRowCount(0)
        
        for i, data in enumerate(self.send_manager.get_sequences()):
            row_position = self.send_sequences_table.rowCount()
            self.send_sequences_table.insertRow(row_position)
            
            # --- DÉBUT DE LA MODIFICATION ---
            # Remplacer le bouton texte par un bouton avec une icône
            send_button = QPushButton()
            send_button.setIcon(self.icon_send)             # Utilise l'icône chargée dans __init__
            send_button.setToolTip("Send this sequence")# Ajoute une aide visuelle au survol
            send_button.setFlat(True)                       # Pour un design plus moderne
            send_button.setIconSize(QSize(20, 20))          # Taille de l'icône cohérente
            
            # La connexion du signal reste la même
            send_button.clicked.connect(lambda checked, d=data: self.send_data_to_serial.emit(d))
            self.send_sequences_table.setCellWidget(row_position, 0, send_button)
            # --- FIN DE LA MODIFICATION ---
            
            self.send_sequences_table.setItem(row_position, 1, QTableWidgetItem(data.get('name', '')))
            self.send_sequences_table.setItem(row_position, 2, QTableWidgetItem(data.get('sequence', '')))
            
        self.send_sequences_table.blockSignals(False)
        self.send_sequences_table.setSortingEnabled(True)

    def refresh_triggers_list(self):
        self.triggers_table.setSortingEnabled(False)
        self.triggers_table.blockSignals(True); self.triggers_table.setRowCount(0)
        for i, rule in enumerate(self.receive_manager.get_rules()):
            row_position = self.triggers_table.rowCount(); self.triggers_table.insertRow(row_position)
            lock_button = QPushButton(); lock_button.setFlat(True); is_enabled = rule.get('enabled', True); lock_button.setIcon(self.icon_lock_open if is_enabled else self.icon_lock_closed); lock_button.clicked.connect(lambda checked, r=i: self.toggle_trigger_state(r))
            self.triggers_table.setCellWidget(row_position, 0, lock_button)
            self.triggers_table.setItem(row_position, 1, QTableWidgetItem(rule.get('name', ''))); self.triggers_table.setItem(row_position, 2, QTableWidgetItem(rule.get('trigger', ''))); self.triggers_table.setItem(row_position, 3, QTableWidgetItem(rule.get('response', '')))
        self.triggers_table.blockSignals(False)
        self.triggers_table.setSortingEnabled(True)
    
    def add_new_sequence(self):
        dialog = SequenceEditorDialog({}, self);
        if dialog.exec(): new_data = dialog.get_data(); self.send_manager.add_sequence(new_data); self.refresh_send_sequences_list()
    def edit_sequence(self, item):
        row_index = item.row(); sequence_data = self.send_manager.get_sequences()[row_index]; dialog = SequenceEditorDialog(sequence_data, self);
        if dialog.exec(): new_data = dialog.get_data(); self.send_manager.edit_sequence(row_index, new_data); self.refresh_send_sequences_list()
    def add_new_trigger(self):
        dialog = SequenceEditorDialog2(parent=self);
        if dialog.exec(): rule = dialog.get_data(); rule['enabled'] = True; self.receive_manager.add_rule(rule); self.refresh_triggers_list()
    def edit_trigger(self, item):
        row_index = item.row(); rule = self.receive_manager.get_rules()[row_index]; dialog = SequenceEditorDialog2(rule, self);
        if dialog.exec(): new_rule = dialog.get_data(); new_rule['enabled'] = rule.get('enabled', True); self.receive_manager.edit_rule(row_index, new_rule); self.refresh_triggers_list()
        
    def show_context_menu(self, pos):
        sender_table = self.sender(); item = sender_table.itemAt(pos)
        if not item: return
        menu = QMenu(self); edit_action = menu.addAction("To modify"); delete_action = menu.addAction("DELETE")
        if sender_table is self.triggers_table:
            row_index = item.row(); rule = self.receive_manager.get_rules()[row_index]; is_enabled = rule.get('enabled', True)
            toggle_action = QAction("Disable" if is_enabled else "Enable", self); menu.insertAction(edit_action, toggle_action); menu.insertSeparator(edit_action)
            toggle_action.triggered.connect(lambda: self.toggle_trigger_state(row_index))
        action = menu.exec(sender_table.mapToGlobal(pos))
        if action == edit_action:
            if sender_table is self.send_sequences_table: self.edit_sequence(item)
            else: self.edit_trigger(item)
        elif action == delete_action:
            if sender_table is self.send_sequences_table: self.delete_sequence(item)
            else: self.delete_trigger(item)
            
    def delete_sequence(self, item):
        row_index = item.row(); name = self.send_manager.get_sequences()[row_index].get('name', 'Sequence without a name');
        reply = QMessageBox.question(self, "Confirmation", f"Delete sequence'{name}' ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes: self.send_manager.delete_sequence(row_index); self.refresh_send_sequences_list()
    def delete_trigger(self, item):
        row_index = item.row(); rule = self.receive_manager.get_rules()[row_index]; name = rule.get('name', '').strip() or 'Unnamed Trigger';
        reply = QMessageBox.question(self, "Confirmation", f"Delete trigger '{name}' ?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes: self.receive_manager.delete_rule(row_index); self.refresh_triggers_list()
        
    def toggle_trigger_state(self, row_index):
        rules = self.receive_manager.get_rules();
        if 0 <= row_index < len(rules):
            rules[row_index]['enabled'] = not rules[row_index].get('enabled', True); self.receive_manager.save_current_file(); self.refresh_triggers_list()
    
# Dans le fichier terminal_widget.py, à la fin de la classe TerminalWidget

        def append_html(self, html_fragment):
            print("DEBUG: --> 2")
            """
            Ajoute du HTML au terminal de manière intelligente :
            - Si l'utilisateur regarde la fin, on fait défiler.
            - Si l'utilisateur a scrollé ou sélectionné du texte, on ne le dérange pas.
            """
            # On récupère la barre de défilement
            scrollbar = self.terminal_display.verticalScrollBar()
            
            # On regarde si l'utilisateur est TOUT EN BAS avant de faire des changements.
            # On se donne une petite marge pour être sûr.
            scroll_est_en_bas = (scrollbar.value() >= scrollbar.maximum() - 5)

            # La méthode .append() gère tout automatiquement :
            # - Elle va à la fin.
            # - Elle insère le texte.
            # - Elle ajoute un saut de ligne.
            # - ELLE NE DÉTRUIT PAS LA SÉLECTION si la vue n'est pas à la fin.
            self.terminal_display.append(html_fragment)
            
            # On fait défiler vers le bas UNIQUEMENT si l'utilisateur était déjà en bas
            if scroll_est_en_bas:
                scrollbar.setValue(scrollbar.maximum())
    def clear_display(self):
        self.terminal_display.clear()
   
    def append_monospace_text(self, text):
        """Ajoute du texte simple avec la police monospace à la fin du terminal."""
        from PyQt6.QtGui import QTextCharFormat, QFont, QTextCursor

    # 1. Obtenir le curseur
        cursor = self.terminal_display.textCursor()
    
    # 2. Le déplacer à la fin (la correction essentielle)
        cursor.movePosition(QTextCursor.MoveOperation.End)
    
    # 3. Préparer le format du texte
        fmt = QTextCharFormat()
        fmt.setFont(QFont("Consolas"))
    
    # 4. Insérer le texte
        cursor.insertText(text, fmt)
    
    # 5. S'assurer que la vue défile
        self.terminal_display.ensureCursorVisible()

    def on_input_line_enter(self):
        """Appelée quand l'utilisateur appuie sur Entrée."""
        line_text = self.input_line.text()
        if line_text:
            # On émet le signal avec le texte à envoyer
            self.send_line_to_serial.emit(line_text)
            # On vide le champ de saisie pour la prochaine commande
            self.input_line.clear()    
   