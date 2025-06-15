#!/bin/bash
# install_gnome_qa.sh - Installer für GNOME Q&A System
# Installiert alle Dependencies und richtet das System für GNOME ein

set -euo pipefail

# =============================================================================
# KONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_LOG="${SCRIPT_DIR}/install_gnome_qa.log"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

# =============================================================================
# LOGGING
# =============================================================================

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${INSTALL_LOG}"
}

log_info() {
    log "${BLUE}[INFO]${NC} $*"
}

log_warn() {
    log "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    log "${RED}[ERROR]${NC} $*"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $*"
}

log_gnome() {
    log "${PURPLE}[GNOME]${NC} $*"
}

# =============================================================================
# SYSTEM DETECTION
# =============================================================================

detect_system() {
    log_info "🔍 Erkenne System-Konfiguration..."
    
    # OS Detection
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        OS_ID="${ID}"
        OS_VERSION="${VERSION_ID:-unknown}"
        OS_NAME="${PRETTY_NAME:-${ID}}"
    else
        OS_ID="unknown"
        OS_VERSION="unknown" 
        OS_NAME="Unknown OS"
    fi
    
    # Desktop Environment
    DESKTOP="${XDG_CURRENT_DESKTOP:-unknown}"
    SESSION_TYPE="${XDG_SESSION_TYPE:-unknown}"
    
    # Architecture
    ARCH=$(uname -m)
    
    log_info "💻 System: ${OS_NAME} (${OS_ID} ${OS_VERSION})"
    log_info "🏗️  Architektur: ${ARCH}"
    log_info "🖥️  Desktop: ${DESKTOP}"
    log_info "📺 Session Type: ${SESSION_TYPE}"
    
    # GNOME Check
    if [[ "${DESKTOP,,}" == *"gnome"* ]]; then
        log_success "✅ GNOME Desktop erkannt"
        return 0
    else
        log_warn "⚠️  Nicht-GNOME Desktop erkannt - Installation trotzdem möglich"
        return 1
    fi
}

# =============================================================================
# DEPENDENCY INSTALLATION  
# =============================================================================

install_system_dependencies() {
    log_info "📦 Installiere System-Dependencies..."
    
    local packages=()
    local clipboard_packages=()
    
    # Basis-Pakete
    packages+=(
        "python3"
        "python3-pip"
        "python3-dev"
    )
    
    # PyQt5 Pakete (distro-spezifisch)
    if [[ "${OS_ID}" == "ubuntu" ]] || [[ "${OS_ID}" == "debian" ]]; then
        packages+=(
            "python3-pyqt5"
            "python3-pyqt5.qtwidgets"
            "python3-pyqt5.qtcore"
            "python3-pyqt5.qtgui"
            "python3-pyqt5.qtdbus"
        )
    elif [[ "${OS_ID}" == "fedora" ]] || [[ "${OS_ID}" == "rhel" ]] || [[ "${OS_ID}" == "centos" ]]; then
        packages+=(
            "python3-qt5"
            "python3-qt5-devel"
        )
    elif [[ "${OS_ID}" == "arch" ]] || [[ "${OS_ID}" == "manjaro" ]]; then
        packages+=(
            "python-pyqt5"
            "qt5-base"
        )
    fi
    
    # Clipboard Tools
    if [[ "${SESSION_TYPE}" == "wayland" ]]; then
        clipboard_packages+=("wl-clipboard")
    fi
    clipboard_packages+=("xclip" "xsel")
    
    # Zusätzliche GNOME-Tools
    if [[ "${DESKTOP,,}" == *"gnome"* ]]; then
        clipboard_packages+=("libnotify-bin")  # für notify-send
    fi
    
    # Installation basierend auf Distribution
    if command -v apt-get &> /dev/null; then
        log_info "🍃 Verwende apt (Debian/Ubuntu)..."
        
        # Update package list
        log_info "Aktualisiere Paket-Liste..."
        sudo apt-get update
        
        # Install packages
        log_info "Installiere Basis-Pakete..."
        sudo apt-get install -y "${packages[@]}"
        
        log_info "Installiere Clipboard-Tools..."
        sudo apt-get install -y "${clipboard_packages[@]}"
        
    elif command -v dnf &> /dev/null; then
        log_info "🎩 Verwende dnf (Fedora)..."
        
        log_info "Installiere Pakete..."
        sudo dnf install -y "${packages[@]}" "${clipboard_packages[@]}"
        
    elif command -v yum &> /dev/null; then
        log_info "🎩 Verwende yum (RHEL/CentOS)..."
        
        log_info "Installiere Pakete..."
        sudo yum install -y "${packages[@]}" "${clipboard_packages[@]}"
        
    elif command -v pacman &> /dev/null; then
        log_info "🏹 Verwende pacman (Arch)..."
        
        log_info "Aktualisiere System..."
        sudo pacman -Sy
        
        log_info "Installiere Pakete..."
        sudo pacman -S --noconfirm "${packages[@]}" "${clipboard_packages[@]}"
        
    else
        log_error "❌ Unbekannter Paket-Manager"
        log_info "Bitte installiere manuell: ${packages[*]} ${clipboard_packages[*]}"
        return 1
    fi
    
    log_success "✅ System-Dependencies installiert"
}

install_python_dependencies() {
    log_info "🐍 Installiere Python-Dependencies..."
    
    # Prüfe ob pip verfügbar ist
    if ! command -v pip3 &> /dev/null; then
        log_error "❌ pip3 nicht gefunden"
        return 1
    fi
    
    # Upgrade pip
    log_info "Aktualisiere pip..."
    python3 -m pip install --user --upgrade pip
    
    # Fallback: PyQt5 über pip falls nicht über System-Pakete verfügbar
    if ! python3 -c "import PyQt5.QtWidgets" 2>/dev/null; then
        log_info "Installiere PyQt5 über pip..."
        python3 -m pip install --user PyQt5
    fi
    
    # Optional: Zusätzliche Python-Pakete
    local python_packages=(
        "psutil"     # System-Monitoring
    )
    
    for package in "${python_packages[@]}"; do
        if ! python3 -c "import ${package}" 2>/dev/null; then
            log_info "Installiere ${package}..."
            python3 -m pip install --user "${package}"
        fi
    done
    
    log_success "✅ Python-Dependencies installiert"
}

# =============================================================================
# FILE SETUP
# =============================================================================

setup_file_permissions() {
    log_info "🔐 Setze Datei-Berechtigungen..."
    
    # Ausführbare Dateien
    local executables=(
        "start_qa_gnome.sh"
        "stop_qa_gnome.sh"
        "qa_overlay_gnome.py"
        "qa_finder_gnome.py"
    )
    
    for file in "${executables[@]}"; do
        if [[ -f "${SCRIPT_DIR}/${file}" ]]; then
            chmod +x "${SCRIPT_DIR}/${file}"
            log_info "✅ ${file} ausführbar gemacht"
        else
            log_warn "⚠️  ${file} nicht gefunden"
        fi
    done
    
    # Log-Verzeichnis erstellen
    mkdir -p "${SCRIPT_DIR}/logs"
    
    log_success "✅ Datei-Berechtigungen gesetzt"
}

create_desktop_integration() {
    log_gnome "🖥️  Erstelle GNOME Desktop-Integration..."
    
    local desktop_dir="$HOME/.local/share/applications"
    local autostart_dir="$HOME/.config/autostart"
    local desktop_file="${desktop_dir}/qa-system-gnome.desktop"
    local autostart_file="${autostart_dir}/qa-system-gnome.desktop"
    
    # Erstelle Verzeichnisse
    mkdir -p "${desktop_dir}"
    mkdir -p "${autostart_dir}"
    
    # Desktop Entry erstellen
    cat > "${desktop_file}" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Q&A System GNOME
Name[de]=Q&A System GNOME
Comment=Question and Answer Overlay System optimized for GNOME Desktop
Comment[de]=Frage-Antwort-Overlay-System optimiert für GNOME Desktop
GenericName=Educational Overlay
GenericName[de]=Bildungs-Overlay

# Execution
Exec=${SCRIPT_DIR}/start_qa_gnome.sh
Icon=applications-education
Terminal=false
Path=${SCRIPT_DIR}/

# Categories and Keywords
Categories=Education;Utility;Office;Development;
Keywords=qa;question;answer;overlay;gnome;education;learning;study;exam;
Keywords[de]=frage;antwort;overlay;gnome;bildung;lernen;studium;prüfung;

# Desktop Integration
StartupNotify=false
NoDisplay=false
Hidden=false
StartupWMClass=Q&A Overlay

# GNOME specific
X-GNOME-Bugzilla-Bugzilla=GNOME
X-GNOME-Bugzilla-Product=qa-system
X-GNOME-Bugzilla-Component=overlay
X-GNOME-UsesNotifications=true

# Actions
Actions=start;stop;restart;

[Desktop Action start]
Name=Start Q&A System
Name[de]=Q&A System starten
Exec=${SCRIPT_DIR}/start_qa_gnome.sh
Icon=media-playback-start

[Desktop Action stop]
Name=Stop Q&A System  
Name[de]=Q&A System stoppen
Exec=${SCRIPT_DIR}/stop_qa_gnome.sh
Icon=media-playback-stop

[Desktop Action restart]
Name=Restart Q&A System
Name[de]=Q&A System neustarten
Exec=${SCRIPT_DIR}/stop_qa_gnome.sh && sleep 2 && ${SCRIPT_DIR}/start_qa_gnome.sh
Icon=view-refresh
EOF
    
    # Desktop-Datei als ausführbar markieren
    chmod +x "${desktop_file}"
    
    # Autostart-Datei erstellen (deaktiviert)
    cp "${desktop_file}" "${autostart_file}"
    echo "X-GNOME-Autostart-enabled=false" >> "${autostart_file}"
    
    # Desktop-Datenbank aktualisieren
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "${desktop_dir}" 2>/dev/null || true
    fi
    
    log_success "✅ Desktop-Integration erstellt"
    log_info "📝 Desktop-Entry: ${desktop_file}"
    log_info "🚀 Autostart-Entry: ${autostart_file} (deaktiviert)"
    log_info "   Aktiviere Autostart über GNOME Einstellungen > Startprogramme"
}

create_launcher_script() {
    log_info "🚀 Erstelle System-weiten Launcher..."
    
    local launcher_script="/usr/local/bin/qa-system-gnome"
    
    cat > /tmp/qa-system-gnome << EOF
#!/bin/bash
# Q&A System GNOME Launcher
# Erstellt von install_gnome_qa.sh

SCRIPT_DIR="${SCRIPT_DIR}"

case "\${1:-start}" in
    start)
        "\${SCRIPT_DIR}/start_qa_gnome.sh"
        ;;
    stop)
        "\${SCRIPT_DIR}/stop_qa_gnome.sh"
        ;;
    restart)
        "\${SCRIPT_DIR}/stop_qa_gnome.sh"
        sleep 2
        "\${SCRIPT_DIR}/start_qa_gnome.sh"
        ;;
    status)
        if pgrep -f "qa_overlay_gnome.py" > /dev/null || pgrep -f "qa_finder_gnome.py" > /dev/null; then
            echo "Q&A System läuft"
            exit 0
        else
            echo "Q&A System läuft nicht"
            exit 1
        fi
        ;;
    *)
        echo "Verwendung: \$0 {start|stop|restart|status}"
        echo ""
        echo "  start    - Startet das Q&A System"
        echo "  stop     - Stoppt das Q&A System"
        echo "  restart  - Startet das Q&A System neu"
        echo "  status   - Zeigt den Status an"
        exit 1
        ;;
esac
EOF
    
    # Installation versuchen (optional, falls sudo verfügbar)
    if sudo install -m 755 /tmp/qa-system-gnome "${launcher_script}" 2>/dev/null; then
        log_success "✅ System-Launcher installiert: ${launcher_script}"
        log_info "   Verwendung: qa-system-gnome {start|stop|restart|status}"
    else
        log_warn "⚠️  System-Launcher konnte nicht installiert werden (sudo erforderlich)"
        log_info "   Manuell installieren: sudo install -m 755 /tmp/qa-system-gnome ${launcher_script}"
    fi
    
    rm -f /tmp/qa-system-gnome
}

# =============================================================================
# TESTING
# =============================================================================

run_installation_tests() {
    log_info "🧪 Führe Installations-Tests durch..."
    
    local test_results=0
    
    # Python Import Tests
    log_info "Teste Python-Imports..."
    
    if python3 -c "import PyQt5.QtWidgets" 2>/dev/null; then
        log_success "✅ PyQt5 QtWidgets Import OK"
    else
        log_error "❌ PyQt5 QtWidgets Import fehlgeschlagen"
        ((test_results++))
    fi
    
    if python3 -c "import PyQt5.QtCore" 2>/dev/null; then
        log_success "✅ PyQt5 QtCore Import OK"
    else
        log_error "❌ PyQt5 QtCore Import fehlgeschlagen"
        ((test_results++))
    fi
    
    # Optional: D-Bus Test
    if python3 -c "import PyQt5.QtDBus" 2>/dev/null; then
        log_success "✅ PyQt5 D-Bus Support verfügbar"
    else
        log_warn "⚠️  PyQt5 D-Bus Support nicht verfügbar"
    fi
    
    # Clipboard Tools testen
    log_info "Teste Clipboard-Tools..."
    
    local clipboard_tools_found=0
    for tool in xclip wl-paste xsel; do
        if command -v "${tool}" &> /dev/null; then
            log_success "✅ ${tool} verfügbar"
            ((clipboard_tools_found++))
        fi
    done
    
    if [[ ${clipboard_tools_found} -eq 0 ]]; then
        log_error "❌ Keine Clipboard-Tools gefunden"
        ((test_results++))
    fi
    
    # Datei-Tests
    log_info "Teste Dateien..."
    
    local required_files=(
        "qa_overlay_gnome.py"
        "qa_finder_gnome.py" 
        "start_qa_gnome.sh"
        "stop_qa_gnome.sh"
        "answare.json"
    )
    
    for file in "${required_files[@]}"; do
        if [[ -f "${SCRIPT_DIR}/${file}" ]]; then
            if [[ -x "${SCRIPT_DIR}/${file}" ]] || [[ "${file}" == *.json ]]; then
                log_success "✅ ${file} OK"
            else
                log_error "❌ ${file} nicht ausführbar"
                ((test_results++))
            fi
        else
            log_error "❌ ${file} nicht gefunden"
            ((test_results++))
        fi
    done
    
    # Ergebnis
    if [[ ${test_results} -eq 0 ]]; then
        log_success "✅ Alle Installations-Tests bestanden"
        return 0
    else
        log_error "❌ ${test_results} Test(s) fehlgeschlagen"
        return 1
    fi
}

# =============================================================================
# MAIN INSTALLATION
# =============================================================================

show_welcome() {
    echo ""
    echo -e "${PURPLE}================================${NC}"
    echo -e "${PURPLE}   Q&A System GNOME Installer   ${NC}"
    echo -e "${PURPLE}================================${NC}"
    echo ""
    echo "Dieser Installer richtet das Q&A System für GNOME ein."
    echo ""
    echo "Was wird installiert:"
    echo "• System-Dependencies (Python, PyQt5, Clipboard-Tools)"
    echo "• Desktop-Integration (.desktop-Dateien)"
    echo "• GNOME-spezifische Optimierungen"
    echo ""
}

show_completion() {
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}   Installation abgeschlossen   ${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    echo "Das Q&A System ist jetzt einsatzbereit!"
    echo ""
    echo "Nächste Schritte:"
    echo "1. Starte das System:  ./start_qa_gnome.sh"
    echo "2. Oder über Desktop: Anwendungen > Q&A System GNOME"
    echo "3. Optional: Autostart aktivieren in GNOME Einstellungen"
    echo ""
    echo "Weitere Befehle:"
    echo "• System starten:   qa-system-gnome start"
    echo "• System stoppen:   qa-system-gnome stop"
    echo "• Status prüfen:    qa-system-gnome status"
    echo ""
    echo "Log-Dateien: ${SCRIPT_DIR}/logs/"
    echo "Installation-Log: ${INSTALL_LOG}"
    echo ""
}

main() {
    # Setup
    echo "Starte Installation..." > "${INSTALL_LOG}"
    
    show_welcome
    
    # Bestätigung einholen
    read -p "Installation fortsetzen? (j/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[JjYy]$ ]]; then
        log_info "Installation abgebrochen"
        exit 0
    fi
    
    # System erkennen
    detect_system
    
    # Dependencies installieren
    log_info "📦 Installiere Dependencies..."
    if ! install_system_dependencies; then
        log_error "❌ System-Dependencies Installation fehlgeschlagen"
        exit 1
    fi
    
    if ! install_python_dependencies; then
        log_error "❌ Python-Dependencies Installation fehlgeschlagen"
        exit 1
    fi
    
    # Dateien einrichten
    setup_file_permissions
    
    # Desktop-Integration
    create_desktop_integration
    create_launcher_script
    
    # Tests durchführen
    if ! run_installation_tests; then
        log_warn "⚠️  Einige Tests fehlgeschlagen - System möglicherweise nicht vollständig funktional"
    fi
    
    # Abschluss
    show_completion
    
    log_success "🎉 GNOME Q&A System Installation erfolgreich abgeschlossen"
}

# Hilfe anzeigen
show_help() {
    echo "GNOME Q&A System Installer"
    echo ""
    echo "Verwendung: $0 [OPTIONEN]"
    echo ""
    echo "Optionen:"
    echo "  -h, --help        Zeige diese Hilfe"
    echo "  --skip-deps       Überspringe Dependency-Installation"
    echo "  --no-desktop      Keine Desktop-Integration"
    echo "  --no-launcher     Keinen System-Launcher erstellen"
    echo ""
}

# Parameter verarbeiten
SKIP_DEPS=false
NO_DESKTOP=false
NO_LAUNCHER=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        --no-desktop)
            NO_DESKTOP=true
            shift
            ;;
        --no-launcher)
            NO_LAUNCHER=true
            shift
            ;;
        *)
            echo "Unbekannte Option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Haupt-Installation starten
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
