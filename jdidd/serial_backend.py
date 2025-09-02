# serial_backend.py
from __future__ import annotations
import time

try:
    import serial
    import serial.tools.list_ports
    from serial.serialutil import SerialException
except Exception:  # pyserial non installé
    serial = None
    SerialException = Exception


class SerialBackend:
    """
    Backend série minimal et robuste.
    - Ne crée PAS de port automatiquement.
    - Peut recevoir un port ouvert depuis l'app (self.ser = serial.Serial(...)).
    - Fournit connect_with_settings() si on veut connecter depuis ici.
    - do_get/do_set envoient une séquence "cd / ; cd <path> ; get/set ; cd /".
    """

    # Mappage module UI -> chemin shell embarqué
    MODULE_PATHS = {
        "LoRaWAN": "svc/net/lora",
        "LoRaWAN_at": "svc/net/lora",
        "LoRaWAN_AT": "svc/net/lora",
        "NVM": "svc/nvm",
        "SYS": "svc/sys",
        "GPS": "svc/gps",
        "GPRS / GSM": "svc/net/gprs",
        "GSM": "svc/net/gprs",
        "MODBUS_Master": "svc/net/modbus/master",
        "MODBUS_Slave": "svc/net/modbus/slave",
        "ZigBee": "svc/net/zigbee",
    }

    def __init__(self, default_baud: int = 115200, timeout: float = 1.0) -> None:
        self.ser = None           # type: ignore  # sera un serial.Serial
        self.port = None          # ex: "COM20"
        self.baudrate = default_baud
        self.timeout = timeout

    # --------------------- état & services ---------------------
    def is_connected(self) -> bool:
        return bool(self.ser) and getattr(self.ser, "is_open", False)

    @staticmethod
    def available_ports() -> list[str]:
        if serial is None:
            return []
        return [p.device for p in serial.tools.list_ports.comports()]

    # --------------------- connexion (optionnelle) ---------------------
    def connect_with_settings(self, settings: dict) -> bool:
        """
        settings attend:
          {'port','baudrate','bytesize','parity','stopbits'}
        """
        if serial is None:
            print("[SerialBackend] pyserial absent -> OFFLINE")
            return False
        try:
            self.ser = serial.Serial(
                port=settings["port"],
                baudrate=settings.get("baudrate", self.baudrate),
                bytesize=settings.get("bytesize", 8),
                parity=settings.get("parity", "N"),
                stopbits=settings.get("stopbits", 1),
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            self.port = settings["port"]
            self.baudrate = settings.get("baudrate", self.baudrate)
            time.sleep(0.2)
            return True
        except (SerialException, OSError, FileNotFoundError) as e:
            print(f"[SerialBackend] connect_with_settings error: {e}")
            self.ser = None
            self.port = None
            return False

    def disconnect(self) -> None:
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.port = None

    # --------------------- bas niveau ---------------------
    def _write_line(self, line: str) -> None:
        if not self.is_connected():
            return
        if not line.endswith("\n"):
            line += "\n"
        self.ser.write(line.replace("\n", "\r\n").encode("utf-8"))
        self.ser.flush()

    def _drain_until_idle(self, idle_ms: int = 120, max_ms: int = 1500) -> str:
        if not self.is_connected():
            return ""
        start = time.time()
        last = start
        buf = bytearray()
        while True:
            chunk = self.ser.read(4096)
            if chunk:
                buf.extend(chunk)
                last = time.time()
            else:
                if (time.time() - last) * 1000 >= idle_ms:
                    break
            if (time.time() - start) * 1000 >= max_ms:
                break
        try:
            return buf.decode("utf-8", errors="replace")
        except Exception:
            return buf.decode("latin1", errors="replace")

    def _exec_sequence(self, lines: list[str]) -> str:
        if not self.is_connected():
            return "[OFFLINE] Aucun port série connecté"
        out = []
        for ln in lines:
            self._write_line(ln)
            time.sleep(0.05)
            out.append(self._drain_until_idle())
        return "".join(out).strip()

    def _module_path(self, module: str) -> str:
        return self.MODULE_PATHS.get((module or "").strip(), "")
    

    def _extract_value_from_chunk(self, chunk: str) -> str:
   
     for ln in chunk.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("user@") or s.startswith("root@") or s.startswith("root/"):
            continue
        # ignore l'echo 'get KEY' éventuel
        if s.lower().startswith("get "):
            continue
        return s
     return chunk.strip()


    # --------------------- API GET/SET ---------------------
    def do_get(self, module: str, key: str) -> str:
        path = self._module_path(module)
        if not path:
            return f"[ERREUR] Chemin inconnu pour module '{module}'"
        if not self.is_connected():
            return "[OFFLINE] GET ignoré (aucun port connecté)"

        # Étapes séparées pour ne pas 'écraser' la valeur par le prompt final
        self._write_line("cd /")
        self._drain_until_idle()
        self._write_line(f"cd {path}")
        self._drain_until_idle()

        # <- la vraie lecture utile
        self._write_line(f"get {key}")
        chunk = self._drain_until_idle(idle_ms=250, max_ms=3000)
        value = self._extract_value_from_chunk(chunk)

        # On retourne à la racine, mais on ignore cette sortie
        self._write_line("cd /")
        self._drain_until_idle()

        return value


    def do_set(self, module: str, key: str, value: str) -> str:
        path = self._module_path(module)
        if not path:
            return f"[ERREUR] Chemin inconnu pour module '{module}'"
        if not self.is_connected():
            return "[OFFLINE] SET ignoré (aucun port connecté)"

        cmd = f"set {key}" if (value is None or str(value) == "") else f"set {key} {value}"

        self._write_line("cd /")
        self._drain_until_idle()
        self._write_line(f"cd {path}")
        self._drain_until_idle()

        self._write_line(cmd)
        chunk = self._drain_until_idle(idle_ms=250, max_ms=3000)
        resp = self._extract_value_from_chunk(chunk)

        self._write_line("cd /")
        self._drain_until_idle()

        return resp

