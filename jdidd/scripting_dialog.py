# Fichier : scripting_dialog.py (Version avec barre d'outils et icônes)

import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QToolBar, QTextEdit, 
                             QGroupBox, QMessageBox, QFileDialog)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import pyqtSignal, QSize

class ScriptingDialog(QDialog):
    run_script_requested = pyqtSignal(str)
    stop_script_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Éditeur de Script")
        self.setGeometry(300, 300, 700, 600)
        self.current_file_path = None

        # --- Chargement des icônes ---
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icons_path = os.path.join(script_dir, "icons")
        self.icon_load = QIcon(os.path.join(icons_path, "upload.png"))
        self.icon_save = QIcon(os.path.join(icons_path, "save.png"))
        self.icon_play = QIcon(os.path.join(icons_path, "play.png"))
        self.icon_stop = QIcon(os.path.join(icons_path, "stop.png"))
        
        # --- Layout Principal ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        toolbar = self.setup_toolbar()
        main_layout.addWidget(toolbar)

        script_group = QGroupBox("Script Python")
        script_layout = QVBoxLayout(script_group)
        self.script_editor = QTextEdit()
        self.script_editor.setFontFamily("Consolas, Courier New, monospace")
        self.script_editor.setPlaceholderText("Écrivez votre script ici...\n\n# Exemple:\n# for i in range(5):\n#     api.log(f'Message {i+1}')\n#     api.send_raw('AT+CMD?\\n')\n#     api.pause(1000)")
        script_layout.addWidget(self.script_editor)
        main_layout.addWidget(script_group, stretch=2)

        output_group = QGroupBox("Sortie du Script")
        output_layout = QVBoxLayout(output_group)
        self.output_console = QTextEdit()
        self.output_console.setReadOnly(True)
        self.output_console.setFontFamily("Consolas, Courier New, monospace")
        output_layout.addWidget(self.output_console)
        main_layout.addWidget(output_group, stretch=1)

        self.stop_action.setEnabled(False)

    def setup_toolbar(self):
        toolbar = QToolBar("Barre d'outils du script")
        toolbar.setIconSize(QSize(24, 24))

        self.load_action = QAction(self.icon_load, "Charger un script...", self)
        self.save_action = QAction(self.icon_save, "Sauvegarder le script...", self)
        self.run_action = QAction(self.icon_play, "Exécuter le script", self)
        self.stop_action = QAction(self.icon_stop, "Arrêter le script", self)
        
        self.load_action.triggered.connect(self.load_script)
        self.save_action.triggered.connect(self.save_script)
        self.run_action.triggered.connect(self.on_run_clicked)
        self.stop_action.triggered.connect(self.stop_script_requested.emit)

        toolbar.addAction(self.load_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.run_action)
        toolbar.addAction(self.stop_action)
        return toolbar

    def on_run_clicked(self):
        script_code = self.script_editor.toPlainText()
        if not script_code.strip():
            QMessageBox.warning(self, "Script Vide", "L'éditeur de script est vide.")
            return
        
        self.output_console.clear()
        self.set_running_state(True)
        self.run_script_requested.emit(script_code)

    def set_running_state(self, is_running):
        self.run_action.setEnabled(not is_running)
        self.load_action.setEnabled(not is_running)
        self.save_action.setEnabled(not is_running)
        self.stop_action.setEnabled(is_running)

    def load_script(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scripts_path = os.path.join(script_dir, "scripts")
        os.makedirs(scripts_path, exist_ok=True) # Crée le dossier s'il n'existe pas

        # 2. On utilise ce chemin comme dossier de départ
        path, _ = QFileDialog.getOpenFileName(self, "Load a Script", scripts_path, "Python Files (*.py);;All Files (*)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.script_editor.setPlainText(f.read())
                self.current_file_path = path
                self.setWindowTitle(f"Éditeur de Script - {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur de Lecture", f"Impossible de lire le fichier :\n{e}")

    def save_script(self):
        path = self.current_file_path
        if not path:
             script_dir = os.path.dirname(os.path.abspath(__file__))
             scripts_path = os.path.join(script_dir, "scripts")
             os.makedirs(scripts_path, exist_ok=True) # Crée le dossier s'il n'existe pas

             # 2. On utilise ce chemin comme dossier de départ
             path, _ = QFileDialog.getSaveFileName(self, "Save the Script", scripts_path, "Python Files (*.py);;All Files (*)")
        
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.script_editor.toPlainText())
                self.current_file_path = path
                self.setWindowTitle(f"Éditeur de Script - {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur de Sauvegarde", f"Impossible de sauvegarder le fichier :\n{e}")

    def on_script_finished(self):
        self.set_running_state(False)

    def on_script_stopped_manually(self):
        self.set_running_state(False)
        self.append_to_output("\n--- Script arrêté par l'utilisateur ---")

    def append_to_output(self, text):
        self.output_console.moveCursor(self.output_console.textCursor().MoveOperation.End)
        self.output_console.insertPlainText(text)