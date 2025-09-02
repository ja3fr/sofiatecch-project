# Fichier : main.py (version intégrée backend partagé + SettingsDialog)

import sys, json, codecs, time, re
from datetime import datetime

import serial, serial.tools.list_ports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QMessageBox, QLabel, QButtonGroup
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QTimer

# Affichage ANSI -> HTML (Terminal)
import ansi2html
from ansi2html import Ansi2HTMLConverter

# Modules locaux
from colors import Colors
from settings_dialog import SettingsDialog
from terminal_widget import TerminalWidget
from calibrator_widget import MenzuCalibratorPage   # IMPORTANT : fichier calibrator_widget.py
from serial_worker import SerialWorker
from scripting_dialog import ScriptingDialog
from serial_backend import SerialBackend            # backend partagé pour Calibrator


# ----------------------- Scripting -----------------------

class ScriptInterruptException(Exception):
    pass

class ScriptAPI(QObject):
    log_requested = pyqtSignal(str)
    send_data_requested = pyqtSignal(bytes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.runner = None

    def log(self, message):
        self.log_requested.emit(str(message))

    def send_raw(self, data_str):
        self.send_data_requested.emit(codecs.decode(data_str, 'unicode_escape').encode('latin-1'))

    def pause(self, milliseconds):
        if self.runner and not self.runner._is_running:
            raise ScriptInterruptException("Script stopped by the user.")
        end_time = time.time() + milliseconds / 1000.0
        while time.time() < end_time:
            if self.runner and not self.runner._is_running:
                raise ScriptInterruptException("Script stopped by the user.")
            time.sleep(0.02)

class ScriptRunner(QObject):
    finished = pyqtSignal()
    output_logged = pyqtSignal(str)

    def __init__(self, script_code, api, parent=None):
        super().__init__(parent)
        self.script_code = script_code
        self.api = api
        self._is_running = True

    def run(self):
        class StdoutInterceptor:
            def __init__(self, signal_emitter):
                self.signal_emitter = signal_emitter
            def write(self, text):
                self.signal_emitter.emit(text)
            def flush(self):
                pass

        old_stdout = sys.stdout
        sys.stdout = StdoutInterceptor(self.output_logged)
        self.api.runner = self
        try:
            exec(self.script_code, {'api': self.api, 'Colors': Colors})
        except ScriptInterruptException:
            pass
        except Exception as e:
            print(f"\nERROR IN SCRIPT:\n{e}")
        finally:
            self.api.runner = None
            sys.stdout = old_stdout
            self.finished.emit()

    def stop(self):
        self._is_running = False


# ----------------------- Application principale -----------------------

class SerialApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sophia-Tech Serial Terminal")
        self.setGeometry(200, 200, 1400, 700)

        # Etat série (Terminal)
        self.serial_settings = None      # dict retourné par SettingsDialog
        self.serial_port = None          # instance serial.Serial pour le Terminal
        self.serial_worker_thread = None
        self.serial_worker = None
        self.serial_buffer = b''

        # Backend série partagé pour le Calibrator (ne DOIT PAS ouvrir lui-même)
        self.backend = SerialBackend()

        # Affichage & scripting
        self.ansi_converter = Ansi2HTMLConverter(dark_bg=False, scheme="solarized")
        self.scripting_dialog = None
        self.script_thread = None
        self.script_runner = None
        self.terminal_display_mode = "ASCII"
        self.is_closing = False

        # File d'envoi (Terminal)
        self.send_queue = []
        self.send_timer = QTimer(self)
        self.send_timer.setInterval(100)
        self.send_timer.timeout.connect(self.process_send_queue)

        # Détection de flux RX pour séquencer TX
        self.is_receiving_data = False
        self.rx_timeout_timer = QTimer(self)
        self.rx_timeout_timer.setInterval(100)
        self.rx_timeout_timer.setSingleShot(True)
        self.rx_timeout_timer.timeout.connect(self._on_rx_stream_finished)

        # Buffer processing timer
        self.buffer_processing_timer = QTimer(self)
        self.buffer_processing_timer.setSingleShot(True)
        self.buffer_processing_timer.setInterval(5)
        self.buffer_processing_timer.timeout.connect(self.process_buffered_data)

        # UI
        self.setup_ui()
        self.connect_signals()
        self.update_status_bar()

    # ----------------------- UI -----------------------

    def setup_ui(self):
        self._setup_toolbar()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        nav = self._setup_navigation()
        main_layout.addLayout(nav)

        content_layout = self._setup_main_content()
        main_layout.addLayout(content_layout, stretch=1)

        self.status_bar_label = QLabel("No configuration. Please configure the port.")
        self.status_bar_label.setStyleSheet(
            "padding: 2px 5px; color: #555; background-color: #f0f0f0; border-top: 1px solid #ccc;"
        )
        main_layout.addWidget(self.status_bar_label)

    def _setup_toolbar(self):
        self.start_action = QAction(QIcon("icons/connect.png"), "Start", self)
        self.stop_action = QAction(QIcon("icons/disconnect.png"), "Stop", self)
        self.clear_action = QAction(QIcon("icons/clear.png"), "Clear", self)
        self.settings_action = QAction(QIcon("icons/settings.png"), "Config", self)
        self.scripting_action = QAction(QIcon("icons/script.png"), "Scripting", self)

        self.stop_action.setEnabled(False)

        tb = self.addToolBar("Main Toolbar")
        tb.addAction(self.start_action)
        tb.addAction(self.stop_action)
        tb.addSeparator()
        tb.addAction(self.clear_action)
        tb.addSeparator()
        tb.addAction(self.settings_action)
        tb.addAction(self.scripting_action)

    def _setup_navigation(self):
        layout = QHBoxLayout()
        self.btn_terminal = QPushButton("Terminal")
        self.btn_terminal.setObjectName("NavButton")
        self.btn_terminal.setCheckable(True)
        self.btn_calibrator = QPushButton("Calibrator")
        self.btn_calibrator.setObjectName("NavButton")
        self.btn_calibrator.setCheckable(True)

        self.nav_button_group = QButtonGroup(self)
        self.nav_button_group.setExclusive(True)
        self.nav_button_group.addButton(self.btn_terminal)
        self.nav_button_group.addButton(self.btn_calibrator)
        self.btn_terminal.setChecked(True)

        layout.addWidget(self.btn_terminal)
        layout.addWidget(self.btn_calibrator)
        layout.addStretch()
        return layout

    def _setup_main_content(self):
        layout = QVBoxLayout()
        self.stacked_widget = QStackedWidget()

        self.terminal_page = TerminalWidget()

        # Injecte le backend partagé au Calibrator (pas de boutons COM côté Calibrator)
        self.calibrator_page = MenzuCalibratorPage(backend=self.backend)

        self.stacked_widget.addWidget(self.terminal_page)
        self.stacked_widget.addWidget(self.calibrator_page)
        layout.addWidget(self.stacked_widget)
        return layout

    def connect_signals(self):
        # IMPORTANT : on passe par des handlers pour gérer la pause/reprise
        self.btn_terminal.clicked.connect(self.enter_terminal_mode)
        self.btn_calibrator.clicked.connect(self.enter_calibrator_mode)

        self.settings_action.triggered.connect(self.open_settings_dialog)
        self.clear_action.triggered.connect(self.terminal_page.clear_display)
        self.start_action.triggered.connect(self.start_communication)
        self.stop_action.triggered.connect(self.stop_communication)
        self.scripting_action.triggered.connect(self.open_scripting_dialog)

        self.terminal_page.send_data_to_serial.connect(self.write_to_serial)
        self.terminal_page.send_line_to_serial.connect(self.write_line_to_serial)
        self.terminal_page.display_mode_changed.connect(self._on_terminal_display_mode_changed)

    # ----------------------- Navigation : pause/reprise RX -----------------------

    def enter_calibrator_mode(self):
        self.stacked_widget.setCurrentIndex(1)

        # Mettre en pause le lecteur RX du Terminal
        if getattr(self, "serial_worker", None):
            try:
                self.serial_worker.pause(True)
            except Exception:
                pass

        # Partager physiquement le même port avec le backend du Calibrator
        self._attach_backend_to_terminal_port()

        # Rafraîchir le bandeau d'état du Calibrator si dispo
        try:
            self.calibrator_page._update_status_label()
        except Exception:
            pass

    def enter_terminal_mode(self):
        self.stacked_widget.setCurrentIndex(0)
        # Reprendre la lecture RX du Terminal
        if getattr(self, "serial_worker", None):
            try:
                self.serial_worker.pause(False)
            except Exception:
                pass

    # ----------------------- Helpers d’affichage -----------------------

    def _on_terminal_display_mode_changed(self, new_mode):
        self.terminal_display_mode = new_mode

    def log_message_to_terminal(self, message, prefix="", prefix_color="gray", is_html=False):
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S") + f".{now.microsecond // 1000:03d}"
        prefix_ansi = f"\033[1m[{prefix if prefix else '---'}] ->\033[0m "
        line_to_display = f"{timestamp} {prefix_ansi}{message}\n"
        self.terminal_page.append_ansi_text(line_to_display)

    # ----------------------- Envoi TX (Terminal) -----------------------

    def process_send_queue(self):
        if not self.send_queue or self.is_receiving_data:
            self.send_timer.stop()
            return

        item = self.send_queue.pop(0)

        if item['type'] == 'sequence':
            seq = item['data']
            mode = seq.get("mode", "ASCII")
            text = seq.get("sequence", "")
            try:
                if mode == "ASCII":
                    data = codecs.decode(text, 'unicode_escape').encode('latin-1')
                elif mode == "HEX":
                    data = bytes([int(p, 16) for p in text.replace("0x", "").split() if p])
                else:  # Decimal
                    data = bytes([int(p, 10) for p in text.split() if p])
                self.send_data(data, source_prefix="[TX]")
            except ValueError as e:
                QMessageBox.critical(self, "Format Error", f"Invalid sequence for {mode}.\n{e}")

        elif item['type'] == 'line':
            line = item['data']
            self.send_data((line + '\r\n').encode('latin-1'), source_prefix="[TX]")

        if not self.send_queue:
            self.send_timer.stop()

    def write_to_serial(self, sequence_data):
        self.send_queue.append({'type': 'sequence', 'data': sequence_data})
        if not self.send_timer.isActive():
            self.send_timer.start()

    def write_line_to_serial(self, text_line):
        self.send_queue.append({'type': 'line', 'data': text_line})
        if not self.send_timer.isActive():
            self.send_timer.start()

    def send_data(self, data_to_send: bytes, source_prefix="[TX]"):
        if not (self.serial_port and self.serial_port.is_open):
            QMessageBox.warning(self, "Not Connected", "Communication is not active.")
            return

        while self.is_receiving_data:
            QApplication.processEvents()
            time.sleep(0.01)

        try:
            self.serial_port.write(data_to_send)

            now = datetime.now()
            timestamp = now.strftime("%H:%M:%S") + f".{now.microsecond // 1000:03d}"
            prefix_ansi = "\033[1;35m[TX] ->\033[0m "  # magenta

            if self.terminal_display_mode == "ASCII":
                content = data_to_send.decode('latin-1', errors='replace').replace('\n', '\\n').replace('\r', '\\r')
                line = f"{timestamp} {prefix_ansi}{content}\n"
                self.terminal_page.append_ansi_text(line)
            elif self.terminal_display_mode == "HEX":
                content = data_to_send.hex(' ').upper()
                line = f"{timestamp} [TX] -> {content}\n"
                self.terminal_page.append_monospace_text(line)
            else:
                content = ' '.join(str(b) for b in data_to_send)
                line = f"{timestamp} [TX] -> {content}\n"
                self.terminal_page.append_monospace_text(line)

        except Exception as e:
            now = datetime.now()
            timestamp = now.strftime("%H:%M:%S") + f".{now.microsecond // 1000:03d}"
            self.terminal_page.append_monospace_text(f"{timestamp} [SEND ERROR] -> {e}\n")

    # ----------------------- RX Terminal -----------------------

    def _on_rx_stream_finished(self):
        self.is_receiving_data = False

    def update_terminal(self, data: bytes):
        self.is_receiving_data = True
        self.rx_timeout_timer.start()
        self.serial_buffer += data
        if not self.buffer_processing_timer.isActive():
            self.buffer_processing_timer.start()

    def process_buffered_data(self):
        for _ in range(100):
            if b'\n' not in self.serial_buffer:
                break
            line_bytes, self.serial_buffer = self.serial_buffer.split(b'\n', 1)
            line_with_newline = line_bytes + b'\n'

            if not line_bytes.strip():
                self.terminal_page.append_monospace_text("\n")
                continue

            now = datetime.now()
            timestamp = now.strftime("%H:%M:%S") + f".{now.microsecond // 1000:03d}"
            prefix_ansi = "\033[1;32m[RX] ->\033[0m "

            if self.terminal_display_mode == "ASCII":
                text = line_bytes.decode('utf-8', errors='replace')
                self.terminal_page.append_ansi_text(f"{timestamp} {prefix_ansi}{text}\n")
            elif self.terminal_display_mode == "HEX":
                content = line_bytes.hex(' ').upper()
                self.terminal_page.append_monospace_text(f"{timestamp} [RX] -> {content}\n")
            else:
                content = ' '.join(str(b) for b in line_bytes)
                self.terminal_page.append_monospace_text(f"{timestamp} [RX] -> {content}\n")

            # Auto-response manager (si défini côté TerminalWidget)
            resp = self.terminal_page.receive_manager.check_and_get_response(line_with_newline)
            if resp:
                self.write_auto_response(resp)

        if b'\n' in self.serial_buffer:
            self.buffer_processing_timer.start()

    def write_raw_data_to_serial(self, data: bytes):
        self.send_data(data, source_prefix="[SCRIPT-TX]")

    def write_auto_response(self, sequence_data):
        mode = sequence_data.get("mode", "ASCII")
        text = sequence_data.get("sequence", "")
        try:
            if mode == "ASCII":
                data = codecs.decode(text, 'unicode_escape').encode('latin-1')
            elif mode == "HEX":
                data = bytes([int(p, 16) for p in text.replace("0x", "").split() if p])
            else:
                data = bytes([int(p, 10) for p in text.split() if p])
            self.send_data(data, source_prefix="[AUTO-TX]")
        except ValueError as e:
            self.log_message_to_terminal(f"Invalid format for {mode}.\n{e}", prefix="[AUTO-TX ERROR]")

    # ----------------------- Scripting -----------------------

    def open_scripting_dialog(self):
        if not self.scripting_dialog:
            self.scripting_dialog = ScriptingDialog(self)
            self.scripting_dialog.run_script_requested.connect(self.run_script)
            self.scripting_dialog.stop_script_requested.connect(self.stop_script)
        self.scripting_dialog.show()
        self.scripting_dialog.activateWindow()

    def run_script(self, script_code):
        if not self.serial_port or not self.serial_port.is_open:
            QMessageBox.warning(self.scripting_dialog, "Not Connected", "Please start the communication.")
            self.scripting_dialog.on_script_finished()
            return

        self.script_thread = QThread()
        api = ScriptAPI()
        self.script_runner = ScriptRunner(script_code, api)
        self.script_runner.moveToThread(self.script_thread)
        api.log_requested.connect(lambda msg: self.log_message_to_terminal(msg, prefix="[SCRIPT]"))
        api.send_data_requested.connect(self.write_raw_data_to_serial)
        self.script_runner.output_logged.connect(self.scripting_dialog.append_to_output)
        self.script_runner.finished.connect(self.scripting_dialog.on_script_finished)
        self.script_runner.finished.connect(self.script_thread.quit)
        self.script_runner.finished.connect(self.script_runner.deleteLater)
        self.script_thread.finished.connect(self.script_thread.deleteLater)
        self.script_thread.started.connect(self.script_runner.run)
        self.script_thread.start()

    def stop_script(self):
        if self.scripting_dialog:
            self.scripting_dialog.on_script_stopped_manually()
        if hasattr(self, 'script_runner') and self.script_runner:
            self.script_runner.stop()

    # ----------------------- Start/Stop COM -----------------------

    def _attach_backend_to_terminal_port(self):
        """
        Branche le port ouvert du Terminal dans le backend partagé (Calibrator).
        Supporte à la fois:
          - backend.set_physical_serial(self.serial_port) si présent
          - ou l’affectation directe des attributs (fallback)
        """
        if not (self.serial_port and self.serial_port.is_open):
            return
        # Méthode dédiée ?
        if hasattr(self.backend, "set_physical_serial"):
            try:
                self.backend.set_physical_serial(self.serial_port)
                return
            except Exception:
                pass
        # Fallback : affecte les attributs attendus
        try:
            self.backend.ser = self.serial_port
            self.backend.port = self.serial_settings.get('port') if self.serial_settings else None
            if hasattr(self.backend, "baudrate") and self.serial_settings:
                self.backend.baudrate = self.serial_settings.get('baudrate')
        except Exception:
            pass

    def start_communication(self):
        if not self.serial_settings:
            QMessageBox.warning(self, "Config Required", "Please configure the port.")
            return
        try:
            self.serial_port = serial.Serial(**self.serial_settings, timeout=1)
            # Important : vider le buffer driver pour éviter une première ligne corrompue
            self.serial_port.reset_input_buffer()
        except serial.SerialException as e:
            QMessageBox.critical(self, "Error", f"Could not open port: {e}")
            return

        # Thread RX
        self.serial_buffer = b''
        self.serial_worker_thread = QThread()
        self.serial_worker = SerialWorker(self.serial_port)
        self.serial_worker.moveToThread(self.serial_worker_thread)
        self.serial_worker_thread.started.connect(self.serial_worker.run)
        self.serial_worker.data_received.connect(self.update_terminal)
        self.serial_worker.error_occurred.connect(self.handle_error)
        self.serial_worker.finished.connect(self.serial_worker_thread.quit)
        self.serial_worker.finished.connect(self.serial_worker.deleteLater)
        self.serial_worker_thread.finished.connect(self.serial_worker_thread.deleteLater)
        self.serial_worker_thread.start()

        # S'assurer que le worker n'est pas en pause
        if hasattr(self.serial_worker, "pause"):
            try:
                self.serial_worker.pause(False)
            except Exception:
                pass

        # UI
        self.start_action.setEnabled(False)
        self.settings_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self.log_message_to_terminal(f"Connection open on {self.serial_settings['port']}", prefix="---")
        self.update_status_bar(is_connected=True)

        # Branche le backend partagé du Calibrator sur CE port (une seule ouverture physique)
        self._attach_backend_to_terminal_port()

        # Mettre à jour le bandeau d'état du Calibrator
        try:
            self.calibrator_page._update_status_label()
        except Exception:
            pass

    def stop_communication(self):
        try:
            if self.serial_worker:
                self.serial_worker.stop()
            if self.serial_worker_thread and self.serial_worker_thread.isRunning():
                self.serial_worker_thread.quit()
                self.serial_worker_thread.wait(200)
        except RuntimeError:
            pass
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                if not self.is_closing:
                    self.log_message_to_terminal("Connection closed", prefix="---")
            self.start_action.setEnabled(True)
            self.settings_action.setEnabled(True)
            self.stop_action.setEnabled(False)
            if self.serial_settings:
                self.update_status_bar(is_connected=False)

            # Détache proprement le backend du Calibrator
            try:
                if hasattr(self.backend, "set_physical_serial"):
                    self.backend.set_physical_serial(None)
                else:
                    self.backend.ser = None
                    self.backend.port = None
            except Exception:
                pass

            # Mettre à jour le bandeau d'état du Calibrator
            try:
                self.calibrator_page._update_status_label()
            except Exception:
                pass

    def handle_error(self, message):
        self.log_message_to_terminal(message, prefix="COMM ERROR", prefix_color="red")
        self.stop_communication()

    # ----------------------- Settings / Status bar -----------------------

    def open_settings_dialog(self):
        available_ports = serial.tools.list_ports.comports()
        dialog = SettingsDialog(available_ports, current_settings=self.serial_settings, parent=self)
        if dialog.exec():
            s = dialog.get_settings()
            if s:
                self.serial_settings = s
                self.update_status_bar()

    def update_status_bar(self, is_connected=False):
        if not self.serial_settings:
            self.status_bar_label.setText("No configuration. Please configure the port.")
            self.status_bar_label.setStyleSheet(
                "padding: 2px 5px; color: #555; background-color: #f0f0f0; border-top: 1px solid #ccc;"
            )
            return

        st = self.serial_settings
        port = st.get('port')
        baud = st.get('baudrate')
        bytesize = st.get('bytesize')

        parity_map = {
            serial.PARITY_NONE: "N", serial.PARITY_EVEN: "E", serial.PARITY_ODD: "O",
            serial.PARITY_MARK: "M", serial.PARITY_SPACE: "S"
        }
        stop_map = {
            serial.STOPBITS_ONE: "1", serial.STOPBITS_ONE_POINT_FIVE: "1.5", serial.STOPBITS_TWO: "2"
        }

        parity = parity_map.get(st.get('parity'), '?')
        stopbits = stop_map.get(st.get('stopbits'), '?')
        text = f"{port}  |  {baud} bps  |  {bytesize}{parity}{stopbits}"

        if is_connected:
            self.status_bar_label.setText(f"Connected: {text}")
            self.status_bar_label.setStyleSheet(
                "padding: 2px 5px; color:#003300; background-color:#d4edda; "
                "border-top:1px solid #c3e6cb; font-weight:bold;"
            )
        else:
            self.status_bar_label.setText(f"Configured: {text}")
            self.status_bar_label.setStyleSheet(
                "padding: 2px 5px; color:#555; background-color:#f0f0f0; border-top:1px solid #ccc;"
            )

    # ----------------------- Fermeture -----------------------

    def closeEvent(self, event):
        self.is_closing = True
        try:
            self.stop_script()
        except Exception:
            pass
        self.stop_communication()
        try:
            if self.script_thread and self.script_thread.isRunning():
                self.script_thread.wait(250)
        except RuntimeError:
            pass
        event.accept()


# ----------------------- Entrée -----------------------

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        with open("style.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Warning: 'style.qss' file not found.")

    print("ansi2html version:", ansi2html.__version__)
    print("ansi2html file:", ansi2html.__file__)

    window = SerialApp()
    window.show()
    sys.exit(app.exec())
