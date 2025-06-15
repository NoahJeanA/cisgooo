#!/usr/bin/env python3
# qa_overlay_gnome.py - GNOME-optimiertes Overlay mit besserer Desktop-Integration

import sys
import socket
import threading
import logging
import time
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QDesktopWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QRect
from PyQt5.QtGui import QFont, QPainter, QPen, QColor, QScreen
from PyQt5.QtDBus import QDBusConnection, QDBusInterface

class GnomeTransparentOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.text_labels = []
        self.y_position = 20
        self.is_visible = False
        self.desktop_env = self.detect_desktop_environment()
        self.primary_screen = None
        self.setup_logging()
        self.setup_window()
        self.setup_gnome_integration()

    def detect_desktop_environment(self):
        """Erkennt die Desktop-Umgebung für optimale Integration"""
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
        session = os.environ.get('DESKTOP_SESSION', '').lower()
        
        if 'gnome' in desktop or 'gnome' in session:
            return 'gnome'
        elif 'kde' in desktop or 'plasma' in session:
            return 'kde'
        elif 'xfce' in desktop:
            return 'xfce'
        else:
            return 'unknown'

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[logging.StreamHandler(), logging.FileHandler('qa_overlay_gnome.log')]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Desktop-Umgebung erkannt: {self.desktop_env}")

    def setup_gnome_integration(self):
        """Setup für GNOME-spezifische Features"""
        if self.desktop_env == 'gnome':
            try:
                # D-Bus Verbindung für GNOME Shell Integration
                self.dbus_connection = QDBusConnection.sessionBus()
                if self.dbus_connection.isConnected():
                    self.logger.info("✅ D-Bus Verbindung für GNOME Shell hergestellt")
                else:
                    self.logger.warning("⚠️  D-Bus Verbindung fehlgeschlagen")
            except Exception as e:
                self.logger.warning(f"D-Bus Setup Fehler: {e}")

    def get_optimal_screen_geometry(self):
        """Ermittelt optimale Bildschirmgeometrie für GNOME"""
        try:
            app = QApplication.instance()
            if not app:
                return QRect(0, 0, 1920, 1080)
            
            # Primären Bildschirm ermitteln
            primary_screen = app.primaryScreen()
            if not primary_screen:
                return QRect(0, 0, 1920, 1080)
                
            self.primary_screen = primary_screen
            geometry = primary_screen.geometry()
            available_geometry = primary_screen.availableGeometry()
            
            self.logger.info(f"Bildschirmgeometrie: {geometry.width()}x{geometry.height()}")
            self.logger.info(f"Verfügbare Geometrie: {available_geometry.width()}x{available_geometry.height()}")
            
            # GNOME Panel/Dock berücksichtigen
            if self.desktop_env == 'gnome':
                # GNOME hat normalerweise ein Top Panel (ca. 32px) und evtl. Dock
                panel_height = 35  # Etwas mehr Puffer für Top Panel
                dock_width = 0     # Dock ist normalerweise auto-hide
                
                # Angepasste verfügbare Geometrie
                adjusted_geometry = QRect(
                    available_geometry.x(),
                    available_geometry.y() + panel_height,
                    available_geometry.width() - dock_width,
                    available_geometry.height() - panel_height
                )
                return adjusted_geometry
            
            return available_geometry
            
        except Exception as e:
            self.logger.error(f"Fehler bei Bildschirmgeometrie: {e}")
            return QRect(0, 0, 1920, 1080)

    def setup_window(self):
        """Optimierte Fenster-Konfiguration für GNOME"""
        try:
            self.setWindowTitle("Q&A Overlay")
            
            # Bildschirmgeometrie ermitteln
            screen_geometry = self.get_optimal_screen_geometry()
            
            # Fenstergröße berechnen
            self.window_width = min(650, screen_geometry.width() // 3)
            self.window_height = min(250, screen_geometry.height() // 4)
            
            # Position: Unten mittig, aber über der GNOME Taskleiste
            x_pos = screen_geometry.x() + (screen_geometry.width() - self.window_width) // 2
            y_pos = screen_geometry.y() + screen_geometry.height() - self.window_height - 20
            
            self.setGeometry(x_pos, y_pos, self.window_width, self.window_height)
            self.screen_geometry = screen_geometry
            
            # GNOME-optimierte Window Flags
            if self.desktop_env == 'gnome':
                # Für GNOME: Immer im Vordergrund, aber nicht störend
                self.setWindowFlags(
                    Qt.WindowStaysOnTopHint | 
                    Qt.FramelessWindowHint | 
                    Qt.Tool |
                    Qt.X11BypassWindowManagerHint  # Umgeht Window Manager für bessere Position
                )
            else:
                # Fallback für andere Desktop-Umgebungen
                self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
            
            # Transparenz aktivieren
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_ShowWithoutActivating)  # Nicht fokussieren beim Anzeigen
            
            # Fenster initial verstecken
            self.hide()
            
        except Exception as e:
            self.logger.error(f"Fenster-Setup Fehler: {e}")
            # Fallback-Geometrie
            self.setGeometry(100, 100, 600, 200)

    def add_text_safe(self, text):
        """Sicheres Hinzufügen von Text mit GNOME-Optimierungen"""
        try:
            if not text or not isinstance(text, str):
                return False
            
            text = text.strip()
            if len(text) == 0:
                return False
            
            # Text kürzen falls zu lang
            if len(text) > 500:
                text = text[:497] + "..."

            # Label erstellen
            label = GnomeOptimizedLabel(text)
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
        """GNOME-optimierte Fenstergrößenanpassung"""
        try:
            if not self.text_labels:
                return
            
            # Maximale Labelbreite ermitteln
            max_width = max((label.width() for label in self.text_labels if label), default=0)
            
            # GNOME-freundliche Dimensionen
            screen_width = self.screen_geometry.width()
            screen_height = self.screen_geometry.height()
            
            # Breite: Maximal 40% des Bildschirms
            needed_width = min(max(max_width + 40, 350), int(screen_width * 0.4))
            
            # Höhe: Maximal 30% des Bildschirms
            needed_height = min(self.y_position + 40, int(screen_height * 0.3))
            
            # Position neu berechnen (zentriert unten)
            x_pos = self.screen_geometry.x() + (self.screen_geometry.width() - needed_width) // 2
            y_pos = self.screen_geometry.y() + self.screen_geometry.height() - needed_height - 40
            
            self.setGeometry(x_pos, y_pos, needed_width, needed_height)
            self.window_width = needed_width
            self.window_height = needed_height
            
        except Exception as e:
            self.logger.error(f"Größenanpassung Fehler: {e}")

    def clear_all_safe(self):
        """Sicheres Löschen aller Inhalte"""
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
            
            # Ursprüngliche Größe wiederherstellen
            self.window_width = min(650, self.screen_geometry.width() // 3)
            self.window_height = min(250, self.screen_geometry.height() // 4)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Löschen aller Texte: {e}")
            return False

    def show_window_safe(self):
        """GNOME-optimierte Fensteranzeige"""
        try:
            if self.text_labels and not self.is_visible:
                # Fenster anzeigen
                self.show()
                self.is_visible = True
                
                # GNOME-spezifische Optimierungen
                if self.desktop_env == 'gnome':
                    # Fenster in den Vordergrund bringen, aber nicht fokussieren
                    self.raise_()
                    # Sicherstellen, dass es über anderen Fenstern liegt
                    self.activateWindow()
                    
        except Exception as e:
            self.logger.error(f"Fehler beim Anzeigen: {e}")

class GnomeOptimizedLabel(QLabel):
    """GNOME-optimiertes Label mit besserer Textdarstellung"""
    
    def __init__(self, text):
        super().__init__()
        try:
            self.setText(text)
            
            # GNOME-freundliche Schriftart
            font = QFont()
            font.setFamily('Ubuntu')  # Fallback auf Ubuntu-Font
            if not font.exactMatch():
                font.setFamily('DejaVu Sans')  # Fallback
            font.setPointSize(10)
            font.setWeight(QFont.Normal)
            
            self.setFont(font)
            self.setStyleSheet("""
                QLabel {
                    color: white;
                    background-color: transparent;
                    padding: 2px;
                }
            """)
            
            self.setWordWrap(True)
            self.setMaximumWidth(700)
            
            # Größe basierend auf Text berechnen
            font_metrics = self.fontMetrics()
            text_rect = font_metrics.boundingRect(0, 0, 700, 2000, Qt.TextWordWrap, text)
            
            width = min(max(text_rect.width() + 15, 100), 700)
            height = min(max(text_rect.height() + 15, 25), 600)
            
            self.setFixedSize(width, height)
            
        except Exception as e:
            print(f"Fehler bei GnomeOptimizedLabel: {e}")
            self.setText(str(text)[:100])
            self.setFixedSize(300, 30)

    def paintEvent(self, event):
        """Verbesserte Textdarstellung mit Outline für bessere Lesbarkeit"""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.TextAntialiasing)
            
            font = self.font()
            painter.setFont(font)
            
            text = self.text()
            rect = self.rect().adjusted(5, 5, -5, -5)
            
            # Schatten für bessere Lesbarkeit
            painter.setPen(QPen(QColor(0, 0, 0, 150), 2))
            painter.drawText(rect.adjusted(1, 1, 1, 1), Qt.TextWordWrap | Qt.AlignTop, text)
            
            # Haupttext in Weiß
            painter.setPen(QPen(QColor(255, 255, 255, 255), 1))
            painter.drawText(rect, Qt.TextWordWrap | Qt.AlignTop, text)
            
        except Exception as e:
            # Fallback bei Fehlern
            painter = QPainter(self)
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(self.rect(), Qt.AlignCenter, self.text()[:50])

class GnomeMessageReceiver(QThread):
    """GNOME-optimierter Message Receiver mit verbesserter Stabilität"""
    
    message_received = pyqtSignal(str, str)
    connection_status = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.host = 'localhost'
        self.port = 12345
        self.running = True
        self.server_socket = None
        self.desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def run(self):
        self.start_server_robust()

    def start_server_robust(self):
        """Robuster Server-Start mit GNOME-Optimierungen"""
        retry_count = 0
        max_retries = 5

        while self.running and retry_count < max_retries:
            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.settimeout(2.0)
                self.server_socket.bind((self.host, self.port))
                self.server_socket.listen(5)

                self.logger.info(f"✅ GNOME Overlay Server läuft auf {self.host}:{self.port}")
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
                            self.logger.warning(f"Verbindungsfehler: {e}")
                        break

            except Exception as e:
                retry_count += 1
                self.logger.error(f"Server Fehler (Versuch {retry_count}): {e}")
                self.connection_status.emit(False)
                time.sleep(min(retry_count * 2, 10))
            finally:
                self.cleanup_socket()

        self.connection_status.emit(False)
        self.logger.info("GNOME Server beendet")

    def handle_connection(self, conn, addr):
        """Verbindungsbehandlung"""
        try:
            conn.settimeout(5.0)
            with conn:
                data = conn.recv(1024)
                if data:
                    nachricht = data.decode('utf-8', errors='ignore')
                    self.verarbeite_nachricht_sicher(nachricht)
        except Exception as e:
            self.logger.warning(f"Verbindungsfehler: {e}")

    def verarbeite_nachricht_sicher(self, nachricht):
        """Sichere Nachrichtenverarbeitung"""
        try:
            if not nachricht or not isinstance(nachricht, str):
                return
            
            nachricht = nachricht.strip()
            
            if nachricht == "CLEAR":
                self.message_received.emit("CLEAR", "")
            elif nachricht.startswith("QUESTION:"):
                inhalt = nachricht[9:].strip()
                if inhalt:
                    self.message_received.emit("QUESTION", inhalt)
            elif nachricht.startswith("ANSWER:"):
                inhalt = nachricht[7:].strip()
                if inhalt:
                    self.message_received.emit("ANSWER", inhalt)
                    
        except Exception as e:
            self.logger.error(f"Nachrichtenverarbeitungsfehler: {e}")

    def cleanup_socket(self):
        """Socket-Cleanup"""
        try:
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
        except Exception as e:
            self.logger.warning(f"Socket cleanup Fehler: {e}")

    def stop(self):
        """Stoppen des Receivers"""
        self.running = False
        self.cleanup_socket()
        self.wait(3000)

class GnomeQAOverlayApp:
    """Hauptapplikation mit GNOME-Integration"""
    
    def __init__(self):
        # QApplication mit GNOME-spezifischen Flags
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Q&A Overlay")
        self.app.setApplicationVersion("1.0")
        self.app.setOrganizationName("QA-System")
        
        # GNOME-spezifische Application Eigenschaften
        if 'gnome' in os.environ.get('XDG_CURRENT_DESKTOP', '').lower():
            self.app.setAttribute(Qt.AA_UseHighDpiPixmaps)
            self.app.setAttribute(Qt.AA_EnableHighDpiScaling)
        
        self.app.setQuitOnLastWindowClosed(False)
        
        # Komponenten initialisieren
        self.overlay = GnomeTransparentOverlay()
        self.receiver = GnomeMessageReceiver()

        # Logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Signal-Verbindungen
        self.receiver.message_received.connect(self.handle_message_safe)
        self.receiver.connection_status.connect(self.handle_connection_status)

        # Auto-Clear Timer
        self.clear_timer = QTimer()
        self.clear_timer.timeout.connect(self.auto_clear)
        self.clear_timer.setSingleShot(True)

        self.logger.info("GNOME Q&A Overlay initialisiert")

    def handle_message_safe(self, typ, inhalt):
        """Sichere Nachrichtenbehandlung"""
        try:
            if typ == "CLEAR":
                self.overlay.clear_all_safe()
                self.clear_timer.stop()
            elif typ == "QUESTION":
                # Frage wird momentan nicht separat angezeigt
                pass
            elif typ == "ANSWER":
                if inhalt:
                    self.overlay.add_text_safe(inhalt)
                    self.clear_timer.stop()
                    self.clear_timer.start(5000)  # 5 Sekunden Auto-Clear
                    
        except Exception as e:
            self.logger.error(f"Nachrichtenbehandlungsfehler: {e}")

    def handle_connection_status(self, connected):
        """Verbindungsstatus-Handler"""
        status = "Verbindung OK" if connected else "Verbindung verloren"
        self.logger.info(f"GNOME Integration: {status}")

    def auto_clear(self):
        """Automatisches Löschen des Overlays"""
        try:
            self.overlay.clear_all_safe()
            self.logger.debug("Auto-Clear ausgeführt")
        except Exception as e:
            self.logger.error(f"Auto-Clear Fehler: {e}")

    def run(self):
        """Hauptschleife starten"""
        try:
            self.receiver.start()
            
            # Exception Handler für unbehandelte Fehler
            sys.excepthook = lambda t, v, tb: self.logger.error(f"Unbehandelte Exception: {t.__name__}: {v}")
            
            self.logger.info("GNOME Q&A Overlay gestartet")
            
            # Qt Event Loop starten
            sys.exit(self.app.exec_())
            
        except Exception as e:
            self.logger.error(f"Kritischer Fehler: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup beim Beenden"""
        try:
            self.receiver.stop()
            self.clear_timer.stop()
            self.logger.info("GNOME Q&A Overlay Cleanup abgeschlossen")
        except Exception as e:
            self.logger.error(f"Cleanup Fehler: {e}")

if __name__ == "__main__":
    app = GnomeQAOverlayApp()
    app.run()
