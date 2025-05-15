"""
Worker for FLRig communication with error handling and logging.
"""

from PyQt5 import QtCore
from src.logger import log_error, log_info
import threading

class FLRigWorker(QtCore.QThread):
    """
    Worker thread for polling FLRig data.
    Emits signals for new data or errors.
    """
    result = QtCore.pyqtSignal(str, str, str, str)  # freq, mode, band, debug_msg

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.running = True
        self.last_freq_a = None
        self.last_freq_b = None
        self.last_vfo = "A"
        self._poll_now_event = threading.Event()  # <-- NEU
    def poll_now(self):
        self._poll_now_event.set() 
        # Set the event to trigger immediate polling
             
    def run(self):
        import time
        import xmlrpc.client
        while self.running:
            debug_msg = ""
            freq = mode = band = ""
            try:
                url = f"http://{self.host}:{self.port}/RPC2"
                flrig = xmlrpc.client.ServerProxy(url)
                try:
                    vfo_status = flrig.rig.get_vfo()
                except Exception as e:
                    debug_msg += f"VFO-Error: {e} | "
                    vfo_status = 0.0

                try:
                    freq_a = float(flrig.rig.get_vfoA())
                    mode_a = flrig.rig.get_modeA()
                except Exception:
                    freq_a = 0.0
                    mode_a = ""
                try:
                    freq_b = float(flrig.rig.get_vfoB())
                    mode_b = flrig.rig.get_modeB()
                except Exception:
                    freq_b = 0.0
                    mode_b = ""

                try:
                    vfo_status_f = float(vfo_status)
                except Exception:
                    vfo_status_f = 0.0

                if abs(vfo_status_f - freq_a) < 10:
                    freq_val = freq_a
                    mode = mode_a
                    self.last_vfo = "A"
                elif abs(vfo_status_f - freq_b) < 10:
                    freq_val = freq_b
                    mode = mode_b
                    self.last_vfo = "B"
                else:
                    if self.last_vfo == "B":
                        freq_val = freq_b
                        mode = mode_b
                    else:
                        freq_val = freq_a
                        mode = mode_a
                self.last_freq_a = freq_a
                self.last_freq_b = freq_b

                freq = str(int(freq_val)) if freq_val else ""
                # Korrektur: Band-Berechnung immer in MHz!
                band = self.freq_to_band(freq_val / 1_000_000) if freq_val else ""
                debug_msg += (
                    f"FLRig: VFO-Status={vfo_status} | "
                    f"A: {round(freq_a/1e6,3) if freq_a else '-'} MHz {mode_a} | "
                    f"B: {round(freq_b/1e6,3) if freq_b else '-'} MHz {mode_b} | "
                    f"Used: {self.last_vfo} {freq} Hz {mode} Band={band}"
                )
                self.result.emit(freq, mode, band, debug_msg)
            except Exception as e:
                debug_msg += f"FLRig-Error: {e}"
                log_error(debug_msg)
                self.result.emit("", "", "", debug_msg)
           # Wait on Event odorer Timeout (2 seconds)
            self._poll_now_event.wait(timeout=2)
            self._poll_now_event.clear()

    @staticmethod
    def freq_to_band(freq):
        bands = {
            (1.8, 2.0): "160M",
            (3.5, 4.0): "80M",
            (7.0, 7.3): "40M",
            (10.1, 10.15): "30M",
            (14.0, 14.35): "20M",
            (18.068, 18.168): "17M",
            (21.0, 21.45): "15M",
            (24.89, 24.99): "12M",
            (28.0, 29.7): "10M",
            (50.0, 54.0): "6M",
            (144.0, 148.0): "2M",
            (430.0, 440.0): "70CM"
        }
        for (low, high), name in bands.items():
            if low <= freq <= high:
                return name
        return ""