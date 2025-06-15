#!/usr/bin/env python3
# qa_overlay.py – dezentes Overlay mit Auto-Clear, Pfeilanzeige, unten mittig

import sys
import socket
import threading
import logging
import time
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QDesktopWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPainter, QPen, QColor

class TransparentOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.text_labels = []
        self.y_position = 20
        self.is_visible = False
        self.setup_window()
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler(), logging.FileHandler('qa_overlay.log')]
        )
        self.logger = logging.getLogger(__name__)

    def setup_window(self):
        try:
            self.setWindowTitle("Q&A Overlay")
            desktop = QDesktopWidget()
            primary_screen = desktop.primaryScreen()
            primary_rect = desktop.screenGeometry(primary_screen)

            self.window_width = min(600, primary_rect.width() // 3)
            self.window_height = min(200, primary_rect.height() // 5)

            x_pos = primary_rect.x() + (primary_rect.width() - self.window_width) // 2
            y_pos = primary_rect.y() + primary_rect.height() - self.window_height - 40

            self.setGeometry(x_pos, y_pos, self.window_width, self.window_height)
            self.primary_rect = primary_rect

            self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.hide()
        except Exception as e:
            self.logger.error(f"Fenster-Setup Fehler: {e}")
            print(f"❌ Fenster-Setup Fehler: {e}")

    def add_text_safe(self, text):
        try:
            if not text or not isinstance(text, str):
                return False
            text = text.strip()
            if len(text) == 0:
                return False
            if len(text) > 500:
                text = text[:497] + "..."

            label = OutlinedLabel(text)
            label.setParent(self)
            label.move(20, self.y_position)
            label.show()

            self.text_labels.append(label)
            self.y_position += max(label.height() + 15, 30)
            self.adjust_window_size_safe()
            self.show_window_safe()
            return True
        except Exception as e:
            self.logger.error(f"Fehler beim Hinzufügen von Text: {e}")
            return False

    def adjust_window_size_safe(self):
        try:
            if not self.text_labels:
                return
            max_width = max((label.width() for label in self.text_labels if label), default=0)

            screen_width = self.primary_rect.width()
            screen_height = self.primary_rect.height()
            needed_width = min(max(max_width + 40, 300), min(800, screen_width // 2))
            needed_height = min(self.y_position + 40, int(screen_height * 0.8))

            x_pos = self.primary_rect.x() + (self.primary_rect.width() - needed_width) // 2
            y_pos = self.primary_rect.y() + self.primary_rect.height() - needed_height - 40

            self.setGeometry(x_pos, y_pos, needed_width, needed_height)
            self.window_width = needed_width
            self.window_height = needed_height
        except Exception as e:
            self.logger.error(f"Größenanpassung Fehler: {e}")

    def clear_all_safe(self):
        try:
            for label in self.text_labels[:]:
                try:
                    if label:
                        label.deleteLater()
                except Exception as e:
                    self.logger.warning(f"Fehler beim Löschen eines Labels: {e}")
            self.text_labels.clear()
            self.y_position = 20
            self.is_visible = False
            self.hide()
            self.window_width = 600
            self.window_height = 200
            return True
        except Exception as e:
            self.logger.error(f"Fehler beim Löschen aller Texte: {e}")
            return False

    def show_window_safe(self):
        try:
            if self.text_labels and not self.is_visible:
                self.show()
                self.is_visible = True
                self.raise_()
                self.activateWindow()
        except Exception as e:
            self.logger.error(f"Fehler beim Anzeigen: {e}")

class OutlinedLabel(QLabel):
    def __init__(self, text):
        super().__init__()
        try:
            self.setText(text)
            self.setFont(QFont('Arial', 10, QFont.Normal))
            self.setStyleSheet("color: white;")
            self.setWordWrap(True)
            self.setMaximumWidth(700)

            font_metrics = self.fontMetrics()
            text_rect = font_metrics.boundingRect(0, 0, 700, 2000, Qt.TextWordWrap, text)
            width = min(max(text_rect.width() + 15, 100), 700)
            height = min(max(text_rect.height() + 15, 25), 600)
            self.setFixedSize(width, height)
        except Exception as e:
            print(f"Fehler bei OutlinedLabel: {e}")
            self.setText(str(text)[:100])
            self.setFixedSize(300, 30)

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setFont(QFont('Arial', 10, QFont.Normal))

            text = self.text()
            rect = self.rect().adjusted(5, 5, -5, -5)

            painter.setPen(QPen(QColor(0, 0, 0, 100), 1))
            painter.drawText(rect.adjusted(1, 1, 1, 1), Qt.TextWordWrap | Qt.AlignTop, text)

            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(rect, Qt.TextWordWrap | Qt.AlignTop, text)
        except Exception:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(self.rect(), Qt.AlignCenter, self.text()[:50])

class RobustMessageReceiver(QThread):
    message_received = pyqtSignal(str, str)
    connection_status = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.host = 'localhost'
        self.port = 12345
        self.running = True
        self.server_socket = None
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def run(self):
        self.start_server_robust()

    def start_server_robust(self):
        retry_count = 0
        max_retries = 5

        while self.running and retry_count < max_retries:
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.settimeout(2.0)
                self.server_socket.bind((self.host, self.port))
                self.server_socket.listen(5)

                self.logger.info(f"✅ Overlay Server läuft auf {self.host}:{self.port}")
                self.connection_status.emit(True)
                retry_count = 0

                while self.running:
                    try:
                        conn, addr = self.server_socket.accept()
                        self.handle_connection(conn, addr)
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.running:
                            self.logger.warning(f"Fehler bei Verbindung: {e}")
                        break

            except Exception as e:
                retry_count += 1
                self.logger.error(f"Server Fehler (Versuch {retry_count}): {e}")
                self.connection_status.emit(False)
                time.sleep(min(retry_count * 2, 10))
            finally:
                self.cleanup_socket()

        self.connection_status.emit(False)
        self.logger.info("Server beendet")

    def handle_connection(self, conn, addr):
        try:
            conn.settimeout(5.0)
            with conn:
                data = conn.recv(1024)
                if data:
                    nachricht = data.decode('utf-8', errors='ignore')
                    self.verarbeite_nachricht_sicher(nachricht)
        except Exception as e:
            self.logger.warning(f"Fehler bei Verbindung: {e}")

    def verarbeite_nachricht_sicher(self, nachricht):
        try:
            if not nachricht or not isinstance(nachricht, str):
                return
            nachricht = nachricht.strip()
            if nachricht == "CLEAR":
                self.message_received.emit("CLEAR", "")
            elif nachricht.startswith("ANSWER:"):
                inhalt = nachricht[7:].strip()
                if inhalt:
                    self.message_received.emit("ANSWER", inhalt)
        except Exception as e:
            self.logger.error(f"Fehler bei Nachrichtenverarbeitung: {e}")

    def cleanup_socket(self):
        try:
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
        except Exception as e:
            self.logger.warning(f"Fehler beim Socket cleanup: {e}")

    def stop(self):
        self.running = False
        self.cleanup_socket()
        self.wait(3000)

class RobustQAOverlayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.overlay = TransparentOverlay()
        self.receiver = RobustMessageReceiver()

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.receiver.message_received.connect(self.handle_message_safe)
        self.receiver.connection_status.connect(self.handle_connection_status)

        self.clear_timer = QTimer()
        self.clear_timer.timeout.connect(self.auto_clear)
        self.clear_timer.setSingleShot(True)

    def handle_message_safe(self, typ, inhalt):
        try:
            if typ == "CLEAR":
                self.overlay.clear_all_safe()
                self.clear_timer.stop()
            elif typ == "ANSWER":
                if inhalt:
                    self.overlay.add_text_safe(inhalt)
                    self.clear_timer.stop()
                    self.clear_timer.start(4000)
        except Exception as e:
            self.logger.error(f"Fehler bei Nachrichten: {e}")

    def handle_connection_status(self, connected):
        self.logger.info("Verbindung OK" if connected else "Verbindung verloren")

    def auto_clear(self):
        try:
            self.overlay.clear_all_safe()
        except Exception as e:
            self.logger.error(f"Fehler bei Auto-Clear: {e}")

    def run(self):
        self.receiver.start()
        sys.excepthook = lambda t, v, tb: self.logger.error(f"Unbehandelte Exception: {t.__name__}: {v}")
        self.logger.info("Overlay gestartet")
        sys.exit(self.app.exec_())

    def cleanup(self):
        self.receiver.stop()
        self.clear_timer.stop()
        self.logger.info("Aufräumen abgeschlossen")

if __name__ == "__main__":
    app = RobustQAOverlayApp()
    app.run()
