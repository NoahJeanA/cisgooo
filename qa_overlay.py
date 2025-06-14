#!/usr/bin/env python3
# qa_overlay.py - Robustes PyQt5 Overlay mit Error Handling

import sys
import socket
import threading
import logging
import time
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QDesktopWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QFont, QPainter, QPen, QColor

class TransparentOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.text_labels = []
        self.y_position = 20
        self.is_visible = False
        self.setup_window()
        
        # Setup Logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup für strukturiertes Logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('qa_overlay.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_window(self):
        """Sichere Fenster-Konfiguration"""
        try:
            self.setWindowTitle("Q&A Overlay")
            
            # Primären Bildschirm ermitteln
            desktop = QDesktopWidget()
            if desktop is None:
                raise Exception("Kein Desktop verfügbar")
                
            primary_screen = desktop.primaryScreen()
            primary_rect = desktop.screenGeometry(primary_screen)
            
            if primary_rect.width() <= 0 or primary_rect.height() <= 0:
                raise Exception("Ungültige Bildschirm-Dimensionen")
            
            # Initial-Größe setzen
            self.window_width = min(600, primary_rect.width() // 3)
            self.window_height = min(200, primary_rect.height() // 5)
            
            # Position rechts mittig am Bildschirm
            x_pos = primary_rect.x() + primary_rect.width() - self.window_width - 20
            y_pos = primary_rect.y() + (primary_rect.height() - self.window_height) // 2
            
            # Sicherstellen dass Position im sichtbaren Bereich ist
            x_pos = max(primary_rect.x(), min(x_pos, primary_rect.x() + primary_rect.width() - self.window_width))
            y_pos = max(primary_rect.y(), min(y_pos, primary_rect.y() + primary_rect.height() - self.window_height))
            
            self.setGeometry(x_pos, y_pos, self.window_width, self.window_height)
            
            # Primären Bildschirm für spätere Berechnungen speichern
            self.primary_rect = primary_rect
            
            # Fenster-Eigenschaften
            self.setWindowFlags(
                Qt.WindowStaysOnTopHint | 
                Qt.FramelessWindowHint |
                Qt.Tool
            )
            
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.hide()
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Fehler bei Fenster-Setup: {e}")
            print(f"❌ Fenster-Setup Fehler: {e}")
            
    def add_text_safe(self, text):
        """Sichere Text-Hinzufügung mit Error Handling"""
        try:
            if not text or not isinstance(text, str):
                return False
                
            text = text.strip()
            if len(text) == 0:
                return False
                
            # Begrenze Text-Länge
            if len(text) > 500:
                text = text[:497] + "..."
            
            label = OutlinedLabel(text)
            if label is None:
                return False
                
            label.setParent(self)
            label.move(20, self.y_position)
            label.show()
            
            self.text_labels.append(label)
            self.y_position += max(label.height() + 15, 30)  # Mindest-Abstand
            
            self.adjust_window_size_safe()
            self.show_window_safe()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Hinzufügen von Text: {e}")
            return False
        
    def adjust_window_size_safe(self):
        """Sichere Fenster-Größenanpassung"""
        try:
            if not self.text_labels:
                return
                
            # Berechne benötigte Dimensionen
            max_width = 0
            for label in self.text_labels:
                try:
                    if label and hasattr(label, 'width'):
                        max_width = max(max_width, label.width())
                except Exception:
                    continue
            
            # Sichere Grenzen setzen
            screen_width = getattr(self.primary_rect, 'width', lambda: 1920)()
            screen_height = getattr(self.primary_rect, 'height', lambda: 1080)()
            
            needed_width = min(max(max_width + 40, 300), min(800, screen_width // 2))
            needed_height = min(self.y_position + 40, int(screen_height * 0.8))
            
            # Neue Position berechnen
            x_pos = self.primary_rect.x() + self.primary_rect.width() - needed_width - 20
            y_pos = self.primary_rect.y() + (self.primary_rect.height() - needed_height) // 2
            
            # Position validieren
            x_pos = max(self.primary_rect.x(), min(x_pos, self.primary_rect.x() + self.primary_rect.width() - needed_width))
            y_pos = max(self.primary_rect.y(), min(y_pos, self.primary_rect.y() + self.primary_rect.height() - needed_height))
            
            # Fenster anpassen
            self.setGeometry(x_pos, y_pos, needed_width, needed_height)
            self.window_width = needed_width
            self.window_height = needed_height
            
        except Exception as e:
            self.logger.error(f"Fehler bei Fenster-Größenanpassung: {e}")
        
    def clear_all_safe(self):
        """Sichere Löschfunktion"""
        try:
            # Labels sicher löschen
            for label in self.text_labels[:]:  # Kopie der Liste
                try:
                    if label:
                        label.deleteLater()
                except Exception as e:
                    self.logger.warning(f"Fehler beim Löschen eines Labels: {e}")
                    
            self.text_labels.clear()
            self.y_position = 20
            self.is_visible = False
            self.hide()
            
            # Fenster auf ursprüngliche Größe zurücksetzen
            self.window_width = 600
            self.window_height = 200
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Löschen aller Texte: {e}")
            return False
        
    def show_window_safe(self):
        """Sichere Fenster-Anzeige"""
        try:
            if self.text_labels and not self.is_visible:
                self.show()
                self.is_visible = True
                self.raise_()  # Fenster in den Vordergrund
                self.activateWindow()
        except Exception as e:
            self.logger.error(f"Fehler beim Anzeigen des Fensters: {e}")

class OutlinedLabel(QLabel):
    def __init__(self, text):
        super().__init__()
        try:
            self.setText(text)
            self.setFont(QFont('Arial', 12, QFont.Bold))
            self.setStyleSheet("color: white;")
            
            # Sichere Text-Anpassung
            self.setWordWrap(True)
            self.setMaximumWidth(700)
            
            # Berechne optimale Größe
            font_metrics = self.fontMetrics()
            if font_metrics:
                text_rect = font_metrics.boundingRect(0, 0, 700, 2000, Qt.TextWordWrap, text)
                width = min(max(text_rect.width() + 15, 100), 700)
                height = min(max(text_rect.height() + 15, 25), 300)
                self.setFixedSize(width, height)
            else:
                # Fallback-Größe
                self.setFixedSize(300, 30)
                
        except Exception as e:
            print(f"Fehler bei OutlinedLabel: {e}")
            # Fallback-Konfiguration
            self.setText(str(text)[:100])
            self.setFixedSize(300, 30)
        
    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            font = QFont('Arial', 12, QFont.Bold)
            painter.setFont(font)
            
            text = self.text()
            rect = self.rect().adjusted(5, 5, -5, -5)
            
            # Schwarzer Umriss
            painter.setPen(QPen(QColor(0, 0, 0), 3))
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx != 0 or dy != 0:
                        offset_rect = rect.adjusted(dx, dy, dx, dy)
                        painter.drawText(offset_rect, Qt.TextWordWrap | Qt.AlignTop, text)
            
            # Weißer Text
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(rect, Qt.TextWordWrap | Qt.AlignTop, text)
            
        except Exception as e:
            # Fallback: Einfacher Text ohne Umriss
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
        
        # Setup Logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Robuster Server-Thread"""
        self.start_server_robust()
        
    def start_server_robust(self):
        """Startet Server mit Error Handling und Reconnection"""
        retry_count = 0
        max_retries = 5
        
        while self.running and retry_count < max_retries:
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.settimeout(2.0)
                
                self.server_socket.bind((self.host, self.port))
                self.server_socket.listen(5)  # Mehr Verbindungen erlauben
                
                self.logger.info(f"✅ Overlay Server läuft auf {self.host}:{self.port}")
                self.connection_status.emit(True)
                retry_count = 0  # Reset bei erfolgreichem Start
                
                while self.running:
                    try:
                        conn, addr = self.server_socket.accept()
                        self.handle_connection(conn, addr)
                        
                    except socket.timeout:
                        continue  # Normal bei Timeout
                    except socket.error as e:
                        if self.running:
                            self.logger.warning(f"Socket Accept Fehler: {e}")
                        break
                    except Exception as e:
                        if self.running:
                            self.logger.error(f"Unerwarteter Fehler bei Accept: {e}")
                        break
                        
            except socket.error as e:
                retry_count += 1
                self.logger.error(f"Server Start Fehler (Versuch {retry_count}): {e}")
                self.connection_status.emit(False)
                
                if retry_count < max_retries and self.running:
                    wait_time = min(retry_count * 2, 10)  # Exponential backoff, max 10s
                    self.logger.info(f"Wiederholung in {wait_time} Sekunden...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                self.logger.error(f"Kritischer Server Fehler: {e}")
                break
                
            finally:
                self.cleanup_socket()
                
        self.connection_status.emit(False)
        self.logger.info("Server beendet")
    
    def handle_connection(self, conn, addr):
        """Behandelt einzelne Verbindung"""
        try:
            conn.settimeout(5.0)
            with conn:
                data = conn.recv(1024)
                if data:
                    nachricht = data.decode('utf-8', errors='ignore')
                    self.verarbeite_nachricht_sicher(nachricht)
                    
        except socket.timeout:
            pass  # Normal bei Timeout
        except Exception as e:
            self.logger.warning(f"Fehler bei Verbindungsbehandlung: {e}")
    
    def verarbeite_nachricht_sicher(self, nachricht):
        """Sichere Nachrichtenverarbeitung"""
        try:
            if not nachricht or not isinstance(nachricht, str):
                return
                
            nachricht = nachricht.strip()
            
            if nachricht == "CLEAR":
                self.message_received.emit("CLEAR", "")
            elif nachricht == "PING":
                pass  # Heartbeat - keine Aktion nötig
            elif nachricht.startswith("QUESTION:"):
                inhalt = nachricht[9:].strip()
                if inhalt:
                    self.message_received.emit("QUESTION", inhalt)
            elif nachricht.startswith("ANSWER:"):
                inhalt = nachricht[7:].strip()
                if inhalt:
                    self.message_received.emit("ANSWER", inhalt)
            else:
                self.logger.warning(f"Unbekannte Nachricht: {nachricht[:50]}")
                
        except Exception as e:
            self.logger.error(f"Fehler bei Nachrichtenverarbeitung: {e}")
    
    def cleanup_socket(self):
        """Socket sicher schließen"""
        try:
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
        except Exception as e:
            self.logger.warning(f"Fehler beim Socket cleanup: {e}")
    
    def stop(self):
        """Graceful Stop"""
        self.running = False
        self.cleanup_socket()
        self.wait(3000)  # Warte max 3 Sekunden auf Thread-Ende

class RobustQAOverlayApp:
    def __init__(self):
        try:
            self.app = QApplication(sys.argv)
            self.app.setQuitOnLastWindowClosed(False)  # App läuft weiter wenn Fenster geschlossen
            
            self.overlay = TransparentOverlay()
            self.receiver = RobustMessageReceiver()
            
            # Setup Logging
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            
            # Verbinde Signale
            self.receiver.message_received.connect(self.handle_message_safe)
            self.receiver.connection_status.connect(self.handle_connection_status)
            
            # Timer für automatisches Löschen
            self.clear_timer = QTimer()
            self.clear_timer.timeout.connect(self.auto_clear)
            self.clear_timer.setSingleShot(True)
            
        except Exception as e:
            print(f"❌ Fehler bei App-Initialisierung: {e}")
            sys.exit(1)
        
    def handle_message_safe(self, typ, inhalt):
        """Sichere Nachrichtenbehandlung"""
        try:
            if typ == "CLEAR":
                self.overlay.clear_all_safe()
                self.clear_timer.stop()
                self.logger.debug("🧹 Overlay geleert")
                
            elif typ == "QUESTION":
                if inhalt:
                    self.overlay.add_text_safe(f"🔍 {inhalt}")
                    self.clear_timer.start(2000)  # 2 Sekunden
                    self.logger.debug(f"❓ Frage angezeigt: {inhalt[:30]}...")
                
            elif typ == "ANSWER":
                if inhalt:
                    self.overlay.add_text_safe(inhalt)
                    self.logger.debug(f"✅ Antwort hinzugefügt: {inhalt[:30]}...")
                    
        except Exception as e:
            self.logger.error(f"Fehler bei Nachrichtenbehandlung: {e}")
    
    def handle_connection_status(self, connected):
        """Behandelt Verbindungsstatus-Änderungen"""
        if connected:
            self.logger.info("🔗 Verbindung hergestellt")
        else:
            self.logger.warning("🔌 Verbindung verloren")
    
    def auto_clear(self):
        """Automatisches Löschen nach Timer"""
        try:
            self.overlay.clear_all_safe()
        except Exception as e:
            self.logger.error(f"Fehler beim automatischen Löschen: {e}")
    
    def run(self):
        """Startet die Anwendung"""
        try:
            # Starte Message Receiver
            self.receiver.start()
            
            # Exception Handler für Qt
            def handle_exception(exc_type, exc_value, exc_traceback):
                self.logger.error(f"Unbehandelte Exception: {exc_type.__name__}: {exc_value}")
            
            sys.excepthook = handle_exception
            
            self.logger.info("🎯 Overlay gestartet - warte auf Nachrichten...")
            
            # Starte Qt Event Loop
            sys.exit(self.app.exec_())
            
        except KeyboardInterrupt:
            self.logger.info("✋ Overlay beendet durch Benutzer")
        except Exception as e:
            self.logger.error(f"Kritischer Fehler: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup bei Beendigung"""
        try:
            self.receiver.stop()
            self.clear_timer.stop()
            self.logger.info("🧹 Cleanup abgeschlossen")
        except Exception as e:
            self.logger.error(f"Fehler beim Cleanup: {e}")

if __name__ == "__main__":
    app = RobustQAOverlayApp()
    app.run()