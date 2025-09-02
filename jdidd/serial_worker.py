# Fichier : serial_worker.py

import time
import serial
from PyQt6.QtCore import QObject, pyqtSignal

class SerialWorker(QObject):
    """
    Worker tournant dans un thread séparé pour lire le port série.
    Il communique via des signaux (pas d'accès direct à l'UI).
    """

    data_received = pyqtSignal(bytes)   # données RX
    error_occurred = pyqtSignal(str)    # erreur côté série
    finished = pyqtSignal()             # fin du thread

    def __init__(self, serial_port):
        super().__init__()
        self.serial_port = serial_port      # objet pyserial.Serial déjà ouvert
        self._is_running = True             # contrôle d'arrêt
        self._paused = False                # <-- AJOUT : lecture en pause

    # ------------ AJOUT ---------------
    def pause(self, flag: bool) -> None:
        """Met en pause (True) ou reprend (False) la lecture RX sans fermer le port."""
        self._paused = bool(flag)
    # ----------------------------------

    def run(self):
        """Boucle principale de lecture tant que _is_running est True."""
        try:
            while self._is_running:
                # Port fermé ? -> Stop
                if not self.serial_port or not self.serial_port.is_open:
                    self.error_occurred.emit("Le port série a été fermé inopinément.")
                    break

                # Si en pause, ne rien lire (laisser le CPU respirer)
                if self._paused:
                    time.sleep(0.02)
                    continue

                try:
                    # Lire tout ce qui est dispo
                    n = self.serial_port.in_waiting
                    if n > 0:
                        data = self.serial_port.read(n)
                        if data:
                            self.data_received.emit(data)
                    else:
                        time.sleep(0.01)  # éviter 100% CPU
                except serial.SerialException as e:
                    self.error_occurred.emit(f"Erreur de lecture du port série : {e}")
                    break
        finally:
            self.finished.emit()

    def stop(self):
        """Demande l'arrêt du worker."""
        self._is_running = False
