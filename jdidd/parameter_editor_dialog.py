from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, QLabel,
    QLineEdit, QComboBox, QSpinBox, QCheckBox, QPushButton
)

class ParameterEditorDialog(QDialog):
    def __init__(self, protocol_data, parent=None):
        super().__init__(parent)
        
        self.protocol_data = protocol_data
        self.widgets = {} # Dictionnaire pour stocker nos widgets par 'id'

        # --- Configuration de la fenêtre ---
        self.setWindowTitle(f"Éditeur - {protocol_data['protocol_name']}")
        
        main_layout = QVBoxLayout(self)
        
        # Le QFormLayout est parfait pour les paires label-widget
        form_layout = QFormLayout()

        # --- Création dynamique des widgets ---
        for param in self.protocol_data['parameters']:
            param_id = param['id']
            param_label = param['label']
            param_type = param['type']
            
            # Créer le label
            label = QLabel(f"{param_label}:")
            widget = None

            # Choisir le widget approprié en fonction du type
            if param_type == "string":
                widget = QLineEdit()
            elif param_type == "password":
                widget = QLineEdit()
                widget.setEchoMode(QLineEdit.EchoMode.Password)
            elif param_type == "enum":
                widget = QComboBox()
                if "options" in param:
                    widget.addItems(param['options'])
            elif param_type == "range":
                widget = QSpinBox()
                # On essaie d'extraire les bornes depuis la chaîne "value"
                try:
                    range_str = param.get("value", "[0:100]").strip("[]")
                    min_val, max_val = map(int, range_str.split(':'))
                    widget.setRange(min_val, max_val)
                except:
                    widget.setRange(0, 9999) # Valeurs par défaut
            elif param_type == "boolean":
                widget = QCheckBox()
            elif param_type == "action":
                # Pour une action, un simple bouton suffit
                widget = QPushButton(param_label)
                # On pourrait connecter ce bouton à une fonction spécifique si nécessaire
            else:
                # Si un type est inconnu, on met un QLineEdit par défaut
                widget = QLineEdit()

            if widget:
                form_layout.addRow(label, widget)
                self.widgets[param_id] = widget

        main_layout.addLayout(form_layout)

        # --- Boutons OK et Annuler ---
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept) # connecte le signal "OK"
        button_box.rejected.connect(self.reject) # connecte le signal "Annuler"
        
        main_layout.addWidget(button_box)

    def get_values(self):
        """ Récupère les valeurs de tous les widgets et les retourne dans un dictionnaire. """
        values = {}
        for param_id, widget in self.widgets.items():
            if isinstance(widget, QLineEdit):
                values[param_id] = widget.text()
            elif isinstance(widget, QComboBox):
                values[param_id] = widget.currentText()
            elif isinstance(widget, QSpinBox):
                values[param_id] = widget.value()
            elif isinstance(widget, QCheckBox):
                values[param_id] = widget.isChecked()
            # Les boutons (actions) n'ont pas de valeur à retourner
            elif isinstance(widget, QPushButton):
                values[param_id] = "ACTION_TRIGGERED" # On peut mettre un placeholder
        return values