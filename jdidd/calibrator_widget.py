# -*- coding: utf-8 -*-
# Fichier : calibrator_widget.py

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Iterable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QTextEdit, QScrollArea, QGroupBox, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt

# ========================= Modèle & utilitaires =========================

@dataclass
class ParamDef:
    label: str
    ptype: str            # "text" | "choice"
    access: str           # "get" | "set" | "getset"
    choices: Optional[Dict[str, str]] = None  # pour type="choice"


def _load_json_raw(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_schema(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retourne un dict du type:
      { "cartes": { <carte>: { <module>: { <param>: meta_dict }}}}
    Essaie d'accepter quelques variantes (“boards”, “cards”).
    """
    if isinstance(raw, dict) and "cartes" in raw and isinstance(raw["cartes"], dict):
        return raw
    for alt in ("boards", "cards"):
        if isinstance(raw, dict) and alt in raw and isinstance(raw[alt], dict):
            return {"cartes": raw[alt]}
    if isinstance(raw, dict) and raw and all(isinstance(v, dict) for v in raw.values()):
        return {"cartes": raw}
    raise ValueError("Schéma JSON non reconnu (clé 'cartes' absente ou invalide).")


def load_config_any(json_path: Optional[str]) -> Dict[str, Any]:
    """
    Essaie successivement:
      1) json_path si fourni
      2) CWD:  mcu_database.json  puis menzu_config.json
      3) ICI:  mcu_database.json  puis menzu_config.json
    Normalise et renvoie un dict avec 'cartes'.
    """
    tried: list[str] = []
    candidates: list[str] = []

    if json_path:
        candidates.append(json_path)

    here = os.path.dirname(__file__)
    for bn in ("mcu_database.json", "menzu_config.json"):
        candidates.append(os.path.join(os.getcwd(), bn))
        candidates.append(os.path.join(here, bn))

    for p in candidates:
        if os.path.exists(p):
            try:
                raw = _load_json_raw(p)
                data = _normalize_schema(raw)
                data["_loaded_from"] = p
                return data
            except Exception as e:
                tried.append(f"{p} -> {e}")

    detail = "\n  - " + "\n  - ".join(tried) if tried else ""
    raise FileNotFoundError(
        "Impossible de charger un JSON valide parmi mcu_database.json / menzu_config.json."
        + detail
    )


# ============================ ParamRow =============================

class ParamRow(QWidget):
    """
    Une ligne paramètre: label + input + boutons GET/SET.
    Tout est loggé dans la console.
    """

    def __init__(
        self,
        module_name: str,
        key: str,
        pdef: ParamDef,
        backend: Any,              # instance SerialBackend (injectée ou locale)
        console: QTextEdit,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.module = module_name
        self.key = key
        self.pdef = pdef
        self.backend = backend
        self.console = console

        grid = QGridLayout(self)
        grid.setContentsMargins(4, 2, 4, 2)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        # Label
        self.lbl = QLabel(pdef.label or key)
        self.lbl.setToolTip(f"{self.module}.{self.key} ({self.pdef.access})")
        grid.addWidget(self.lbl, 0, 0)

        # Input
        if pdef.ptype == "choice" and pdef.choices:
            self.input_widget = QComboBox()

            def sort_key(k: str) -> Tuple[int, str]:
                try:
                    return (0, int(k))
                except ValueError:
                    return (1, k)

            for ck in sorted(pdef.choices.keys(), key=sort_key):
                self.input_widget.addItem(pdef.choices[ck], userData=ck)
        else:
            self.input_widget = QLineEdit()
            self.input_widget.setPlaceholderText(self.pdef.label)
        grid.addWidget(self.input_widget, 0, 1)

        # Boutons
        self.btn_get = QPushButton("Get")
        self.btn_set = QPushButton("Set")

        # Droits d'accès
        access_str = str(pdef.access).strip().lower()
        can_get = ("get" in access_str)
        can_set = ("set" in access_str)

        self.btn_get.setEnabled(can_get)
        self.btn_set.setEnabled(can_set)
        self.btn_get.setVisible(can_get)
        self.btn_set.setVisible(can_set)

        # Handlers
        self.btn_get.clicked.connect(self._on_get)
        self.btn_set.clicked.connect(self._on_set)

        btns = QHBoxLayout()
        btns.addWidget(self.btn_get)
        btns.addWidget(self.btn_set)
        btns.addStretch(1)
        grid.addLayout(btns, 0, 2)

        # Layout tweaks
        self.lbl.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # ---------- Helpers ----------
    def _log(self, text: str) -> None:
        self.console.append(text)
        self.console.ensureCursorVisible()

    # ---------- Actions ----------
    def _on_get(self) -> None:
        try:
            reply = self.backend.do_get(self.module, self.key)
            self._log(f"→ GET {self.module}.{self.key}")
            self._log(f"← {reply}")

            # Si choix: mettre à jour la sélection selon la clé reçue
            if self.pdef.ptype == "choice" and self.pdef.choices:
                idx_key = (reply.split()[-1] if reply else "").strip()
                if idx_key in (self.pdef.choices or {}):
                    for i in range(self.input_widget.count()):  # type: ignore
                        if self.input_widget.itemData(i) == idx_key:  # type: ignore
                            self.input_widget.setCurrentIndex(i)  # type: ignore
                            break
                    self._log(f"[INFO] {self.module}.{self.key} = {self.pdef.choices[idx_key]} (key='{idx_key}')")
            else:
                if hasattr(self.input_widget, "setText"):
                    self.input_widget.setText(reply)  # type: ignore
        except Exception as e:
            self._log(f"[ERREUR] GET {self.module}.{self.key}: {e}")
            QMessageBox.critical(self, "Erreur GET", f"Impossible de lire {self.key}:\n{e}")

    def _on_set(self) -> None:
        try:
            if isinstance(self.input_widget, QComboBox):
                value_key = self.input_widget.currentData()
                value_display = self.input_widget.currentText()
                if value_key is None:
                    value_key = value_display
            else:
                value_key = self.input_widget.text().strip()  # type: ignore
                value_display = value_key

            # Autoriser SET sans valeur pour les paramètres "set"-only
            if not value_key:
                if ("set" in self.pdef.access) and ("get" not in self.pdef.access):
                    value_key = ""  # envoie 'set <key>' sans argument
                else:
                    QMessageBox.warning(self, "Valeur manquante", f"Veuillez fournir une valeur pour {self.key}.")
                    return

            reply = self.backend.do_set(self.module, self.key, str(value_key))
            self._log(f"→ SET {self.module}.{self.key} = {value_display} (raw:{value_key})")
            self._log(f"← {reply}")
        except Exception as e:
            self._log(f"[ERREUR] SET {self.module}.{self.key}: {e}")
            QMessageBox.critical(self, "Erreur SET", f"Impossible d'écrire {self.key}:\n{e}")


# =========================== Page embarquable ===========================

class MenzuCalibratorPage(QWidget):
    """
    Onglet Calibrator.
    - Utilise UN backend série partagé (injecté par main.py).
    - Aucun bouton connecter/déconnecter ici (géré par le Terminal).
    """

    def __init__(
        self,
        json_path: Optional[str] = None,
        backend: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        # Backend : injecté par main.py (recommandé). Sinon, fallback autonome.
        if backend is None:
            # Fallback hors-ligne si le main n'injecte pas (évite crash).
            from serial_backend import SerialBackend
            backend = SerialBackend()
        self.backend = backend

        self.data: Dict[str, Any] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # --- Bandeau d’état Backend (info uniquement) ---
        status_bar = QHBoxLayout()
        self.status_lbl = QLabel()
        self.status_lbl.setStyleSheet("color:#999;")
        status_bar.addWidget(self.status_lbl, 1)
        root.addLayout(status_bar)

        # --- Sélection Carte/Module ---
        sel = QHBoxLayout()
        self.cmb_carte = QComboBox()
        self.cmb_module = QComboBox()
        self.cmb_carte.currentTextChanged.connect(self._on_card_changed)
        self.cmb_module.currentTextChanged.connect(self._on_module_changed)
        sel.addWidget(QLabel("Carte:"))
        sel.addWidget(self.cmb_carte, 1)
        sel.addWidget(QLabel("Module:"))
        sel.addWidget(self.cmb_module, 1)
        root.addLayout(sel)

        # --- Zone paramètres (scroll) ---
        self.params_scroll = QScrollArea()
        self.params_scroll.setWidgetResizable(True)
        self.params_host = QWidget()
        self.params_layout = QVBoxLayout(self.params_host)
        self.params_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.params_layout.setSpacing(6)
        self.params_layout.setContentsMargins(6, 6, 6, 6)
        self.params_scroll.setWidget(self.params_host)
        root.addWidget(self.params_scroll, 1)

        # --- Boutons globaux ---
        bulk = QHBoxLayout()
        self.btn_get_all = QPushButton("Get All")
        self.btn_set_all = QPushButton("Set All")
        self.btn_get_all.clicked.connect(self._on_get_all)
        self.btn_set_all.clicked.connect(self._on_set_all)
        bulk.addStretch(1)
        bulk.addWidget(self.btn_get_all)
        bulk.addWidget(self.btn_set_all)
        root.addLayout(bulk)

        # --- Console ---
        grp = QGroupBox("Console")
        v = QVBoxLayout(grp)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        v.addWidget(self.console)
        root.addWidget(grp, 1)

        # --- Charger JSON ---
        try:
            self.data = load_config_any(json_path)
            src = self.data.pop("_loaded_from", None)
            if src:
                self.console.append(f"[INFO] JSON chargé: {src}")
        except Exception as e:
            self.console.append(f"[ERREUR] Chargement JSON: {e}")
            QMessageBox.critical(self, "JSON invalide", str(e))
            self._update_status_label()
            return

        # Remplir cartes
        cards = list(self.data.get("cartes", {}).keys())
        self.cmb_carte.blockSignals(True)
        self.cmb_module.blockSignals(True)
        self.cmb_carte.clear()
        self.cmb_module.clear()
        self.cmb_carte.addItems(cards)
        self.cmb_carte.blockSignals(False)
        self.cmb_module.blockSignals(False)

        # Etat initial
        self._update_status_label()
        if cards:
            self._on_card_changed(cards[0])
        else:
            self.console.append("[WARN] Aucune carte trouvée.")

    # ---------- Helpers UI ----------
    def _update_status_label(self) -> None:
        try:
            connected = bool(getattr(self.backend, "is_connected", lambda: False)())
        except Exception:
            connected = False

        if connected:
            port = getattr(self.backend, "port", None)
            self.status_lbl.setText(f"Backend: connecté à {port}")
        else:
            self.status_lbl.setText("Backend: hors-ligne (utilise le port du Terminal lorsque connecté)")

    def _clear_params(self) -> None:
        while True:
            item = self.params_layout.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _iter_rows(self) -> Iterable[ParamRow]:
        for i in range(self.params_layout.count()):
            it = self.params_layout.itemAt(i)
            if it:
                w = it.widget()
                if isinstance(w, ParamRow):
                    yield w

    # ---------- Cartes / Modules ----------
    def _on_card_changed(self, card_name: str) -> None:
        modules_dict = self.data.get("cartes", {}).get(card_name, {})
        if not isinstance(modules_dict, dict):
            self.console.append(f"[ERREUR] Les modules de '{card_name}' ne sont pas un dict.")
            self._clear_params()
            return

        modules = list(modules_dict.keys())
        self.console.append(f"[DEBUG] Modules pour '{card_name}': {modules}")

        self.cmb_module.blockSignals(True)
        self.cmb_module.clear()
        self.cmb_module.addItems(modules)
        self.cmb_module.blockSignals(False)

        if modules:
            self._on_module_changed(modules[0])
        else:
            self.console.append(f"[WARN] Aucun module sous '{card_name}'.")
            self._clear_params()

    def _on_module_changed(self, module_name: str) -> None:
        self._clear_params()

        card_name = self.cmb_carte.currentText()
        params = self.data.get("cartes", {}).get(card_name, {}).get(module_name, {})
        if not isinstance(params, dict):
            self.console.append(f"[ERREUR] Paramètres '{card_name}.{module_name}' non-dict.")
            return
        if not params:
            self.console.append(f"[WARN] Aucun paramètre sous '{card_name}.{module_name}'.")
            return

        # Ordre imposé pour quelques modules
        preferred_orders = {
            "LoRaWAN_at": ["APPKEY", "DEUI", "NWKKEY", "ACT", "CLASS", "NJS", "CFM"],
            "NVM": [
                "MAX_LOG1","MAX_LOG2","MAX_LOG3","MAX_LOG4","MAX_LOG5",
                "LOG1_WRITE","LOG2_WRITE","LOG3_WRITE","LOG4_WRITE","LOG5_WRITE",
                "LOG1_READ","LOG2_READ","LOG3_READ","LOG4_READ","LOG5_READ",
                "LOG1_UNREAD","LOG2_UNREAD","LOG3_UNREAD","LOG4_UNREAD","LOG5_UNREAD",
                "CLEAR_LOG1","CLEAR_LOG2","CLEAR_LOG3","CLEAR_LOG4","CLEAR_LOG5"
            ],
            "MODBUS_Master": ["PORT","SPEED","PARITY","HOST"],
        }
        keys = list(params.keys())
        if module_name in preferred_orders:
            order = preferred_orders[module_name]
            keys = [k for k in order if k in params] + [k for k in keys if k not in order]

        self.console.append(f"[DEBUG] Params clés (ordonnés): {keys}")

        created = 0
        for key in keys:
            meta = params.get(key)
            if not isinstance(meta, dict):
                self.console.append(f"[WARN] Param '{key}' ignoré: type {type(meta)}")
                continue

            pdef = ParamDef(
                label=meta.get("label", key),
                ptype=meta.get("type", "text"),
                access=str(meta.get("access", "getset")).lower(),
                choices=meta.get("choices") if meta.get("type") == "choice" else None,
            )

            try:
                row = ParamRow(module_name, key, pdef, self.backend, self.console)
                self.params_layout.addWidget(row)
                created += 1
                self.console.append(f"[DEBUG] Ligne créée: {module_name}.{key} (access={pdef.access}, type={pdef.ptype})")
            except Exception as e:
                self.console.append(f"[ERREUR] Création ligne '{key}': {e}")

        # Un seul stretch pour pousser le reste vers le haut
        self.params_layout.addStretch(1)
        self.console.append(f"[INFO] Lignes créées: {created}/{len(keys)} pour {card_name}.{module_name}")

    # ---------- Get/Set All ----------
    def _on_get_all(self) -> None:
        if not getattr(self.backend, "is_connected", lambda: False)():
            QMessageBox.warning(self, "Non connecté", "Veuillez d'abord démarrer la communication (onglet Terminal).")
            return
        count = 0
        for row in self._iter_rows():
            if "get" in row.pdef.access:
                row._on_get()
                count += 1
        self.console.append(f"[INFO] Get All: {count} paramètres lus")

    def _on_set_all(self) -> None:
        if not getattr(self.backend, "is_connected", lambda: False)():
            QMessageBox.warning(self, "Non connecté", "Veuillez d'abord démarrer la communication (onglet Terminal).")
            return
        reply = QMessageBox.question(
            self, "Confirmation",
            "Voulez-vous vraiment écrire tous les paramètres modifiables ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        count = 0
        for row in self._iter_rows():
            if "set" in row.pdef.access:
                row._on_set()
                count += 1
        self.console.append(f"[INFO] Set All: {count} paramètres écrits")
