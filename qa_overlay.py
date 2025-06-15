#!/usr/bin/env python3
# qa_overlay.py - Robustes PyQt5 Overlay mit Konfigurations-Support

import sys
import socket
import threading
import logging
import time
import json
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QDesktopWidget, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QFont, QPainter, QPen, QColor, QFontDatabase

class ConfigurableOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.text_labels = []
        self.y_position = 20
        self.is_visible = False
        self.config_file = Path(__file__).parent / "qa_config.json"
        self.config = self.load_config()
        
        # FileWatcher für Config-Änderungen
        self.config_watcher = QTimer()
        self.config_watcher.timeout.connect(self.check_config_changes)
        self.config_watcher.start(2000)  # Alle 2 Sekunden prüfen
        self.last_config_mtime = 0
        
        self.setup_window()
        self.setup_logging()
        
    def load_config(self):
        """Lädt Konfiguration aus Datei"""
        default_config = {
            "overlay": {
                "position": "right-middle",
                "width": 600,
                "height": 200,
                "transparency": 95,
                "auto_hide_delay": 30,
                "animation_enabled": True
            },
            "text": {
                "font_family": "Arial",
                "font_size": 12,
                "font_bold": True,
                "text_color": "#FFFFFF",
                "outline_color": "#000000",
                "outline_width": 3,
                "line_spacing": 15
            },
            "colors": {
                "background_color": "#2B2B2B",
                "question_prefix": "🔍",
                "answer_prefix": "➤",
                "error_prefix": "❌"
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge mit Defaults
                    for key in default_config:
                        if key not in loaded:
                            loaded[key] = default_config[key]
                        elif isinstance(default_config[key], dict):
                            for subkey in default_config[key]:
                                if subkey not in loaded[key]:
                                    loaded[key][subkey] = default_config[key][subkey]
                    return loaded
        except Exception as e:
            print(f"Fehler beim Laden der Config: {e}")
            
        return default_config
    
    def check_config_changes(self):
        """Prüft ob Config-Datei geändert wurde"""
        try:
            if self.config_file.exists():
                mtime = self.config_file.stat().st_mtime
                if mtime > self.last_config_mtime:
                    self.last_config_mtime = mtime
                    new_config = self.load_config()
                    if new_config != self.config:
                        self.config = new_config
                        self.apply_config()
                        self.logger.info("📋 Konfiguration neu geladen")
        except Exception as e:
            self.logger.warning(f"Fehler beim Config-Check: {e}")
        
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
        """Sichere Fenster-Konfiguration mit Config"""
        try:
            self.setWindowTitle("Q&A Overlay")
            
            # Primären Bildschirm ermitteln
            desktop = QDesktopWidget()
            if desktop is None:
                raise Exception("Kein Desktop verfügbar")
                
            primary_screen = desktop.primaryScreen()
            self.primary_rect = desktop.screenGeometry(primary_screen)
            
            if self.primary_rect.width() <= 0 or self.primary_rect.height() <= 0:
                raise Exception("Ungültige Bildschirm-Dimensionen")
            
            # Fenster-Eigenschaften
            self.setWindowFlags(
                Qt.WindowStaysOnTopHint | 
                Qt.FramelessWindowHint |
                Qt.Tool |
                Qt.WindowTransparentForInput  # Maus-Events durchlassen
            )
            
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
            
            # Konfiguration anwenden
            self.apply_config()
            self.hide()
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Fehler bei Fenster-Setup: {e}")
            print(f"❌ Fenster-Setup Fehler: {e}")
            
    def apply_config(self):
        """Wendet Konfiguration auf Overlay an"""
        try:
            # Position und Größe
            self.calculate_and_set_geometry()
            
            # Transparenz
            opacity = self.config['overlay']['transparency'] / 100.0
            self.setWindowOpacity(opacity)
            
            # Update alle existierenden Labels
            for label in self.text_labels:
                if isinstance(label, ConfigurableLabel):
                    label.update_from_config(self.config)
                    
        except Exception as e:
            self.logger.error(f"Fehler beim Anwenden der Config: {e}")
    
    def calculate_and_set_geometry(self):
        """Berechnet und setzt Fenster-Position basierend auf Config"""
        position = self.config['overlay']['position']
        width = self.config['overlay']['width']
        height = self.config['overlay']['height']
        
        screen_width = self.primary_rect.width()
        screen_height = self.primary_rect.height()
        screen_x = self.primary_rect.x()
        screen_y = self.primary_rect.y()
        
        margin = 20
        
        # Position berechnen
        if 'right' in position:
            x = screen_x + screen_width - width - margin
        elif 'left' in position:
            x = screen_x + margin
        else:  # center
            x = screen_x + (screen_width - width) // 2
            
        if 'top' in position:
            y = screen_y + margin
        elif 'bottom' in position:
            y = screen_y + screen_height - height - margin
        else:  # middle/center
            y = screen_y + (screen_height - height) // 2
            
        self.setGeometry(x, y, width, height)
        self.window_width = width
        self.window_height = height
        
    def add_text_safe(self, text, text_type='normal'):
        """Sichere Text-Hinzufügung mit Config-Support"""
        try:
            if not text or not isinstance(text, str):
                return False
                
            text = text.strip()
            if len(text) == 0:
                return False
                
            # Prefix basierend auf Typ
            if text_type == 'question' and not text.startswith(self.config['colors']['question_prefix']):
                text = f"{self.config['colors']['question_prefix']} {text}"
            elif text_type == 'answer' and not text.startswith(self.config['colors']['answer_prefix']):
                text = f"{self.config['colors']['answer_prefix']} {text}"
            elif text_type == 'error' and not text.startswith(self.config['colors']['error_prefix']):
                text = f"{self.config['colors']['error_prefix']} {text}"
                
            # Begrenze Text-Länge
            if len(text) > 500:
                text = text[:497] + "..."
            
            label = ConfigurableLabel(text, self.config)
            if label is None:
                return False
                
            label.setParent(self)
            label.move(20, self.y_position)
            
            # Animation wenn aktiviert
            if self.config['overlay']['animation_enabled']:
                self.animate_label_in(label)
            else:
                label.show()
            
            self.text_labels.append(label)
            self.y_position += label.height() + self.config['text']['line_spacing']
            
            self.adjust_window_size_safe()
            self.show_window_safe()
            
            # Auto-Hide Timer
            if self.config['overlay']['auto_hide_delay'] > 0:
                QTimer.singleShot(
                    self.config['overlay']['auto_hide_delay'] * 1000,
                    self.check_and_hide
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Hinzufügen von Text: {e}")
            return False
            
    def animate_label_in(self, label):
        """Animiert Label beim Erscheinen"""
        effect = QGraphicsOpacityEffect()
        label.setGraphicsEffect(effect)
        
        self.fade_animation = QPropertyAnimation(effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0)
        self.fade_animation.setEndValue(1)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        label.show()
        self.fade_animation.start()
        
    def check_and_hide(self):
        """Prüft ob Overlay ausgeblendet werden soll"""
        # Nur ausblenden wenn keine neuen Nachrichten kamen
        if hasattr(self, 'last_message_time'):
            if time.time() - self.last_message_time > self.config['overlay']['auto_hide_delay']:
                if self.config['overlay']['animation_enabled']:
                    self.animate_out()
                else:
                    self.hide()
                    
    def animate_out(self):
        """Animiert Overlay beim Ausblenden"""
        self.fade_out = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out.setDuration(500)
        self.fade_out.setStartValue(self.windowOpacity())
        self.fade_out.setEndValue(0)
        self.fade_out.finished.connect(self.hide)
        self.fade_out.start()
        
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
            screen_width = self.primary_rect.width()
            screen_height = self.primary_rect.height()
            
            needed_width = min(max(max_width + 40, 300), min(self.config['overlay']['width'], screen_width // 2))
            needed_height = min(self.y_position + 40, int(screen_height * 0.8))
            
            # Position neu berechnen basierend auf Config
            self.window_width = needed_width
            self.window_height = needed_height
            self.calculate_and_set_geometry()
            
        except Exception as e:
            self.logger.error(f"Fehler bei Fenster-Größenanpassung: {e}")
        
    def clear_all_safe(self):
        """Sichere Löschfunktion mit Animation"""
        try:
            if self.config['overlay']['animation_enabled'] and self.text_labels:
                # Fade out Animation
                for label in self.text_labels:
                    effect = QGraphicsOpacityEffect()
                    label.setGraphicsEffect(effect)
                    
                    fade = QPropertyAnimation(effect, b"opacity")
                    fade.setDuration(200)
                    fade.setStartValue(1)
                    fade.setEndValue(0)
                    fade.finished.connect(label.deleteLater)
                    fade.start()
                    
                QTimer.singleShot(250, self.finish_clear)
            else:
                self.finish_clear()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Fehler beim Löschen aller Texte: {e}")
            return False
            
    def finish_clear(self):
        """Beendet den Clear-Vorgang"""
        for label in self.text_labels:
            try:
                if label and label.parent():
                    label.deleteLater()
            except:
                pass
                
        self.text_labels.clear()
        self.y_position = 20
        self.is_visible = False
        self.hide()
        
        # Fenster auf konfigurierte Größe zurücksetzen
        self.window_width = self.config['overlay']['width']
        self.window_height = self.config['overlay']['height']
        
    def show_window_safe(self):
        """Sichere Fenster-Anzeige mit Animation"""
        try:
            if self.text_labels and not self.is_visible:
                self.last_message_time = time.time()
                
                if self.config['overlay']['animation_enabled']:
                    self.setWindowOpacity(0)
                    self.show()
                    
                    self.fade_in = QPropertyAnimation(self, b"windowOpacity")
                    self.fade_in.setDuration(300)
                    self.fade_in.setStartValue(0)
                    self.fade_in.setEndValue(self.config['overlay']['transparency'] / 100.0)
                    self.fade_in.start()
                else:
                    self.show()
                    
                self.is_visible = True
                self.raise_()
                
        except Exception as e:
            self.logger.error(f"Fehler beim Anzeigen des Fensters: {e}")
            
    def paintEvent(self, event):
        """Zeichnet Hintergrund mit konfigurierbarer Farbe"""
        if self.config['colors']['background_color'] != 'transparent':
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Hintergrund
            bg_color = QColor(self.config['colors']['background_color'])
            bg_color.setAlpha(200)  # Leicht transparent
            painter.fillRect(self.rect(), bg_color)
            
            # Rahmen
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

class ConfigurableLabel(QLabel):
    def __init__(self, text, config):
        super().__init__()
        self.config = config
        self.setText(text)
        self.setup_style()
        
    def setup_style(self):
        """Wendet Style aus Config an"""
        try:
            # Font
            font = QFont(
                self.config['text']['font_family'],
                self.config['text']['font_size'],
                QFont.Bold if self.config['text']['font_bold'] else QFont.Normal
            )
            self.setFont(font)
            
            # Style
            self.setStyleSheet(f"color: {self.config['text']['text_color']};")
            self.setWordWrap(True)
            self.setMaximumWidth(700)
            
            # Berechne optimale Größe
            font_metrics = self.fontMetrics()
            if font_metrics:
                text_rect = font_metrics.boundingRect(0, 0, 700, 2000, Qt.TextWordWrap, self.text())
                width = min(max(text_rect.width() + 15, 100), 700)
                height = min(max(text_rect.height() + 15, 25), 300)
                self.setFixedSize(width, height)
            else:
                self.setFixedSize(300, 30)
                
        except Exception as e:
            print(f"Fehler bei Label-Style: {e}")
            self.setFixedSize(300, 30)
            
    def update_from_config(self, config):
        """Aktualisiert Label mit neuer Config"""
        self.config = config
        self.setup_style()
        self.update()
        
    def paintEvent(self, event):
        """Zeichnet Text mit konfigurierbarem Umriss"""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            font = self.font()
            painter.setFont(font)
            
            text = self.text()
            rect = self.rect().adjusted(5, 5, -5, -5)
            
            # Umriss nur wenn Breite > 0
            if self.config['text']['outline_width'] > 0:
                # Schwarzer Umriss
                painter.setPen(QPen(
                    QColor(self.config['text']['outline_color']), 
                    self.config['text']['outline_width']
                ))
                
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx != 0 or dy != 0:
                            offset_rect = rect.adjusted(dx, dy, dx, dy)
                            painter.drawText(offset_rect, Qt.TextWordWrap | Qt.AlignTop, text)
            
            # Haupttext
            painter.setPen(QPen(QColor(self.config['text']['text_color']), 1))
            painter.drawText(rect, Qt.TextWordWrap | Qt.AlignTop, text)
            
        except Exception as e:
            # Fallback
            super().paintEvent(event)

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
                    wait_time = min(retry_count * 2, 10)
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
            pass
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
                pass
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
        self.wait(3000)

class RobustQAOverlayApp:
    def __init__(self):
        try:
            self.app = QApplication(sys.argv)
            self.app.setQuitOnLastWindowClosed(False)
            
            self.overlay = ConfigurableOverlay()
            self.receiver = RobustMessageReceiver()
            
            # Setup Logging
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            
            # Verbinde Signale
            self.receiver.message_received.connect(self.handle_message_safe)
            self.receiver.connection_status.connect(self.handle_connection_status)
            
        except Exception as e:
            print(f"❌ Fehler bei App-Initialisierung: {e}")
            sys.exit(1)
        
    def handle_message_safe(self, typ, inhalt):
        """Sichere Nachrichtenbehandlung"""
        try:
            if typ == "CLEAR":
                self.overlay.clear_all_safe()
                self.logger.debug("🧹 Overlay geleert")
                
            elif typ == "QUESTION":
                if inhalt:
                    # Entferne existierendes Prefix falls vorhanden
                    if inhalt.startswith("🔍"):
                        inhalt = inhalt[2:].strip()
                    self.overlay.add_text_safe(inhalt, 'question')
                    self.logger.debug(f"❓ Frage angezeigt: {inhalt[:30]}...")
                
            elif typ == "ANSWER":
                if inhalt:
                    # Entferne existierendes Prefix falls vorhanden
                    if inhalt.startswith("➤"):
                        inhalt = inhalt[1:].strip()
                    self.overlay.add_text_safe(inhalt, 'answer')
                    self.logger.debug(f"✅ Antwort hinzugefügt: {inhalt[:30]}...")
                    
        except Exception as e:
            self.logger.error(f"Fehler bei Nachrichtenbehandlung: {e}")
    
    def handle_connection_status(self, connected):
        """Behandelt Verbindungsstatus-Änderungen"""
        if connected:
            self.logger.info("🔗 Verbindung hergestellt")
        else:
            self.logger.warning("🔌 Verbindung verloren")
    
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
            self.logger.info("🧹 Cleanup abgeschlossen")
        except Exception as e:
            self.logger.error(f"Fehler beim Cleanup: {e}")

if __name__ == "__main__":
    app = RobustQAOverlayApp()
    app.run()