"""
Main QSO form window with statusbar, debug field, error handling, and i18n.
"""

import socket
import os
import json
import unicodedata
import shutil
from src.utils import resource_path
from PyQt5 import QtWidgets, QtCore, QtGui
from datetime import datetime, timezone, timedelta
from src.flrig_worker import FLRigWorker
from src.qrz_lookup import lookup_qrz
from src.config_dialog import ConfigDialog, save_config, load_config
from src.logger import log_error, log_info
from src.utils import now_utc_str
from src.callsign_tag_editor import CallsignTagEditor
from src.utils import user_data_path
from src.focus_aware_lineedit import FocusAwareLineEdit

class QSOForm(QtWidgets.QMainWindow):
    """
    Main window for QSO entry and sending.
    """
    SENT_QSOS_FILE = user_data_path("sent_qsos.adi")
     
    def __init__(self, config, translation):
        """
        Initialize the main QSO form window.
        """
        super().__init__()
        self.config = config
        self.translation = translation
        self.status_history = []
        self.qrz_session_key = None
        self.flrig_worker = None
        self.last_flrig_debug = ""
        self.qso_date_user_set = False
        self.time_on_user_set = False
        self.time_off_user_set = False
        icon_path = resource_path("icons/wlicon_green.png")
        self.setWindowIcon(QtGui.QIcon(icon_path))

        self.init_ui()
        self.check_and_handle_old_sent_qsos() 
        self.update_datetime()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_datetime)
        self.timer.start(1000)
        self.start_flrig_worker()
        self.call.setFocus() # Set focus to the call sign field
        

    def init_ui(self):
        """
        Initialize the user interface.
        """
        self.setWindowTitle(self.translation["app_title"])
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        width = min(600, screen.width() - 60)
        height = min(700, screen.height() - 60)
        font = self.font()
        font.setPointSize(font.pointSize() + 2)  
        self.setFont(font)
        self.resize(width, height)
        self.setMinimumSize(550, 550) 
        
        # Handle manual edit in timecounting fields
        self.time_on_user_set = False
        self.time_off_user_set = False

        # --- ScrollArea ---
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        central_widget = QtWidgets.QWidget()
        scroll_area.setWidget(central_widget)
        self.setCentralWidget(scroll_area)

        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.form_layout = QtWidgets.QFormLayout()
        self.form_layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.form_layout.setVerticalSpacing(16)
        main_layout.addLayout(self.form_layout)
        main_layout.addStretch(1)

        # Fields
        self.call = QtWidgets.QLineEdit()
        self.call_tags_widget = QtWidgets.QWidget()
        self.call_tags_layout = QtWidgets.QHBoxLayout(self.call_tags_widget)
        self.call_tags_layout.setContentsMargins(0, 0, 0, 0)
        self.call_tags_widget.setVisible(False)
        self.call.editingFinished.connect(self.lookup_qrz_gui)
        self.call.textChanged.connect(self.call_to_upper)
        self.band = QtWidgets.QLineEdit()
        self.freq = QtWidgets.QLineEdit()
        self.mode = QtWidgets.QLineEdit()
        self.mode.textChanged.connect(self.update_rst_fields)
        self.rst_sent = QtWidgets.QLineEdit()
        self.rst_rcvd = QtWidgets.QLineEdit()
        self.gridsquare = QtWidgets.QLineEdit()
        self.comment = QtWidgets.QLineEdit()
        self.name = QtWidgets.QLineEdit()
        self.qth = QtWidgets.QLineEdit()
        self.tx_pwr = QtWidgets.QLineEdit()
        self.country = QtWidgets.QLineEdit()
        self.operator = QtWidgets.QLineEdit()
        self.station_callsign = QtWidgets.QLineEdit(self.config.get("station_callsign", ""))
        self.dxcc = QtWidgets.QLineEdit()

        self.qso_date_display = FocusAwareLineEdit()
        self.qso_date_display.setReadOnly(False)
        self.time_on_display = FocusAwareLineEdit()
        self.time_on_display.setReadOnly(False)
        self.time_off_display = FocusAwareLineEdit()
        self.time_off_display.setReadOnly(False)
        self.qso_date_display.focused.connect(self.on_qso_date_focused)
        self.time_on_display.focused.connect(self.on_time_on_focused)
        self.time_off_display.focused.connect(self.on_time_off_focused)
        self.qso_date_adif = ""
        self.time_on_adif = ""
        self.time_off_adif = ""

        # Debug field (visible/invisible) - treat like other fields
        self.flrig_debug_line = QtWidgets.QLineEdit()
        self.flrig_debug_line.setReadOnly(True)
        self.flrig_debug_line.setStyleSheet("color: #00ff00; background: #222;")
        self.flrig_debug_line.setVisible(self.config.get("show_debug", False))
        self.flrig_debug_line.setMinimumHeight(30)
        self.flrig_debug_line.setFont(font)
        self.flrig_debug_line.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Set height and font size for all fields
        for widget in [self.call, self.band, self.freq, self.mode, self.rst_sent, self.rst_rcvd,
                    self.gridsquare, self.comment, self.name, self.qth, self.tx_pwr,
                    self.country, self.operator, self.station_callsign, self.dxcc,
                    self.qso_date_display, self.time_on_display, self.time_off_display]:
            widget.setMinimumWidth(350)
            widget.setMinimumHeight(30)
            widget.setFont(font)
            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Form layout (labels from translation)
        self.flrig_debug_line = None
        self.debug_row_index = self.form_layout.rowCount()
        if self.config.get("show_debug", False):
            self.add_flrig_debug_field()
        self.form_layout.addRow(self.translation["call"], self.call)
        self.form_layout.addRow("", self.call_tags_widget)  
        self.form_layout.addRow(self.translation["band"], self.band)
        self.form_layout.addRow(self.translation["freq"], self.freq)
        self.form_layout.addRow(self.translation["mode"], self.mode)
        self.form_layout.addRow(self.translation["rst_sent"], self.rst_sent)
        self.form_layout.addRow(self.translation["rst_rcvd"], self.rst_rcvd)
        self.form_layout.addRow(self.translation["comment"], self.comment)
        self.form_layout.addRow(self.translation["qso_date"], self.qso_date_display)
        self.form_layout.addRow(self.translation["qso_start"], self.time_on_display)
        self.form_layout.addRow(self.translation["qso_end"], self.time_off_display)
        self.form_layout.addRow(self.translation["name"], self.name)
        self.form_layout.addRow(self.translation["qth"], self.qth)
        self.form_layout.addRow(self.translation["tx_pwr"], self.tx_pwr)
        self.form_layout.addRow(self.translation["country"], self.country)
        self.form_layout.addRow(self.translation["operator"], self.operator)
        self.form_layout.addRow(self.translation["station_callsign"], self.station_callsign)
        self.form_layout.addRow(self.translation["dxcc"], self.dxcc)

        # Make labels bold (after adding the fields!)
        label_font = QtGui.QFont(font)
        label_font.setBold(True)
        for i in range(self.form_layout.rowCount()):
            label_item = self.form_layout.itemAt(i, QtWidgets.QFormLayout.LabelRole)
            if label_item and label_item.widget():
                label_item.widget().setFont(label_font)

        self.create_toolbar_and_menu()
        self.statusbar = self.statusBar()
        self.statusbar.showMessage(self.translation["ready"])
        self.statusbar.messageChanged.connect(self.on_status_message_changed)
        self.statusbar.mousePressEvent = self.show_status_history

    def check_and_handle_old_sent_qsos(self):
        """
        At program start: If sent_qsos.adi exists and is not empty, offer to export or clear.
        """
        if os.path.exists(self.SENT_QSOS_FILE):
            try:
                with open(self.SENT_QSOS_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
            except Exception:
                content = ""
            if content:
                msg = self.translation["unsaved_qsos_found"]
                reply = QtWidgets.QMessageBox.question(
                    self,
                    self.translation["export_old_qsos"],
                    msg,
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
                    QtWidgets.QMessageBox.Yes
                )
                # Yes = export now, No = clear file, Cancel = keep file
                if reply == QtWidgets.QMessageBox.Yes:
                    self.export_sent_qsos()
                    self.clear_sent_qsos_file()
                elif reply == QtWidgets.QMessageBox.No:
                    self.clear_sent_qsos_file()
                # Cancel: keep file as is
            else:
                self.clear_sent_qsos_file()
        else:
            self.clear_sent_qsos_file()

    def clear_sent_qsos_file(self):
        """
        Clear the sent QSO ADIF file.
        """
        with open(self.SENT_QSOS_FILE, "w", encoding="utf-8") as f:
            pass  # just clear

    def append_sent_qso(self, adif_entry):
        """
        Append a sent QSO ADIF entry to the file.
        """
        with open(self.SENT_QSOS_FILE, "a", encoding="utf-8") as f:
            f.write(adif_entry + "\n")

    def export_sent_qsos(self):
        """
        Offer to export all sent QSOs to a file.
        """
        if not os.path.exists(self.SENT_QSOS_FILE):
            QtWidgets.QMessageBox.information(self, self.translation["export"], self.translation["no_qsos_to_export"])
            return
        options = QtWidgets.QFileDialog.Options()
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, self.translation["export"], "", "ADIF Files (*.adi);;All Files (*)", options=options
        )
        if filename:
            shutil.copyfile(self.SENT_QSOS_FILE, filename)
            QtWidgets.QMessageBox.information(self, self.translation["export"], self.translation["qsos_exported"])

    def update_rst_fields(self):
        
        mode_val = self.mode.text().strip().upper()
        if mode_val.startswith("CW"):
            self.rst_sent.setText("599")
            self.rst_rcvd.setText("599")
        elif mode_val:
            self.rst_sent.setText("59")
            self.rst_rcvd.setText("59")

    def show_callsign_tags(self, tags):
        """
        Show tags as bubbles next to the callsign field.
        """
        while self.call_tags_layout.count():
            item = self.call_tags_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        # add new tags as bubble
        for tag in tags:
            lbl = QtWidgets.QLabel(tag)
            lbl.setStyleSheet("background:#ffffff; color:#000000; border-radius:8px; padding:2px 8px; margin-right:4px;")
            self.call_tags_layout.addWidget(lbl)
        self.call_tags_widget.setVisible(bool(tags))

    def call_to_upper(self):
        """
        Convert the callsign input to uppercase.
        """
        text = self.call.text()
        if text != text.upper():
            cursor_pos = self.call.cursorPosition()
            self.call.setText(text.upper())
            self.call.setCursorPosition(cursor_pos)

    def start_flrig_worker(self):
        """
        Start or restart the FLRig worker thread.
        """
        if self.flrig_worker:
            self.flrig_worker.running = False
            self.flrig_worker.wait()
        self.flrig_worker = FLRigWorker(self.config.get("flrig_host", "127.0.0.1"),
                                        self.config.get("flrig_port", 12345))
        self.flrig_worker.result.connect(self.update_flrig_fields)
        self.flrig_worker.start()

    def update_flrig_fields(self, freq, mode, band, debug_msg):
        """
        Update form fields with data from FLRig.
        """
        flrig_connected = bool(freq or mode or band)
        
        # Set mode to simple modes. From CW-L to CW etc.
        def simplify_mode(m):
            m = m.upper()
            if m.startswith("CW"):
                return "CW"
            if m in ("LSB", "USB"):
                return "SSB"
            if m.startswith("FM"):
                return "FM"
            if m.startswith("AM"):
                return "AM"
            return m

        def format_freq(freq_str):
            """
            Formats Freqency coming from FLRig.
            """
            try:
                s = str(freq_str).replace(",", ".")
                freq_val = float(s)
                # if value > 1_000_000, it is in Hz, otherwise MHz
                if freq_val > 1_000_000:
                    hz = int(freq_val)
                else:
                    hz = int(round(freq_val * 1_000_000))
                mhz = hz // 1_000_000
                khz = (hz // 1_000) % 1_000
                hz_rest = hz % 1_000
                return f"{mhz}.{khz:03}.{hz_rest:03}"
            except Exception:
                return str(freq_str)

        if flrig_connected:
            # Frequency always override if different
            formatted_freq = format_freq(freq) if freq else ""
            if self.freq.text().strip() != formatted_freq:
                self.freq.setText(formatted_freq)

            # Mode  always override if different
            mode_val = simplify_mode(mode) if mode else ""
            if self.mode.text().strip().upper() != mode_val:
                self.mode.setText(mode_val)
            else:
                mode_val = self.mode.text().strip().upper()

            # Band  always override if different
            band_val = band if band else ""
            if self.band.text().strip() != band_val:
                self.band.setText(band_val)

            self.last_flrig_debug = debug_msg
            if self.flrig_debug_line:
                self.flrig_debug_line.setText(debug_msg)
            # PReload RST fields (only if empty)
            if mode_val == "CW":
                if self.rst_sent.text().strip() == "":
                    self.rst_sent.setText("599")
                if self.rst_rcvd.text().strip() == "":
                    self.rst_rcvd.setText("599")
            elif mode_val:
                if self.rst_sent.text().strip() == "":
                    self.rst_sent.setText("59")
                if self.rst_rcvd.text().strip() == "":
                    self.rst_rcvd.setText("59")
        else:
            self.last_flrig_debug = debug_msg
            if self.flrig_debug_line:
                self.flrig_debug_line.setText(debug_msg)

    def create_toolbar_and_menu(self):
        """
        Create the toolbar and menu bar.
        """
        for tb in self.findChildren(QtWidgets.QToolBar):
            self.removeToolBar(tb)
        send_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)
        reset_icon = self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)
        exit_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DialogCloseButton)
        config_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogDetailedView)
        tag_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileDialogInfoView)

        toolbar = self.addToolBar(self.translation["actions"])
        toolbar.setMovable(False)
        send_action = QtWidgets.QAction(send_icon, self.translation["send"], self)
        send_action.triggered.connect(self.send_qso)
        reset_action = QtWidgets.QAction(reset_icon, self.translation["reset"], self)
        reset_action.triggered.connect(self.reset_fields)
        exit_action = QtWidgets.QAction(exit_icon, self.translation["exit"], self)
        exit_action.triggered.connect(self.close)
        config_action = QtWidgets.QAction(config_icon, self.translation["config"], self)
        config_action.triggered.connect(self.open_config_dialog)
        tag_action = QtWidgets.QAction(tag_icon, self.translation.get("edit_callsign_tags", "Edit Callsign Tags"), self)
        tag_action.triggered.connect(self.open_callsign_tag_editor)

        toolbar.addAction(send_action)
        toolbar.addAction(reset_action)
        toolbar.addAction(config_action)
        toolbar.addAction(tag_action)
        toolbar.addSeparator()     
        toolbar.addAction(exit_action)
         

        # Add Spacer push to the right
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        spacer.setStyleSheet("background: transparent;")
        toolbar.addWidget(spacer) 
                
        # Added Always on top checkbox 
        self.always_on_top_checkbox = QtWidgets.QCheckBox(self.translation.get("always_on_top", "Always on top"))
        self.always_on_top_checkbox.setChecked(False)
        self.always_on_top_checkbox.stateChanged.connect(self.toggle_always_on_top)
        self.always_on_top_checkbox.setStyleSheet(
            "QCheckBox { background:transparent; color: #fff; padding: 2px 8px; border-radius: 4px; }"
        )
        
        toolbar.addWidget(self.always_on_top_checkbox)

        menubar = self.menuBar()
        file_menu = menubar.addMenu(self.translation["file"])
        file_menu.addAction(send_action)
        file_menu.addAction(reset_action)
        file_menu.addAction(config_action)
        file_menu.addAction(tag_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

    def toggle_always_on_top(self, state):
        """
        Toggle the always-on-top window flag based on the checkbox state.
        """
        if state == QtCore.Qt.Checked:
            self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        else:
            self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, False)
        self.show()  # Necessary to apply the window flag change
        
    def on_qso_date_focused(self):
        """
        Wird aufgerufen, wenn das QSO-Datum-Feld den Fokus erhält.
        """
        self.qso_date_user_set = True

    def on_time_on_focused(self):
        """
        Wird aufgerufen, wenn das QSO-Startzeit-Feld den Fokus erhält.
        """
        self.time_on_user_set = True

    def on_time_off_focused(self):
        """
        Wird aufgerufen, wenn das QSO-Endzeit-Feld den Fokus erhält.
        """
        self.time_off_user_set = True
                
    def update_datetime(self):
        """
        Update the date and time fields.
        Only update date if empty, and time fields only if not user-set.
        """
        now = datetime.now()
        now_utc = datetime.now(timezone.utc)
        # Only set date if field is empty
        if not self.qso_date_user_set:
            self.qso_date_display.setText(now.strftime("%d.%m.%Y"))
        # Zeitfelder nur setzen, wenn nicht user-set
        if not self.time_on_user_set:
            self.time_on_display.setText(now_utc.strftime("%H:%M:%S"))
        if not self.time_off_user_set:
            time_off_utc = now_utc + timedelta(seconds=20)
            self.time_off_display.setText(time_off_utc.strftime("%H:%M:%S"))
        # ADIF fields always from display fields
        self.qso_date_adif = now_utc.strftime("%Y%m%d")
        self.time_on_adif = self.time_on_display.text().replace(":", "")
        self.time_off_adif = self.time_off_display.text().replace(":", "")

    def reset_fields(self):
        """
        Reset all input fields to their default state.
        """
        for widget in [self.call, self.band, self.freq, self.mode, self.rst_sent, self.rst_rcvd,
                       self.gridsquare, self.comment, self.name, self.qth, self.tx_pwr,
                       self.country, self.operator, self.dxcc]:
            widget.clear()
        self.station_callsign.setText(self.config.get("station_callsign", ""))
        self.qso_date_user_set = False
        self.time_on_user_set = False
        self.time_off_user_set = False
        self.update_datetime()
        self.statusbar.showMessage(self.translation["fields_reset"])
        self.show_callsign_tags([]) 
        self.call.setFocus() # Set focus to the call sign field
        if self.flrig_worker: # Poll FLRig for current values
            self.flrig_worker.poll_now()
            
    def adif_freq_value(self):
        """
        Convert frequency to ADIF format.
        """
        # Converts "7.012.620" to "7.01262"
        freq_parts = self.freq.text().split(".")
        if len(freq_parts) == 3:
            return f"{freq_parts[0]}.{freq_parts[1]}{freq_parts[2]}"
        return self.freq.text().replace(",", ".")  # Fallback

    def adif_safe(self, text):
        """
        Convert text to ADIF-safe ASCII: replaces German umlauts and ß, removes accents.
        """
        text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        text = text.replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
        text = text.replace("ß", "ss")
        # Remove all other accents
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        return text

    def send_qso(self):
        """
        Send the QSO data to WLGate via UDP.
        """
        self.statusbar.showMessage(self.translation["sending_qso"])
        if not self.call.text().strip():
            QtWidgets.QMessageBox.warning(self, self.translation["error"], self.translation["call_required"])
            self.statusbar.showMessage(self.translation["call_required"])
            return
        if not self.band.text().strip():
            QtWidgets.QMessageBox.warning(self, self.translation["error"], self.translation["band_required"])
            self.statusbar.showMessage(self.translation["band_required"])
            return
        if not self.mode.text().strip():
            QtWidgets.QMessageBox.warning(self, self.translation["error"], self.translation["mode_required"])
            self.statusbar.showMessage(self.translation["mode_required"])
            return
        if not self.rst_sent.text().strip():
            QtWidgets.QMessageBox.warning(self, self.translation["error"], self.translation["rst_sent_required"])
            self.statusbar.showMessage(self.translation["rst_sent_required"])
            return
        if not self.rst_rcvd.text().strip():
            QtWidgets.QMessageBox.warning(self, self.translation["error"], self.translation["rst_rcvd_required"])
            self.statusbar.showMessage(self.translation["rst_rcvd_required"])
            return


        def adif_field(name, value):
            """
           Build ADIF field name value pair.
            """
            # Remove German umlauts and ß
            value = self.adif_safe(value.strip())
            return f"<{name}:{len(value)}>{value}" if value else ""

        adif = (
            adif_field("CALL", self.call.text()) +
            adif_field("QSO_DATE", self.qso_date_adif) +
            adif_field("TIME_ON", self.time_on_adif) +
            adif_field("TIME_OFF", self.time_off_adif) +
            adif_field("BAND", self.band.text()) +
            adif_field("FREQ", self.adif_freq_value()) +
            adif_field("MODE", self.mode.text()) +
            adif_field("RST_SENT", self.rst_sent.text()) +
            adif_field("RST_RCVD", self.rst_rcvd.text()) +
            adif_field("GRIDSQUARE", self.gridsquare.text()) +
            adif_field("COMMENT", self.comment.text()) +
            adif_field("NAME", self.name.text()) +
            adif_field("QTH", self.qth.text()) +
            adif_field("TX_PWR", self.tx_pwr.text()) +
            adif_field("COUNTRY", self.country.text()) +
            adif_field("OPERATOR", self.operator.text()) +
            adif_field("STATION_CALLSIGN", self.station_callsign.text()) +
            adif_field("DXCC", self.dxcc.text()) +
            "<EOR>"
        )

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(adif.encode('ascii', errors='replace'), (self.config.get("wlgate_host", "127.0.0.1"), self.config.get("wlgate_port", 2237)))
            sock.close()
 
            QtWidgets.QMessageBox.information(self, self.translation["success"], self.translation["qso_sent"])
            self.statusbar.showMessage(self.translation["qso_sent"])
            self.reset_fields()
            log_info("QSO sent to WLGate.")
            self.append_sent_qso(adif)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, self.translation["error"], f"{self.translation['send_error']}: {e}")
            self.statusbar.showMessage(f"{self.translation['send_error']}: {e}")
            log_error(f"WLGate send error: {e}")

        if self.flrig_worker: # Poll FLRig for current values
            self.flrig_worker.poll_now()
            
    def add_flrig_debug_field(self):
        """
        Add the FLRig debug field to the form.
        """
        font = self.font()
        label_font = QtGui.QFont(font)
        label_font.setBold(True)
        self.flrig_debug_line = QtWidgets.QLineEdit()
        self.flrig_debug_line.setReadOnly(True)
        self.flrig_debug_line.setStyleSheet("color: #00ff00; background: #222;")
        self.flrig_debug_line.setMinimumHeight(30)
        self.flrig_debug_line.setFont(font)
        self.flrig_debug_line.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        # Always insert at row 0!
        self.form_layout.insertRow(0, self.translation["flrig_debug"], self.flrig_debug_line)
        label_item = self.form_layout.itemAt(0, QtWidgets.QFormLayout.LabelRole)
        if label_item and label_item.widget():
            label_item.widget().setFont(label_font)
        self.flrig_debug_line.setText(self.last_flrig_debug)

    def apply_translation(self, translation):
        """
        Apply a new translation to all labels and UI elements.
        """
        self.translation = translation
        self.setWindowTitle(self.translation["app_title"])
        # Labels in the form
        row = 0
        if self.flrig_debug_line and self.form_layout.itemAt(row, QtWidgets.QFormLayout.LabelRole):
            self.form_layout.labelForField(self.flrig_debug_line).setText(self.translation["flrig_debug"])
            row += 1
        self.form_layout.labelForField(self.call).setText(self.translation["call"])
        row += 1
        
        row += 1
        self.form_layout.labelForField(self.band).setText(self.translation["band"])
        self.form_layout.labelForField(self.freq).setText(self.translation["freq"])
        self.form_layout.labelForField(self.mode).setText(self.translation["mode"])
        self.form_layout.labelForField(self.rst_sent).setText(self.translation["rst_sent"])
        self.form_layout.labelForField(self.rst_rcvd).setText(self.translation["rst_rcvd"])
        self.form_layout.labelForField(self.gridsquare).setText(self.translation["gridsquare"])
        self.form_layout.labelForField(self.comment).setText(self.translation["comment"])
        self.form_layout.labelForField(self.name).setText(self.translation["name"])
        self.form_layout.labelForField(self.qth).setText(self.translation["qth"])
        self.form_layout.labelForField(self.tx_pwr).setText(self.translation["tx_pwr"])
        self.form_layout.labelForField(self.country).setText(self.translation["country"])
        self.form_layout.labelForField(self.operator).setText(self.translation["operator"])
        self.form_layout.labelForField(self.station_callsign).setText(self.translation["station_callsign"])
        self.form_layout.labelForField(self.dxcc).setText(self.translation["dxcc"])
        self.form_layout.labelForField(self.qso_date_display).setText(self.translation["qso_date"])
        self.form_layout.labelForField(self.time_on_display).setText(self.translation["qso_start"])
        self.form_layout.labelForField(self.time_off_display).setText(self.translation["qso_end"])
        # Rebuild toolbar and menus
        self.menuBar().clear()
        self.create_toolbar_and_menu()
        # Status bar
        self.statusbar.showMessage(self.translation["ready"])

    def open_config_dialog(self):
        """
        Open the configuration dialog and apply changes if accepted.
        """       
        dlg = ConfigDialog(self, self.config, self.translation)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            old_lang = self.config.get("language", "en")
            self.config = dlg.get_config()
            save_config(self.config)
            self.config = load_config()
            new_lang = self.config.get("language", "en")
            if new_lang != old_lang:
                from src.utils import load_translation
                translation = load_translation(new_lang)
                self.apply_translation(translation)
            self.station_callsign.setText(self.config.get("station_callsign", ""))
            self.statusbar.showMessage(self.translation["config_saved"])
            self.start_flrig_worker()
            # remove Debugfield, if exist
            if self.form_layout.rowCount() > 0:
                label_item = self.form_layout.itemAt(0, QtWidgets.QFormLayout.LabelRole)
                if label_item and label_item.widget() and label_item.widget().text() == self.translation["flrig_debug"]:
                    self.form_layout.removeRow(0)
                    self.flrig_debug_line = None  # delete reference 

            # Add new debug field
            if self.config.get("show_debug", False):
                font = self.font()
                label_font = QtGui.QFont(font)
                label_font.setBold(True)
                self.flrig_debug_line = QtWidgets.QLineEdit()
                self.flrig_debug_line.setReadOnly(True)
                self.flrig_debug_line.setStyleSheet("color: #00ff00; background: #222;")
                self.flrig_debug_line.setMinimumHeight(30)
                self.flrig_debug_line.setFont(font)
                self.flrig_debug_line.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                self.form_layout.insertRow(self.debug_row_index, self.translation["flrig_debug"], self.flrig_debug_line)
                # Label set bold
                label_item = self.form_layout.itemAt(self.debug_row_index, QtWidgets.QFormLayout.LabelRole)
                if label_item and label_item.widget():
                    label_item.widget().setFont(label_font)
                self.flrig_debug_line.setText(self.last_flrig_debug)
            
    def load_and_show_callsign_tags(self):
        """
        Load and display tags for the current callsign.
        """
        callsign = self.call.text().strip().upper()
        if not callsign:
            self.show_callsign_tags([])
            return
        tags = []
        try:
            tags_file = user_data_path("callsign_tags.json")
            if os.path.exists(tags_file):
                with open(tags_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                tags = data.get(callsign, [])
        except Exception as e:
            log_error(f"Error loading callsign tags: {e}")
        self.show_callsign_tags(tags)
                
    def open_callsign_tag_editor(self):
        """
        Open the callsign tag editor dialog.
        """
        dlg = CallsignTagEditor(self, translation=self.translation)
        dlg.exec_()
        
    def lookup_qrz_gui(self):
        """
        Perform a QRZ.com lookup for the current callsign.
        If not found, try again without /P, /M, /AM, /MM suffix.
        """
        call = self.call.text().strip()
        if not call or not self.config.get("qrz_username") or not self.config.get("qrz_password"):
            self.statusbar.showMessage(self.translation["qrz_skipped"])
            self.show_callsign_tags([]) 
            return

        self.statusbar.showMessage(self.translation["qrz_query"].format(call=call))
        data, self.qrz_session_key = lookup_qrz(
            call,
            self.config.get("qrz_username"),
            self.config.get("qrz_password"),
            self.qrz_session_key
        )

        # If not found, try again without /P, /M, /AM, /MM
        if not data:
            import re
            match = re.match(r"^([A-Z0-9]+)(/(P|M|AM|MM))$", call, re.IGNORECASE)
            if match:
                base_call = match.group(1)
                self.statusbar.showMessage(self.translation["qrz_query"].format(call=base_call))
                data, self.qrz_session_key = lookup_qrz(
                    base_call,
                    self.config.get("qrz_username"),
                    self.config.get("qrz_password"),
                    self.qrz_session_key
                )

        if data:
            self.name.setText(data["name"])
            self.qth.setText(data["qth"])
            self.country.setText(data["country"])
            self.gridsquare.setText(data["gridsquare"])
            self.statusbar.showMessage(self.translation["qrz_data_ok"].format(call=call))
        else:
            self.statusbar.showMessage(self.translation.get("qrz_not_found", "Rufzeichen nicht bei QRZ gefunden"))
        self.comment.setFocus()
        self.load_and_show_callsign_tags()
        
    def on_status_message_changed(self, msg):
        """
        Handle changes to the status bar message.
        """
        timestamp = now_utc_str()
        entry = f"{timestamp} {msg}"
        self.status_history.append(entry)
        log_info(msg)

    def show_status_history(self, event):
        """
        Show a dialog with the status message history.
        """
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(self.translation.get("status_history", "Status History"))
        layout = QtWidgets.QVBoxLayout(dlg)
        text = QtWidgets.QTextEdit("\n".join(self.status_history))
        text.setReadOnly(True)
        layout.addWidget(text)
        btn_copy = QtWidgets.QPushButton(self.translation.get("copy_to_clipboard", "Copy to clipboard"))
        btn_copy.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(text.toPlainText()))
        layout.addWidget(btn_copy)
        dlg.exec_()

    def save_session_history_adif(self):
        """
        Save all sent QSOs of this session as an ADIF file in data/historie with a localized timestamped filename.
        Keep only the 100 most recent history files in the directory.
        """
        history_dir = user_data_path(os.path.join("", "historie"))
        os.makedirs(history_dir, exist_ok=True)

        fmt = self.translation.get("history_filename_format", "%Y-%m-%d_%H-%M-%S_history.adi")
        now = datetime.now()
        filename = now.strftime(fmt)
        full_path = os.path.join(history_dir, filename)

        if os.path.exists(self.SENT_QSOS_FILE):
            try:
                with open(self.SENT_QSOS_FILE, "r", encoding="utf-8") as src, open(full_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
            except Exception as e:
                log_error(f"Could not write session history ADIF: {e}")

        # --- Keep only the 100 newest history files ---
        try:
            files = [os.path.join(history_dir, f) for f in os.listdir(history_dir) if f.endswith(".adi")]
            files.sort(key=lambda x: os.path.getmtime(x))  # oldest first
            limit = 100
            num_to_delete = len(files) - limit
            if num_to_delete > 0:
                for old_file in files[:num_to_delete]:
                    try:
                        os.remove(old_file)
                    except Exception as e:
                        log_error(f"Could not remove old history file {old_file}: {e}")
                # log userinfo
                log_info(self.translation["history_cleanup_info"].format(count=num_to_delete, limit=limit))
        except Exception as e:
            log_error(f"Could not clean up history directory: {e}")

    def closeEvent(self, event):
        """
        Handle the window close event.
        """
        if self.flrig_worker:
            self.flrig_worker.running = False
            self.flrig_worker.wait()
        
        # Write History adif anyways.
        self.save_session_history_adif()
        
        # Offer export on close if file is not empty
        if os.path.exists(self.SENT_QSOS_FILE):
            try:
                with open(self.SENT_QSOS_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
            except Exception:
                content = ""
            if content:
                reply = QtWidgets.QMessageBox.question(
                    self,
                    self.translation["export"],
                    self.translation["export_qsos_on_exit"],
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                )
                if reply == QtWidgets.QMessageBox.Yes:
                    self.export_sent_qsos()
                self.clear_sent_qsos_file()
        event.accept()