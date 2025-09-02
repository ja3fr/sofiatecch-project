# Fichier : settings_dialog.py (Avec mise à jour automatique et corrections)

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox, 
                             QPushButton, QDialogButtonBox, QLabel)
from PyQt6.QtCore import QTimer
import serial
import serial.tools.list_ports

class SettingsDialog(QDialog):
    def __init__(self, available_ports, current_settings=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Serial Port Configuration")
        self.setMinimumWidth(350)

        # NOUVEAU : Attribut pour mémoriser le port à sélectionner initialement
        self.initial_port_to_select = None
        self.current_port_devices = []

        # Layout principal et formulaire
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Widgets de configuration
        self.port_combo = QComboBox()
        self.baud_rate_combo = QComboBox()
        self.data_bits_combo = QComboBox()
        self.parity_combo = QComboBox()
        self.stop_bits_combo = QComboBox()

        # MODIFIÉ : Ajout des vitesses de transmission plus élevées
        self.baud_rate_combo.addItems([
            "9600", "19200", "38400", "57600", "115200", 
            "230400", "460800", "921600"
        ])
        self.data_bits_combo.addItems(["8", "7", "6", "5"])
        self.parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"])
        self.stop_bits_combo.addItems(["1", "1.5", "2"])

        # Ajout au formulaire
        form_layout.addRow(QLabel("Port:"), self.port_combo)
        form_layout.addRow(QLabel("Baud Rate:"), self.baud_rate_combo)
        form_layout.addRow(QLabel("Data Bits:"), self.data_bits_combo)
        form_layout.addRow(QLabel("Parity:"), self.parity_combo)
        form_layout.addRow(QLabel("Stop Bits:"), self.stop_bits_combo)
        main_layout.addLayout(form_layout)

        # Boutons OK et Annuler
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        # Charger les paramètres initiaux ou les valeurs par défaut
        if current_settings:
            self.load_initial_settings(current_settings)
        else:
            # MODIFIÉ : Définition complète des valeurs par défaut (8N1)
            self.baud_rate_combo.setCurrentText("115200")
            self.data_bits_combo.setCurrentText("8")
            self.parity_combo.setCurrentText("None")
            self.stop_bits_combo.setCurrentText("1")

        # Mise en place du QTimer pour la mise à jour automatique
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(2000)
        self.update_timer.timeout.connect(self.check_for_port_update)
        self.update_timer.start()

        # Lancement initial de la vérification des ports
        self.check_for_port_update()

    def populate_ports_list(self, ports):
        """Vide et remplit la QComboBox des ports, en restaurant la sélection."""
        # Sauvegarder la sélection actuelle pour essayer de la restaurer
        current_selection_data = self.port_combo.currentData()
        
        # Le port à sélectionner en priorité est celui passé à l'ouverture, sinon l'actuel
        port_to_select = self.initial_port_to_select or current_selection_data
        
        self.port_combo.clear()
        self.current_port_devices = [p.device for p in ports]

        if ports:
            for port in ports:
                self.port_combo.addItem(f"{port.device} - {port.description}", port.device)
            self.port_combo.setEnabled(True)
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
            
            # MODIFIÉ : Logique de restauration de la sélection améliorée
            if port_to_select:
                index_to_restore = self.port_combo.findData(port_to_select)
                if index_to_restore != -1:
                    self.port_combo.setCurrentIndex(index_to_restore)
        else:
            self.port_combo.addItem("No ports available")
            self.port_combo.setEnabled(False)
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            
        # On a utilisé le port initial, on le réinitialise pour ne pas forcer la sélection plus tard
        self.initial_port_to_select = None

    def check_for_port_update(self):
        """Vérifie si la liste des ports a changé et met à jour si nécessaire."""
        available_ports = serial.tools.list_ports.comports()
        available_devices = [p.device for p in available_ports]

        if set(available_devices) != set(self.current_port_devices):
            print("Port change detected. List updated.")
            self.populate_ports_list(available_ports)

    def closeEvent(self, event):
        """S'assure que le timer est arrêté lorsque la fenêtre se ferme."""
        self.update_timer.stop()
        super().closeEvent(event)

    def load_initial_settings(self, settings):
        """Pré-remplit les widgets avec les paramètres actuels."""
        # MODIFIÉ : Mémorise le port à sélectionner au lieu de ne rien faire (pass)
        self.initial_port_to_select = settings.get('port')

        self.baud_rate_combo.setCurrentText(str(settings.get('baudrate', '115200')))
        self.data_bits_combo.setCurrentText(str(settings.get('bytesize', 8)))
        parity_map = {serial.PARITY_NONE: "None", serial.PARITY_EVEN: "Even", serial.PARITY_ODD: "Odd", serial.PARITY_MARK: "Mark", serial.PARITY_SPACE: "Space"}
        self.parity_combo.setCurrentText(parity_map.get(settings.get('parity', serial.PARITY_NONE)))
        stop_bits_map = {serial.STOPBITS_ONE: "1", serial.STOPBITS_ONE_POINT_FIVE: "1.5", serial.STOPBITS_TWO: "2"}
        self.stop_bits_combo.setCurrentText(stop_bits_map.get(settings.get('stopbits', serial.STOPBITS_ONE)))

    def get_settings(self):
        """Retourne les paramètres de configuration sous forme de dictionnaire."""
        if not self.port_combo.isEnabled():
            return None
            
        parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD, "Mark": serial.PARITY_MARK, "Space": serial.PARITY_SPACE}
        stop_bits_map = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}

        return {
            'port': self.port_combo.currentData(),
            'baudrate': int(self.baud_rate_combo.currentText()),
            'bytesize': int(self.data_bits_combo.currentText()),
            'parity': parity_map[self.parity_combo.currentText()],
            'stopbits': stop_bits_map[self.stop_bits_combo.currentText()]
        }