#!/usr/bin/env python3
# qa_config_gui.py - GUI für Q&A Overlay Konfiguration

import sys
import json
import os
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QSpinBox, QSlider,
                           QComboBox, QColorDialog, QGroupBox, QGridLayout,
                           QCheckBox, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette

class ConfigGUI(QMainWindow):
    settings_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.config_file = Path(__file__).parent / "qa_config.json"
        self.default_config = {
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
        
        self.current_config = self.load_config()
        self.init_ui()
        self.apply_current_config()
        
    def load_config(self):
        """Lädt Konfiguration aus Datei oder erstellt Default"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge mit Defaults für fehlende Werte
                    return self.merge_configs(self.default_config, loaded)
            return self.default_config.copy()
        except Exception as e:
            print(f"Fehler beim Laden der Config: {e}")
            return self.default_config.copy()
    
    def merge_configs(self, default, loaded):
        """Merged loaded config mit defaults"""
        merged = default.copy()
        for key, value in loaded.items():
            if key in merged and isinstance(merged[key], dict):
                merged[key] = self.merge_configs(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    def save_config(self):
        """Speichert Konfiguration in Datei"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_config, f, indent=2, ensure_ascii=False)
            self.settings_changed.emit()
            return True
        except Exception as e:
            print(f"Fehler beim Speichern: {e}")
            return False
    
    def init_ui(self):
        """Initialisiert die Benutzeroberfläche"""
        self.setWindowTitle("Q&A Overlay Konfiguration")
        self.setFixedSize(600, 700)
        
        # Hauptwidget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Position & Größe
        position_group = self.create_position_group()
        main_layout.addWidget(position_group)
        
        # Text-Einstellungen
        text_group = self.create_text_group()
        main_layout.addWidget(text_group)
        
        # Farben
        color_group = self.create_color_group()
        main_layout.addWidget(color_group)
        
        # Weitere Einstellungen
        misc_group = self.create_misc_group()
        main_layout.addWidget(misc_group)
        
        # Preview
        preview_group = self.create_preview_group()
        main_layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Speichern")
        self.save_btn.clicked.connect(self.save_settings)
        
        self.reset_btn = QPushButton("🔄 Zurücksetzen")
        self.reset_btn.clicked.connect(self.reset_settings)
        
        self.apply_btn = QPushButton("✅ Anwenden")
        self.apply_btn.clicked.connect(self.apply_settings)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.apply_btn)
        
        main_layout.addLayout(button_layout)
        
        # Style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#resetBtn {
                background-color: #ff9800;
            }
            QPushButton#resetBtn:hover {
                background-color: #e68900;
            }
        """)
        
        self.reset_btn.setObjectName("resetBtn")
    
    def create_position_group(self):
        """Erstellt Position & Größe Gruppe"""
        group = QGroupBox("📍 Position & Größe")
        layout = QGridLayout()
        
        # Position
        layout.addWidget(QLabel("Position:"), 0, 0)
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            "right-top", "right-middle", "right-bottom",
            "left-top", "left-middle", "left-bottom",
            "center-top", "center", "center-bottom"
        ])
        self.position_combo.currentTextChanged.connect(self.update_preview)
        layout.addWidget(self.position_combo, 0, 1)
        
        # Breite
        layout.addWidget(QLabel("Breite:"), 1, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(200, 1200)
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(self.update_preview)
        layout.addWidget(self.width_spin, 1, 1)
        
        # Höhe
        layout.addWidget(QLabel("Initial-Höhe:"), 2, 0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 800)
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(self.update_preview)
        layout.addWidget(self.height_spin, 2, 1)
        
        # Transparenz
        layout.addWidget(QLabel("Transparenz:"), 3, 0)
        self.transparency_slider = QSlider(Qt.Horizontal)
        self.transparency_slider.setRange(50, 100)
        self.transparency_slider.valueChanged.connect(self.update_transparency_label)
        layout.addWidget(self.transparency_slider, 3, 1)
        
        self.transparency_label = QLabel("95%")
        layout.addWidget(self.transparency_label, 3, 2)
        
        group.setLayout(layout)
        return group
    
    def create_text_group(self):
        """Erstellt Text-Einstellungen Gruppe"""
        group = QGroupBox("📝 Text-Einstellungen")
        layout = QGridLayout()
        
        # Schriftart
        layout.addWidget(QLabel("Schriftart:"), 0, 0)
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Arial", "Helvetica", "Times New Roman", 
                                "Courier New", "Verdana", "Tahoma"])
        self.font_combo.currentTextChanged.connect(self.update_preview)
        layout.addWidget(self.font_combo, 0, 1)
        
        # Schriftgröße
        layout.addWidget(QLabel("Schriftgröße:"), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.valueChanged.connect(self.update_preview)
        layout.addWidget(self.font_size_spin, 1, 1)
        
        # Fett
        self.font_bold_check = QCheckBox("Fett")
        self.font_bold_check.stateChanged.connect(self.update_preview)
        layout.addWidget(self.font_bold_check, 2, 1)
        
        # Zeilenabstand
        layout.addWidget(QLabel("Zeilenabstand:"), 3, 0)
        self.line_spacing_spin = QSpinBox()
        self.line_spacing_spin.setRange(10, 30)
        self.line_spacing_spin.setSuffix(" px")
        self.line_spacing_spin.valueChanged.connect(self.update_preview)
        layout.addWidget(self.line_spacing_spin, 3, 1)
        
        # Umriss-Breite
        layout.addWidget(QLabel("Umriss-Breite:"), 4, 0)
        self.outline_width_spin = QSpinBox()
        self.outline_width_spin.setRange(0, 5)
        self.outline_width_spin.setSuffix(" px")
        self.outline_width_spin.valueChanged.connect(self.update_preview)
        layout.addWidget(self.outline_width_spin, 4, 1)
        
        group.setLayout(layout)
        return group
    
    def create_color_group(self):
        """Erstellt Farben Gruppe"""
        group = QGroupBox("🎨 Farben")
        layout = QGridLayout()
        
        # Text-Farbe
        layout.addWidget(QLabel("Text-Farbe:"), 0, 0)
        self.text_color_btn = QPushButton()
        self.text_color_btn.setFixedSize(100, 30)
        self.text_color_btn.clicked.connect(lambda: self.choose_color('text'))
        layout.addWidget(self.text_color_btn, 0, 1)
        
        # Umriss-Farbe
        layout.addWidget(QLabel("Umriss-Farbe:"), 1, 0)
        self.outline_color_btn = QPushButton()
        self.outline_color_btn.setFixedSize(100, 30)
        self.outline_color_btn.clicked.connect(lambda: self.choose_color('outline'))
        layout.addWidget(self.outline_color_btn, 1, 1)
        
        # Hintergrund-Farbe
        layout.addWidget(QLabel("Hintergrund:"), 2, 0)
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedSize(100, 30)
        self.bg_color_btn.clicked.connect(lambda: self.choose_color('background'))
        layout.addWidget(self.bg_color_btn, 2, 1)
        
        group.setLayout(layout)
        return group
    
    def create_misc_group(self):
        """Erstellt weitere Einstellungen"""
        group = QGroupBox("⚙️ Weitere Einstellungen")
        layout = QGridLayout()
        
        # Auto-Hide
        layout.addWidget(QLabel("Auto-Ausblenden:"), 0, 0)
        self.auto_hide_spin = QSpinBox()
        self.auto_hide_spin.setRange(0, 120)
        self.auto_hide_spin.setSuffix(" Sek")
        self.auto_hide_spin.setSpecialValueText("Deaktiviert")
        layout.addWidget(self.auto_hide_spin, 0, 1)
        
        # Animationen
        self.animation_check = QCheckBox("Animationen aktiviert")
        layout.addWidget(self.animation_check, 1, 0, 1, 2)
        
        group.setLayout(layout)
        return group
    
    def create_preview_group(self):
        """Erstellt Preview-Bereich"""
        group = QGroupBox("👁️ Vorschau")
        layout = QVBoxLayout()
        
        self.preview_frame = QFrame()
        self.preview_frame.setFixedHeight(100)
        self.preview_frame.setStyleSheet("border: 1px solid #ccc; border-radius: 5px;")
        
        preview_layout = QVBoxLayout(self.preview_frame)
        
        self.preview_question = QLabel("🔍 Beispiel-Frage?")
        self.preview_answer = QLabel("➤ Beispiel-Antwort")
        
        preview_layout.addWidget(self.preview_question)
        preview_layout.addWidget(self.preview_answer)
        
        layout.addWidget(self.preview_frame)
        group.setLayout(layout)
        return group
    
    def choose_color(self, color_type):
        """Öffnet Farbauswahl-Dialog"""
        current_color = QColor()
        
        if color_type == 'text':
            current_color.setNamedColor(self.current_config['text']['text_color'])
        elif color_type == 'outline':
            current_color.setNamedColor(self.current_config['text']['outline_color'])
        elif color_type == 'background':
            current_color.setNamedColor(self.current_config['colors']['background_color'])
        
        color = QColorDialog.getColor(current_color, self, f"{color_type.capitalize()} Farbe wählen")
        
        if color.isValid():
            if color_type == 'text':
                self.current_config['text']['text_color'] = color.name()
                self.text_color_btn.setStyleSheet(f"background-color: {color.name()}")
            elif color_type == 'outline':
                self.current_config['text']['outline_color'] = color.name()
                self.outline_color_btn.setStyleSheet(f"background-color: {color.name()}")
            elif color_type == 'background':
                self.current_config['colors']['background_color'] = color.name()
                self.bg_color_btn.setStyleSheet(f"background-color: {color.name()}")
            
            self.update_preview()
    
    def update_transparency_label(self, value):
        """Aktualisiert Transparenz-Label"""
        self.transparency_label.setText(f"{value}%")
        self.update_preview()
    
    def update_preview(self):
        """Aktualisiert die Vorschau"""
        # Font
        font = QFont(
            self.font_combo.currentText(),
            self.font_size_spin.value(),
            QFont.Bold if self.font_bold_check.isChecked() else QFont.Normal
        )
        
        self.preview_question.setFont(font)
        self.preview_answer.setFont(font)
        
        # Farben
        text_color = self.current_config['text']['text_color']
        bg_color = self.current_config['colors']['background_color']
        
        style = f"""
            color: {text_color};
            background-color: {bg_color};
            padding: 10px;
        """
        
        self.preview_question.setStyleSheet(style)
        self.preview_answer.setStyleSheet(style)
    
    def apply_current_config(self):
        """Wendet aktuelle Konfiguration auf UI an"""
        # Position & Größe
        self.position_combo.setCurrentText(self.current_config['overlay']['position'])
        self.width_spin.setValue(self.current_config['overlay']['width'])
        self.height_spin.setValue(self.current_config['overlay']['height'])
        self.transparency_slider.setValue(self.current_config['overlay']['transparency'])
        
        # Text
        self.font_combo.setCurrentText(self.current_config['text']['font_family'])
        self.font_size_spin.setValue(self.current_config['text']['font_size'])
        self.font_bold_check.setChecked(self.current_config['text']['font_bold'])
        self.line_spacing_spin.setValue(self.current_config['text']['line_spacing'])
        self.outline_width_spin.setValue(self.current_config['text']['outline_width'])
        
        # Farben
        self.text_color_btn.setStyleSheet(f"background-color: {self.current_config['text']['text_color']}")
        self.outline_color_btn.setStyleSheet(f"background-color: {self.current_config['text']['outline_color']}")
        self.bg_color_btn.setStyleSheet(f"background-color: {self.current_config['colors']['background_color']}")
        
        # Weitere
        self.auto_hide_spin.setValue(self.current_config['overlay']['auto_hide_delay'])
        self.animation_check.setChecked(self.current_config['overlay']['animation_enabled'])
        
        self.update_preview()
    
    def collect_current_settings(self):
        """Sammelt aktuelle Einstellungen aus UI"""
        self.current_config['overlay']['position'] = self.position_combo.currentText()
        self.current_config['overlay']['width'] = self.width_spin.value()
        self.current_config['overlay']['height'] = self.height_spin.value()
        self.current_config['overlay']['transparency'] = self.transparency_slider.value()
        self.current_config['overlay']['auto_hide_delay'] = self.auto_hide_spin.value()
        self.current_config['overlay']['animation_enabled'] = self.animation_check.isChecked()
        
        self.current_config['text']['font_family'] = self.font_combo.currentText()
        self.current_config['text']['font_size'] = self.font_size_spin.value()
        self.current_config['text']['font_bold'] = self.font_bold_check.isChecked()
        self.current_config['text']['line_spacing'] = self.line_spacing_spin.value()
        self.current_config['text']['outline_width'] = self.outline_width_spin.value()
    
    def save_settings(self):
        """Speichert Einstellungen"""
        self.collect_current_settings()
        if self.save_config():
            QMessageBox.information(self, "Erfolg", "✅ Einstellungen gespeichert!")
        else:
            QMessageBox.warning(self, "Fehler", "❌ Fehler beim Speichern!")
    
    def apply_settings(self):
        """Wendet Einstellungen an ohne zu speichern"""
        self.collect_current_settings()
        self.settings_changed.emit()
        QMessageBox.information(self, "Erfolg", "✅ Einstellungen angewendet!")
    
    def reset_settings(self):
        """Setzt Einstellungen zurück"""
        reply = QMessageBox.question(self, "Zurücksetzen", 
                                   "Wirklich auf Standard zurücksetzen?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.current_config = self.default_config.copy()
            self.apply_current_config()
            QMessageBox.information(self, "Erfolg", "🔄 Einstellungen zurückgesetzt!")

def main():
    app = QApplication(sys.argv)
    gui = ConfigGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()