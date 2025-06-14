#!/usr/bin/env python3
# qa_finder.py - Robuster Frage-Antwort-System mit Error Handling

import json
import subprocess
import time
import socket
import threading
import sys
import logging
from difflib import get_close_matches
from datetime import datetime
from pathlib import Path

class RobustQAFinder:
    def __init__(self):
        self.host = 'localhost'
        self.port = 12345
        self.fragen = []
        self.letzter_inhalt = ""
        self.running = True
        self.connection_alive = False
        self.error_count = 0
        self.max_errors = 10
        
        # Setup Logging
        self.setup_logging()
        
        # Threading Events
        self.shutdown_event = threading.Event()
        
    def setup_logging(self):
        """Setup für strukturiertes Logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('qa_finder.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def lade_fragen_sicher(self, dateipfad):
        """Lädt Fragen mit robustem Error Handling"""
        try:
            file_path = Path(dateipfad)
            if not file_path.exists():
                self.logger.error(f"Datei nicht gefunden: {dateipfad}")
                return False
                
            if file_path.stat().st_size == 0:
                self.logger.error(f"Datei ist leer: {dateipfad}")
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not isinstance(data, list) or len(data) == 0:
                self.logger.error("JSON enthält keine gültige Fragenliste")
                return False
                
            # Validiere Datenstruktur
            valid_questions = 0
            for i, eintrag in enumerate(data):
                if self.validiere_frage(eintrag, i):
                    valid_questions += 1
                    
            if valid_questions == 0:
                self.logger.error("Keine gültigen Fragen gefunden")
                return False
                
            self.fragen = data
            self.logger.info(f"✅ {len(self.fragen)} Fragen geladen ({valid_questions} gültig)")
            return True
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON Parse Error: {e}")
        except FileNotFoundError:
            self.logger.error(f"Datei nicht gefunden: {dateipfad}")
        except PermissionError:
            self.logger.error(f"Keine Berechtigung für Datei: {dateipfad}")
        except Exception as e:
            self.logger.error(f"Unerwarteter Fehler beim Laden: {e}")
            
        return False
        
    def validiere_frage(self, eintrag, index):
        """Validiert einzelne Frage-Antwort-Einträge"""
        try:
            if not isinstance(eintrag, dict):
                self.logger.warning(f"Eintrag {index} ist kein Dictionary")
                return False
                
            if 'question' not in eintrag:
                self.logger.warning(f"Eintrag {index} hat keine 'question'")
                return False
                
            if not isinstance(eintrag['question'], str) or len(eintrag['question'].strip()) == 0:
                self.logger.warning(f"Eintrag {index} hat ungültige Frage")
                return False
                
            # Prüfe ob mindestens eine Antwort existiert
            has_answer = False
            if 'answer' in eintrag and isinstance(eintrag['answer'], str) and len(eintrag['answer'].strip()) > 0:
                has_answer = True
            elif 'answers' in eintrag and isinstance(eintrag['answers'], list) and len(eintrag['answers']) > 0:
                # Prüfe ob alle Antworten Strings sind
                if all(isinstance(ans, str) and len(ans.strip()) > 0 for ans in eintrag['answers']):
                    has_answer = True
                    
            if not has_answer:
                self.logger.warning(f"Eintrag {index} hat keine gültigen Antworten")
                return False
                
            return True
            
        except Exception as e:
            self.logger.warning(f"Fehler bei Validierung von Eintrag {index}: {e}")
            return False

    def get_clipboard_robust(self):
        """Robuste Clipboard-Abfrage mit Error Handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    ['xclip', '-selection', 'clipboard', '-o'], 
                    capture_output=True, 
                    text=True, 
                    timeout=2,
                    check=False
                )
                
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    self.logger.warning(f"xclip returned code {result.returncode}")
                    
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Clipboard timeout (Versuch {attempt + 1})")
            except FileNotFoundError:
                self.logger.error("xclip nicht installiert")
                return None
            except Exception as e:
                self.logger.warning(f"Clipboard Fehler (Versuch {attempt + 1}): {e}")
                
            if attempt < max_retries - 1:
                time.sleep(0.5)
                
        return ""

    def normalisiere_text(self, text):
        """Sichere Text-Normalisierung"""
        try:
            if not isinstance(text, str):
                return ""
            return ' '.join(text.lower().strip().split())
        except Exception as e:
            self.logger.warning(f"Fehler bei Text-Normalisierung: {e}")
            return ""

    def finde_passende_fragen_robust(self, suchtext):
        """Robuste Suche mit Error Handling"""
        try:
            if not suchtext or len(suchtext.strip()) < 3:
                return []
                
            suchtext_norm = self.normalisiere_text(suchtext)
            if not suchtext_norm:
                return []
                
            gefundene = []
            
            # 1. Exakte Übereinstimmung
            for eintrag in self.fragen:
                try:
                    if self.normalisiere_text(eintrag.get('question', '')) == suchtext_norm:
                        gefundene.append((eintrag, 100))
                except Exception as e:
                    self.logger.warning(f"Fehler bei exakter Suche: {e}")
                    continue
            
            # 2. Teilstring-Suche (nur wenn keine exakte Übereinstimmung)
            if not gefundene:
                for eintrag in self.fragen:
                    try:
                        frage_norm = self.normalisiere_text(eintrag.get('question', ''))
                        if not frage_norm:
                            continue
                            
                        if suchtext_norm in frage_norm or frage_norm in suchtext_norm:
                            ratio = min(len(suchtext_norm), len(frage_norm)) / max(len(suchtext_norm), len(frage_norm))
                            gefundene.append((eintrag, ratio * 80))
                    except Exception as e:
                        self.logger.warning(f"Fehler bei Teilstring-Suche: {e}")
                        continue
            
            # 3. Fuzzy-Matching (nur wenn immer noch nichts gefunden)
            if not gefundene:
                try:
                    fragen_texte = [eintrag.get('question', '') for eintrag in self.fragen if eintrag.get('question')]
                    matches = get_close_matches(suchtext, fragen_texte, n=3, cutoff=0.6)
                    
                    for match in matches:
                        for eintrag in self.fragen:
                            if eintrag.get('question') == match:
                                gefundene.append((eintrag, 60))
                                break
                except Exception as e:
                    self.logger.warning(f"Fehler bei Fuzzy-Matching: {e}")
            
            # Sortiere und begrenze Ergebnisse
            gefundene.sort(key=lambda x: x[1], reverse=True)
            return [eintrag for eintrag, _ in gefundene[:5]]  # Max 5 Ergebnisse
            
        except Exception as e:
            self.logger.error(f"Fehler bei Frage-Suche: {e}")
            return []

    def test_connection(self):
        """Testet die Verbindung zum Overlay"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect((self.host, self.port))
                s.sendall(b"PING")
                self.connection_alive = True
                return True
        except Exception:
            self.connection_alive = False
            return False

    def sende_nachricht_robust(self, nachricht, max_retries=3):
        """Robuste Socket-Kommunikation mit Retry-Logic"""
        if not nachricht:
            return False
            
        for attempt in range(max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3.0)
                    s.connect((self.host, self.port))
                    s.sendall(nachricht.encode('utf-8'))
                    
                    self.connection_alive = True
                    self.error_count = 0  # Reset bei erfolgreicher Übertragung
                    return True
                    
            except socket.timeout:
                self.logger.warning(f"Socket timeout (Versuch {attempt + 1})")
            except ConnectionRefusedError:
                if attempt == 0:
                    self.logger.warning("Overlay nicht verfügbar")
                self.connection_alive = False
            except Exception as e:
                self.logger.warning(f"Socket Fehler (Versuch {attempt + 1}): {e}")
                
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                
        self.error_count += 1
        self.connection_alive = False
        return False

    def sende_antworten(self, gefundene, frage):
        """Sendet Frage und Antworten mit Error Handling"""
        try:
            # Sende CLEAR Signal
            if not self.sende_nachricht_robust("CLEAR"):
                return False
                
            time.sleep(0.1)
            
            # Sende Frage
            frage_kurz = frage[:80] + "..." if len(frage) > 80 else frage
            if not self.sende_nachricht_robust(f"QUESTION:{frage_kurz}"):
                return False
            
            # Sende Antworten
            antwort_count = 0
            for eintrag in gefundene:
                try:
                    if 'answer' in eintrag:
                        if self.sende_nachricht_robust(f"ANSWER:➤ {eintrag['answer']}"):
                            antwort_count += 1
                    elif 'answers' in eintrag:
                        for antwort in eintrag['answers'][:3]:  # Max 3 Antworten pro Eintrag
                            if self.sende_nachricht_robust(f"ANSWER:➤ {antwort}"):
                                antwort_count += 1
                except Exception as e:
                    self.logger.warning(f"Fehler beim Senden einer Antwort: {e}")
                    continue
                    
            self.logger.info(f"✅ {antwort_count} Antworten gesendet")
            return antwort_count > 0
            
        except Exception as e:
            self.logger.error(f"Fehler beim Senden der Antworten: {e}")
            return False

    def monitor_clipboard_robust(self):
        """Robuste Clipboard-Überwachung mit Error Handling"""
        if not self.lade_fragen_sicher('answare.json'):
            self.logger.error("Kann nicht starten - Fehler beim Laden der Fragen")
            return
            
        self.logger.info("📋 Clipboard-Monitoring gestartet")
        self.logger.info("🎯 Antworten werden an Overlay gesendet")
        self.logger.info("⚠️  Drücke Strg+C zum Beenden")
        
        last_check = time.time()
        connection_check_interval = 10  # Alle 10 Sekunden Verbindung prüfen
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # Periodische Verbindungsprüfung
                current_time = time.time()
                if current_time - last_check > connection_check_interval:
                    self.test_connection()
                    last_check = current_time
                
                # Zu viele Fehler - Pause einlegen
                if self.error_count >= self.max_errors:
                    self.logger.warning(f"Zu viele Fehler ({self.error_count}) - Pause 30 Sekunden")
                    if self.shutdown_event.wait(30):
                        break
                    self.error_count = 0
                    continue
                
                # Clipboard abfragen
                aktueller_inhalt = self.get_clipboard_robust()
                if aktueller_inhalt is None:
                    # xclip nicht verfügbar
                    self.logger.error("xclip nicht verfügbar - beende")
                    break
                
                # Neue Frage verarbeiten
                if aktueller_inhalt and aktueller_inhalt != self.letzter_inhalt:
                    if len(aktueller_inhalt.strip()) < 8:
                        self.logger.debug(f"Text zu kurz: {len(aktueller_inhalt)} Zeichen")
                        self.letzter_inhalt = aktueller_inhalt
                        continue
                    
                    self.logger.info(f"🔍 Neue Frage: \"{aktueller_inhalt[:50]}...\"")
                    
                    # Suche passende Antworten
                    gefundene = self.finde_passende_fragen_robust(aktueller_inhalt)
                    
                    if gefundene:
                        if self.sende_antworten(gefundene, aktueller_inhalt):
                            self.logger.info(f"✅ {len(gefundene)} Antwort(en) erfolgreich gesendet")
                        else:
                            self.logger.warning("❌ Fehler beim Senden der Antworten")
                    else:
                        # Keine Antwort gefunden
                        if self.sende_nachricht_robust("CLEAR"):
                            self.sende_nachricht_robust("QUESTION:Neue Frage")
                            self.sende_nachricht_robust("ANSWER:❌ Keine Antwort gefunden")
                        self.logger.info("⚠️ Keine passende Antwort gefunden")
                    
                    self.letzter_inhalt = aktueller_inhalt
                
                # Kurze Pause
                if self.shutdown_event.wait(0.2):
                    break
                    
            except KeyboardInterrupt:
                self.logger.info("✋ Beenden durch Benutzer")
                break
            except Exception as e:
                self.error_count += 1
                self.logger.error(f"Unerwarteter Fehler: {e}")
                if self.shutdown_event.wait(1):
                    break
                    
        self.logger.info("📋 Clipboard-Monitoring beendet")

    def graceful_shutdown(self):
        """Graceful Shutdown"""
        self.logger.info("🛑 Initiiere Shutdown...")
        self.running = False
        self.shutdown_event.set()

def signal_handler(signum, frame):
    """Signal Handler für graceful shutdown"""
    finder.graceful_shutdown()

if __name__ == "__main__":
    # Signal Handler registrieren
    import signal
    
    finder = RobustQAFinder()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        finder.monitor_clipboard_robust()
    except Exception as e:
        finder.logger.error(f"Kritischer Fehler: {e}")
    finally:
        finder.graceful_shutdown()