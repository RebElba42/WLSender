import json
import os
from PyQt5 import QtWidgets, QtCore
from src.utils import user_data_path
from src.utils import resource_path

DATA_DIR = resource_path("data")
CALLSIGN_TAGS_FILE = user_data_path("callsign_tags.json")

class CallsignTagEditor(QtWidgets.QDialog):
    def __init__(self, parent=None, translation=None):
        super().__init__(parent)
        self.translation = translation or {}
        self.setWindowTitle(self.translation.get("callsign_tag_editor_title", "Callsign Tags Editor"))
        self.setMinimumSize(400, 300)
        self.data = {}
        self.load_data()

        layout = QtWidgets.QVBoxLayout(self)

        # Rufzeichen-Liste (ComboBox)
        self.callsign_combo = QtWidgets.QComboBox()
        self.callsign_combo.setEditable(True)
        self.callsign_combo.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.callsign_combo.setPlaceholderText(self.translation.get("callsign_select_placeholder", "Select or enter callsign"))
        self.callsign_combo.currentTextChanged.connect(self.on_callsign_selected)
        layout.addWidget(self.callsign_combo)

        # Rufzeichen-Eingabe (synchronisiert mit ComboBox)
        self.call_input = self.callsign_combo.lineEdit()
        self.call_input.setPlaceholderText(self.translation.get("callsign_placeholder", "Enter callsign (e.g. DL1ABC)"))
        self.call_input.editingFinished.connect(self.load_tags_for_call)
        # Nur Großbuchstaben erlauben:
        self.call_input.textChanged.connect(lambda text: self.call_input.setText(text.upper()))

        # Tag-Liste
        self.tag_list = QtWidgets.QListWidget()
        layout.addWidget(self.tag_list)

        # Tag hinzufügen/entfernen
        tag_input_layout = QtWidgets.QHBoxLayout()
        self.new_tag_input = QtWidgets.QLineEdit()
        self.new_tag_input.setPlaceholderText(self.translation.get("add_tag_placeholder", "Add new tag"))
        tag_input_layout.addWidget(self.new_tag_input)
        btn_add = QtWidgets.QPushButton(self.translation.get("add_tag", "Add Tag"))
        btn_add.clicked.connect(self.add_tag)
        tag_input_layout.addWidget(btn_add)
        btn_remove = QtWidgets.QPushButton(self.translation.get("remove_selected", "Remove Selected"))
        btn_remove.clicked.connect(self.remove_selected_tag)
        tag_input_layout.addWidget(btn_remove)
        layout.addLayout(tag_input_layout)

        # Speichern & Schließen
        btn_save = QtWidgets.QPushButton(self.translation.get("save", "Save"))
        btn_save.clicked.connect(self.save_and_close)
        layout.addWidget(btn_save)

        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        self.update_callsign_list()

    def apply_translation(self, translation):
        self.translation = translation
        self.setWindowTitle(self.translation.get("callsign_tag_editor_title", "Callsign Tags Editor"))
        self.callsign_combo.setPlaceholderText(self.translation.get("callsign_select_placeholder", "Select or enter callsign"))
        self.call_input.setPlaceholderText(self.translation.get("callsign_placeholder", "Enter callsign (e.g. DL1ABC)"))
        self.new_tag_input.setPlaceholderText(self.translation.get("add_tag_placeholder", "Add new tag"))
        # Buttons und weitere Texte ggf. aktualisieren

    def load_data(self):
        if os.path.exists(CALLSIGN_TAGS_FILE):
            with open(CALLSIGN_TAGS_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {}

    def update_callsign_list(self):
        self.callsign_combo.blockSignals(True)
        self.callsign_combo.clear()
        self.callsign_combo.addItems(sorted(self.data.keys()))
        self.callsign_combo.blockSignals(False)

    def on_callsign_selected(self, callsign):
        self.call_input.setText(callsign)
        self.load_tags_for_call()  # Hier wird die Tag-Liste aktualisiert (geleert oder gefüllt)

    def load_tags_for_call(self):
        call = self.call_input.text().strip().upper()
        self.tag_list.clear()
        if call and call in self.data:
            self.tag_list.addItems(self.data[call])

    def add_tag(self):
        call = self.call_input.text().strip().upper()
        tag = self.new_tag_input.text().strip()
        if not call or not tag:
            return
        tags = self.data.setdefault(call, [])
        if len(tags) >= 5:
            QtWidgets.QMessageBox.warning(
                self,
                self.translation.get("tag_limit_title", "Tag limit reached"),
                self.translation.get("tag_limit_msg", "A maximum of 5 tags per callsign is allowed.")
            )
            return
        if tag not in tags:
            tags.append(tag)
            self.tag_list.addItem(tag)
            self.update_callsign_list()
        self.new_tag_input.clear()

    def remove_selected_tag(self):
        call = self.call_input.text().strip().upper()
        selected = self.tag_list.selectedItems()
        if not call or not selected:
            return
        tags = self.data.get(call, [])
        for item in selected:
            tag = item.text()
            if tag in tags:
                tags.remove(tag)
            self.tag_list.takeItem(self.tag_list.row(item))
        self.update_callsign_list()
        
    def save_and_close(self):
        with open(CALLSIGN_TAGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        self.accept()