# Fichier: sequence_editor_dialog.py (Avec validation de format avancée)

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QDialogButtonBox,
    QLabel, QLineEdit, QTextEdit, QRadioButton, QButtonGroup, QMessageBox
)
from PyQt6.QtGui import QPalette

class SequenceEditorDialog(QDialog):
    def __init__(self, sequence_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Send Sequence")
        self.setMinimumWidth(500)
        self._is_programmatically_changing = False

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit(sequence_data.get("name", ""))
        form_layout.addRow("1 - Nom :", self.name_edit)
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("2 - Séquence   Edit Mode:"))
        self.radio_ascii = QRadioButton("ASCII")
        self.radio_hex = QRadioButton("HEX")
        self.radio_decimal = QRadioButton("Decimal")
        # Le binaire est plus complexe à valider, on le laisse pour plus tard si besoin
        # self.radio_binary = QRadioButton("Binary")
        
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_ascii)
        self.mode_group.addButton(self.radio_hex)
        self.mode_group.addButton(self.radio_decimal)
        
        current_mode = sequence_data.get("mode", "ASCII")
        if current_mode == "HEX": self.radio_hex.setChecked(True)
        elif current_mode == "Decimal": self.radio_decimal.setChecked(True)
        else: self.radio_ascii.setChecked(True)

        mode_layout.addWidget(self.radio_ascii)
        mode_layout.addWidget(self.radio_hex)
        mode_layout.addWidget(self.radio_decimal)
        mode_layout.addStretch()
        
        self.sequence_text_edit = QTextEdit(sequence_data.get("sequence", ""))
        self.sequence_text_edit.setMinimumHeight(100)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)

        main_layout.addLayout(form_layout)
        main_layout.addLayout(mode_layout)
        main_layout.addWidget(self.sequence_text_edit)
        main_layout.addWidget(buttons)
        
        # --- Connexions pour la validation ---
        self.sequence_text_edit.textChanged.connect(self.on_text_changed)
        self.mode_group.buttonClicked.connect(self.on_mode_changed)

        # Valider le texte initial
        self.validate_current_text()

    def get_current_mode(self):
        if self.radio_hex.isChecked(): return "HEX"
        if self.radio_decimal.isChecked(): return "Decimal"
        return "ASCII"

    def on_mode_changed(self):
        self.validate_current_text()

    def on_text_changed(self):
        if self._is_programmatically_changing:
            return
        self.validate_current_text()

    def validate_current_text(self):
        """Fonction maîtresse qui valide et reformate le texte."""
        mode = self.get_current_mode()
        text = self.sequence_text_edit.toPlainText()
        
        if mode == "ASCII":
            # Pas de validation pour l'ASCII, on s'assure juste que le style est normal
            self.set_valid_style()
            return

        elif mode == "HEX":
            # Enlever tous les caractères non-hexadécimaux (sauf l'espace)
            clean_text = "".join([c for c in text if c in "0123456789abcdefABCDEF "]).upper()
            # Enlever les espaces multiples
            clean_text = " ".join(clean_text.split())
            
            # Vérifier la validité de chaque partie
            parts = clean_text.split()
            is_valid = all(len(p) <= 2 for p in parts)

            if is_valid:
                self.set_valid_style()
            else:
                self.set_invalid_style("HEX values ​​must be 1 or 2 characters long.")

            # Reformatage automatique
            # On enlève les espaces pour travailler
            no_space_text = clean_text.replace(" ", "")
            # On regroupe par 2 et on joint avec un espace
            reformatted_text = " ".join(no_space_text[i:i+2] for i in range(0, len(no_space_text), 2))
            
            if reformatted_text != text:
                self.set_text_programmatically(reformatted_text)

        elif mode == "Decimal":
            # Enlever tous les caractères non-décimaux (sauf l'espace)
            clean_text = "".join([c for c in text if c in "0123456789 "])
            clean_text = " ".join(clean_text.split())

            # Vérifier la validité de chaque partie
            is_valid = True
            try:
                parts = clean_text.split()
                if parts: # S'il y a des nombres
                    is_valid = all(0 <= int(p) <= 255 for p in parts if p)
            except (ValueError, TypeError):
                is_valid = False

            if is_valid:
                self.set_valid_style()
            else:
                self.set_invalid_style("Decimal values ​​must be between 0 and 255.")
            
            if clean_text != text:
                self.set_text_programmatically(clean_text)

    def set_text_programmatically(self, text):
        """Met à jour le texte et gère le curseur et les signaux."""
        self._is_programmatically_changing = True
        cursor = self.sequence_text_edit.textCursor()
        pos = cursor.position()
        self.sequence_text_edit.setPlainText(text)
        cursor.setPosition(min(pos, len(text)))
        self.sequence_text_edit.setTextCursor(cursor)
        self._is_programmatically_changing = False

    def set_valid_style(self):
        """Réinitialise le style du champ de texte à son état normal."""
        self.sequence_text_edit.setToolTip("")
        self.sequence_text_edit.setStyleSheet("")

    def set_invalid_style(self, tooltip_text):
        """Applique un style d'erreur au champ de texte."""
        self.sequence_text_edit.setToolTip(tooltip_text)
        self.sequence_text_edit.setStyleSheet("border: 1px solid red;")

    def validate_and_accept(self):
        name = self.name_edit.text().strip()
        sequence = self.sequence_text_edit.toPlainText().strip()
        if not name or not sequence:
            QMessageBox.warning(self, "Required Fields", "The 'Name' and 'Sequence' fields cannot be empty.")
            return
        
        # Dernière validation avant de fermer
        self.validate_current_text()
        if self.sequence_text_edit.toolTip(): # Si un tooltip d'erreur est présent
             QMessageBox.warning(self, "Invalid Format", "The sequence contains an error. Please correct it.")
             return

        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text(),
            "sequence": self.sequence_text_edit.toPlainText(),
            "mode": self.get_current_mode()
        }