from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QDialogButtonBox,
    QLabel, QLineEdit, QTextEdit, QRadioButton, QButtonGroup, QMessageBox
)

class SequenceEditorDialog2(QDialog):
    def __init__(self, rule_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Trigger/Response")
        self.setMinimumWidth(500)
        self._is_programmatically_changing = False
        rule_data = rule_data or {}

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Nom du trigger
        self.name_edit = QLineEdit(rule_data.get("name", ""))
        form_layout.addRow("1 -Trigger Name :", self.name_edit)

        # Mode du trigger (ASCII/HEX/Decimal)
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("2 - Trigger mode :"))
        self.radio_ascii = QRadioButton("ASCII")
        self.radio_hex = QRadioButton("HEX")
        self.radio_decimal = QRadioButton("Decimal")
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_ascii)
        self.mode_group.addButton(self.radio_hex)
        self.mode_group.addButton(self.radio_decimal)
        current_mode = rule_data.get("mode", "ASCII")
        if current_mode == "HEX":
            self.radio_hex.setChecked(True)
        elif current_mode == "Decimal":
            self.radio_decimal.setChecked(True)
        else:
            self.radio_ascii.setChecked(True)
        mode_layout.addWidget(self.radio_ascii)
        mode_layout.addWidget(self.radio_hex)
        mode_layout.addWidget(self.radio_decimal)
        mode_layout.addStretch()
        form_layout.addRow(mode_layout)

        # Valeur du trigger (QTextEdit)
        self.trigger_edit = QTextEdit(rule_data.get("trigger", ""))
        self.trigger_edit.setMinimumHeight(60)
        form_layout.addRow("3 - Trigger Value :", self.trigger_edit)

        # Réponse
        self.response_edit = QTextEdit(rule_data.get("reponse", ""))
        self.response_edit.setMinimumHeight(60)
        form_layout.addRow("4 - Response to send :", self.response_edit)

        # Mode de la réponse (ASCII/HEX/Decimal)
        resp_mode_layout = QHBoxLayout()
        resp_mode_layout.addWidget(QLabel("Mode of Response:"))
        self.resp_radio_ascii = QRadioButton("ASCII")
        self.resp_radio_hex = QRadioButton("HEX")
        self.resp_radio_decimal = QRadioButton("Decimal")
        self.resp_mode_group = QButtonGroup(self)
        self.resp_mode_group.addButton(self.resp_radio_ascii)
        self.resp_mode_group.addButton(self.resp_radio_hex)
        self.resp_mode_group.addButton(self.resp_radio_decimal)
        current_resp_mode = rule_data.get("response_mode", "ASCII")
        if current_resp_mode == "HEX":
            self.resp_radio_hex.setChecked(True)
        elif current_resp_mode == "Decimal":
            self.resp_radio_decimal.setChecked(True)
        else:
            self.resp_radio_ascii.setChecked(True)
        resp_mode_layout.addWidget(self.resp_radio_ascii)
        resp_mode_layout.addWidget(self.resp_radio_hex)
        resp_mode_layout.addWidget(self.resp_radio_decimal)
        resp_mode_layout.addStretch()
        form_layout.addRow(resp_mode_layout)

        main_layout.addLayout(form_layout)

        # Boutons OK/Annuler
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        # Validation dynamique du trigger et de la réponse
        self.trigger_edit.textChanged.connect(self.on_trigger_text_changed)
        self.mode_group.buttonClicked.connect(self.on_mode_changed)
        self.response_edit.textChanged.connect(self.on_response_text_changed)
        self.resp_mode_group.buttonClicked.connect(self.on_response_mode_changed)
        self.validate_current_trigger()
        self.validate_current_response()

    def get_mode(self):
        if self.radio_hex.isChecked(): return "HEX"
        if self.radio_decimal.isChecked(): return "Decimal"
        return "ASCII"
    def get_response_mode(self):
        if self.resp_radio_hex.isChecked(): return "HEX"
        if self.resp_radio_decimal.isChecked(): return "Decimal"
        return "ASCII"

    def on_mode_changed(self):
        self.validate_current_trigger()
    def on_trigger_text_changed(self):
        if self._is_programmatically_changing:
            return
        self.validate_current_trigger()
    def on_response_mode_changed(self):
        self.validate_current_response()
    def on_response_text_changed(self):
        if self._is_programmatically_changing:
            return
        self.validate_current_response()

    def validate_current_trigger(self):
        mode = self.get_mode()
        text = self.trigger_edit.toPlainText()
        if mode == "ASCII":
            self.set_valid_style(self.trigger_edit)
            return
        elif mode == "HEX":
            clean_text = "".join([c for c in text if c in "0123456789abcdefABCDEF "]).upper()
            clean_text = " ".join(clean_text.split())
            parts = clean_text.split()
            is_valid = all(len(p) <= 2 for p in parts)
            if is_valid:
                self.set_valid_style(self.trigger_edit)
            else:
                self.set_invalid_style(self.trigger_edit, "HEX values ​​must be 1 or 2 characters long.")
            no_space_text = clean_text.replace(" ", "")
            reformatted_text = " ".join(no_space_text[i:i+2] for i in range(0, len(no_space_text), 2))
            if reformatted_text != text:
                self.set_text_programmatically(self.trigger_edit, reformatted_text)
        elif mode == "Decimal":
            clean_text = "".join([c for c in text if c in "0123456789 "])
            clean_text = " ".join(clean_text.split())
            is_valid = True
            try:
                parts = clean_text.split()
                if parts:
                    is_valid = all(0 <= int(p) <= 255 for p in parts if p)
            except (ValueError, TypeError):
                is_valid = False
            if is_valid:
                self.set_valid_style(self.trigger_edit)
            else:
                self.set_invalid_style(self.trigger_edit, "Decimal values ​​must be between 0 and 255.")
            if clean_text != text:
                self.set_text_programmatically(self.trigger_edit, clean_text)

    def validate_current_response(self):
        mode = self.get_response_mode()
        text = self.response_edit.toPlainText()
        if mode == "ASCII":
            self.set_valid_style(self.response_edit)
            return
        elif mode == "HEX":
            clean_text = "".join([c for c in text if c in "0123456789abcdefABCDEF "]).upper()
            clean_text = " ".join(clean_text.split())
            parts = clean_text.split()
            is_valid = all(len(p) <= 2 for p in parts)
            if is_valid:
                self.set_valid_style(self.response_edit)
            else:
                self.set_invalid_style(self.response_edit, "HEX values ​​must be 1 or 2 characters long.")
            no_space_text = clean_text.replace(" ", "")
            reformatted_text = " ".join(no_space_text[i:i+2] for i in range(0, len(no_space_text), 2))
            if reformatted_text != text:
                self.set_text_programmatically(self.response_edit, reformatted_text)
        elif mode == "Decimal":
            clean_text = "".join([c for c in text if c in "0123456789 "])
            clean_text = " ".join(clean_text.split())
            is_valid = True
            try:
                parts = clean_text.split()
                if parts:
                    is_valid = all(0 <= int(p) <= 255 for p in parts if p)
            except (ValueError, TypeError):
                is_valid = False
            if is_valid:
                self.set_valid_style(self.response_edit)
            else:
                self.set_invalid_style(self.response_edit, "Decimal values ​​must be between 0 and 255.")
            if clean_text != text:
                self.set_text_programmatically(self.response_edit, clean_text)

    def set_text_programmatically(self, widget, text):
        self._is_programmatically_changing = True
        cursor = widget.textCursor()
        pos = cursor.position()
        widget.setPlainText(text)
        cursor.setPosition(min(pos, len(text)))
        widget.setTextCursor(cursor)
        self._is_programmatically_changing = False

    def set_valid_style(self, widget):
        widget.setToolTip("")
        widget.setStyleSheet("")
    def set_invalid_style(self, widget, tooltip_text):
        widget.setToolTip(tooltip_text)
        widget.setStyleSheet("border: 1px solid red;")

    def validate_and_accept(self):
        name = self.name_edit.text().strip()
        trigger = self.trigger_edit.toPlainText().strip()
        response = self.response_edit.toPlainText().strip()
        mode = self.get_mode()
        resp_mode = self.get_response_mode()
        if not name or not trigger or not response:
            QMessageBox.warning(self, "Required Fields", "The 'Name', 'Trigger' and 'Response' fields cannot be empty.")
            return
        self.validate_current_trigger()
        self.validate_current_response()
        if self.trigger_edit.toolTip():
            QMessageBox.warning(self, "Invalid Format", "The trigger contains an error. Please correct it.")
            return
        if self.response_edit.toolTip():
            QMessageBox.warning(self, "Invalid Format", "The trigger contains an error. Please correct it. Veuillez la corriger.")
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "trigger": self.trigger_edit.toPlainText().strip(),
            "mode": self.get_mode(),
            "response": self.response_edit.toPlainText().strip(),
            "response_mode": self.get_response_mode()
        }
