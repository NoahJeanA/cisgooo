#!/bin/bash
# start_qa_gnome.sh - GNOME-optimiertes Start-Skript für Q&A System
# Erkennt automatisch Wayland/Xorg und passt sich entsprechend an

set -euo pipefail

# =============================================================================
# KONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
LOG_FILE="${LOG_DIR}/qa_gnome_$(date +%Y%m%d_%H%M%S).log"

# PID-Dateien
OVERLAY_PID_FILE="${SCRIPT_DIR}/qa_overlay_gnome.pid"
FINDER_PID_FILE="${SCRIPT_DIR}/qa_finder_gnome.pid"

# Restart-Konfiguration
MAX_RESTARTS=5
RESTART_DELAY=5
HEALTH_CHECK_INTERVAL=10

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

# =============================================================================
# DESKTOP UMGEBUNG ERKENNUNG
# =============================================================================

detect_desktop_environment() {
    local desktop="${XDG_CURRENT_DESKTOP:-unknown}"
    local session="${DESKTOP_SESSION:-unknown}"
    local session_type="${XDG_SESSION_TYPE:-unknown}"
    local wayland_display="${WAYLAND_DISPLAY:-}"
    local x_display="${DISPLAY:-}"
    
    echo "DESKTOP=${desktop,,}"
    echo "SESSION=${session,,}"
    echo "SESSION_TYPE=${session_type,,}"
    echo "WAYLAND_DISPLAY=${wayland_display}"
    echo "X_DISPLAY=${x_display}"
    
    # Session Type bestimmen
    if [[ "$session_type" == "wayland" ]] || [[ -n "$wayland_display" ]]; then
        echo "DISPLAY_SERVER=wayland"
    elif [[ "$session_type" == "x11" ]] || [[ -n "$x_display" ]]; then
        echo "DISPLAY_SERVER=xorg"
    else
        echo "DISPLAY_SERVER=unknown"
    fi
    
    # Desktop Environment bestimmen
    if [[ "$desktop" == *"gnome"* ]] || [[ "$session" == *"gnome"* ]]; then
        echo "DE=gnome"
    elif [[ "$desktop" == *"kde"* ]] || [[ "$desktop" == *"plasma"* ]]; then
        echo "DE=kde"
    elif [[ "$desktop" == *"xfce"* ]]; then
        echo "DE=xfce"
    elif [[ "$desktop" == *"mate"* ]]; then
        echo "DE=mate"
    else
        echo "DE=unknown"
    fi
}

# =============================================================================
# LOGGING FUNKTIONEN
# =============================================================================

setup_logging() {
    mkdir -p "${LOG_DIR}"
    exec 1> >(tee -a "${LOG_FILE}")
    exec 2> >(tee -a "${LOG_FILE}" >&2)
}

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
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
# CLEANUP UND SIGNAL HANDLING
# =============================================================================

cleanup() {
    log_info "🧹 GNOME Cleanup wird durchgeführt..."
    
    # Stoppe alle Hintergrundprozesse
    if [[ -f "${OVERLAY_PID_FILE}" ]]; then
        local overlay_pid=$(cat "${OVERLAY_PID_FILE}" 2>/dev/null || echo "")
        if [[ -n "${overlay_pid}" ]] && kill -0 "${overlay_pid}" 2>/dev/null; then
            log_info "Stoppe GNOME Overlay (PID: ${overlay_pid})"
            kill -TERM "${overlay_pid}" 2>/dev/null || true
            sleep 2
            kill -KILL "${overlay_pid}" 2>/dev/null || true
        fi
        rm -f "${OVERLAY_PID_FILE}"
    fi
    
    if [[ -f "${FINDER_PID_FILE}" ]]; then
        local finder_pid=$(cat "${FINDER_PID_FILE}" 2>/dev/null || echo "")
        if [[ -n "${finder_pid}" ]] && kill -0 "${finder_pid}" 2>/dev/null; then
            log_info "Stoppe GNOME Finder (PID: ${finder_pid})"
            kill -TERM "${finder_pid}" 2>/dev/null || true
            sleep 2
            kill -KILL "${finder_pid}" 2>/dev/null || true
        fi
        rm -f "${FINDER_PID_FILE}"
    fi
    
    # Alle Python-Prozesse des GNOME Q&A Systems beenden
    pkill -f "qa_overlay_gnome.py" 2>/dev/null || true
    pkill -f "qa_finder_gnome.py" 2>/dev/null || true
    
    log_success "✅ GNOME Cleanup abgeschlossen"
}

trap cleanup EXIT
trap 'log_warn "⚠️  Signal empfangen - beende graceful..."; exit 0' INT TERM

# =============================================================================
# SYSTEM TESTS
# =============================================================================

check_gnome_requirements() {
    log_gnome "🔍 Prüfe GNOME-spezifische Anforderungen..."
    
    local all_good=true
    
    # Desktop-Umgebung analysieren
    eval "$(detect_desktop_environment)"
    
    log_info "🖥️  Desktop Environment: ${DE}"
    log_info "📺 Display Server: ${DISPLAY_SERVER}"
    log_info "🎯 Session Type: ${SESSION_TYPE}"
    
    # GNOME-spezifische Prüfungen
    if [[ "$DE" == "gnome" ]]; then
        log_success "✅ GNOME Desktop erkannt"
        
        # GNOME Shell Version prüfen
        if command -v gnome-shell &> /dev/null; then
            local gnome_version=$(gnome-shell --version 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+' || echo "unknown")
            log_success "✅ GNOME Shell Version: ${gnome_version}"
        else
            log_warn "⚠️  GNOME Shell nicht gefunden"
        fi
        
        # D-Bus prüfen
        if systemctl --user is-active dbus &> /dev/null; then
            log_success "✅ D-Bus Service aktiv"
        else
            log_warn "⚠️  D-Bus Service nicht aktiv"
        fi
        
    else
        log_warn "⚠️  Nicht-GNOME Desktop erkannt (${DE})"
        log_info "   Das System funktioniert auch auf anderen Desktops"
    fi
    
    # Display Server spezifische Prüfungen
    if [[ "$DISPLAY_SERVER" == "wayland" ]]; then
        log_info "🌊 Wayland Display Server erkannt"
        
        # wl-clipboard prüfen
        if command -v wl-paste &> /dev/null; then
            log_success "✅ wl-clipboard verfügbar"
        else
            log_error "❌ wl-clipboard nicht installiert"
            log_info "   Installiere mit: sudo apt-get install wl-clipboard"
            all_good=false
        fi
        
    elif [[ "$DISPLAY_SERVER" == "xorg" ]]; then
        log_info "🖼️  Xorg Display Server erkannt"
        
        # xclip prüfen
        if command -v xclip &> /dev/null; then
            log_success "✅ xclip verfügbar"
        else
            log_error "❌ xclip nicht installiert"
            log_info "   Installiere mit: sudo apt-get install xclip"
            all_good=false
        fi
        
    else
        log_warn "⚠️  Display Server unbekannt"
        all_good=false
    fi
    
    return $([ "$all_good" = true ] && echo 0 || echo 1)
}

check_python_requirements() {
    log_info "🐍 Prüfe Python-Anforderungen..."
    
    local all_good=true
    
    # Python 3 prüfen
    if ! command -v python3 &> /dev/null; then
        log_error "❌ Python3 nicht gefunden"
        all_good=false
    else
        local python_version=$(python3 --version | cut -d' ' -f2)
        log_success "✅ Python3 gefunden: ${python_version}"
    fi
    
    # PyQt5 prüfen
    if ! python3 -c "import PyQt5.QtWidgets" 2>/dev/null; then
        log_error "❌ PyQt5 nicht vollständig installiert"
        log_info "   Installiere mit: sudo apt-get install python3-pyqt5"
        all_good=false
    else
        log_success "✅ PyQt5 verfügbar"
    fi
    
    # Optional: PyQt5 DBus für GNOME Integration
    if python3 -c "import PyQt5.QtDBus" 2>/dev/null; then
        log_success "✅ PyQt5 D-Bus Support verfügbar"
    else
        log_warn "⚠️  PyQt5 D-Bus Support nicht verfügbar"
        log_info "   Installiere mit: sudo apt-get install python3-pyqt5.qtdbus"
    fi
    
    return $([ "$all_good" = true ] && echo 0 || echo 1)
}

check_system_resources() {
    log_info "💻 Prüfe System-Ressourcen..."
    
    # Freier Speicher
    local free_mem=$(free -m | awk 'NR==2{printf "%d", $7}')
    if [[ ${free_mem} -lt 100 ]]; then
        log_warn "⚠️  Wenig freier Speicher: ${free_mem}MB"
    else
        log_success "✅ Ausreichend Speicher: ${free_mem}MB"
    fi
    
    # CPU Load
    local cpu_load=$(uptime | awk -F'load average:' '{ print $2 }' | awk '{ print $1 }' | sed 's/,//')
    log_info "📊 CPU Load: ${cpu_load}"
    
    # Disk Space
    local disk_free=$(df "${SCRIPT_DIR}" | awk 'NR==2 {print $4}')
    log_info "💾 Freier Speicherplatz: $((disk_free / 1024))MB"
    
    return 0
}

check_file_integrity() {
    log_info "📁 Prüfe GNOME-spezifische Dateien..."
    
    local all_good=true
    
    # Python-Skripte prüfen
    for script in "qa_overlay_gnome.py" "qa_finder_gnome.py"; do
        if [[ ! -f "${SCRIPT_DIR}/${script}" ]]; then
            log_error "❌ ${script} nicht gefunden"
            all_good=false
        elif [[ ! -r "${SCRIPT_DIR}/${script}" ]]; then
            log_error "❌ ${script} nicht lesbar"
            all_good=false
        else
            # Syntax-Check
            if python3 -m py_compile "${SCRIPT_DIR}/${script}" 2>/dev/null; then
                log_success "✅ ${script} Syntax OK"
            else
                log_error "❌ ${script} Syntax-Fehler"
                all_good=false
            fi
        fi
    done
    
    # JSON-Datei prüfen
    if [[ ! -f "${SCRIPT_DIR}/answare.json" ]]; then
        log_error "❌ answare.json nicht gefunden"
        all_good=false
    elif [[ ! -r "${SCRIPT_DIR}/answare.json" ]]; then
        log_error "❌ answare.json nicht lesbar"
        all_good=false
    else
        # JSON Syntax prüfen
        if python3 -c "import json; json.load(open('${SCRIPT_DIR}/answare.json'))" 2>/dev/null; then
            local question_count=$(python3 -c "import json; print(len(json.load(open('${SCRIPT_DIR}/answare.json'))))")
            log_success "✅ answare.json OK (${question_count} Fragen)"
        else
            log_error "❌ answare.json ungültiges JSON"
            all_good=false
        fi
    fi
    
    return $([ "$all_good" = true ] && echo 0 || echo 1)
}

test_network_connectivity() {
    log_info "🌐 Teste Netzwerk für Overlay-Kommunikation..."
    
    # Teste localhost Port
    if ss -tuln | grep -q ":12345 "; then
        log_warn "⚠️  Port 12345 bereits belegt"
        return 1
    else
        log_success "✅ Port 12345 verfügbar"
    fi
    
    # Teste Socket-Kommunikation
    if python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 12345))
    s.close()
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
    exit(1)
" 2>/dev/null; then
        log_success "✅ Socket-Test erfolgreich"
        return 0
    else
        log_error "❌ Socket-Test fehlgeschlagen"
        return 1
    fi
}

run_all_tests() {
    log_gnome "🧪 Führe GNOME-optimierte System-Tests durch..."
    
    local test_results=0
    
    check_gnome_requirements || ((test_results++))
    check_python_requirements || ((test_results++))
    check_system_resources || ((test_results++))
    check_file_integrity || ((test_results++))
    test_network_connectivity || ((test_results++))
    
    if [[ ${test_results} -eq 0 ]]; then
        log_success "✅ Alle GNOME-Tests bestanden"
        return 0
    else
        log_error "❌ ${test_results} Test(s) fehlgeschlagen"
        return 1
    fi
}

# =============================================================================
# PROZESS MANAGEMENT
# =============================================================================

start_overlay() {
    log_gnome "🎯 Starte GNOME Overlay..."
    
    cd "${SCRIPT_DIR}"
    
    # Umgebungsvariablen für GNOME setzen
    export QT_QPA_PLATFORM=xcb  # Force Qt to use X11 auch unter Wayland wenn nötig
    
    python3 qa_overlay_gnome.py &
    local pid=$!
    echo ${pid} > "${OVERLAY_PID_FILE}"
    
    # Warte auf Startup
    sleep 4
    
    if kill -0 ${pid} 2>/dev/null; then
        log_success "✅ GNOME Overlay gestartet (PID: ${pid})"
        return 0
    else
        log_error "❌ GNOME Overlay konnte nicht gestartet werden"
        rm -f "${OVERLAY_PID_FILE}"
        return 1
    fi
}

start_finder() {
    log_gnome "🔍 Starte GNOME Finder..."
    
    cd "${SCRIPT_DIR}"
    python3 qa_finder_gnome.py &
    local pid=$!
    echo ${pid} > "${FINDER_PID_FILE}"
    
    # Warte auf Startup
    sleep 3
    
    if kill -0 ${pid} 2>/dev/null; then
        log_success "✅ GNOME Finder gestartet (PID: ${pid})"
        return 0
    else
        log_error "❌ GNOME Finder konnte nicht gestartet werden"
        rm -f "${FINDER_PID_FILE}"
        return 1
    fi
}

check_process_health() {
    local process_name=$1
    local pid_file=$2
    
    if [[ ! -f "${pid_file}" ]]; then
        return 1
    fi
    
    local pid=$(cat "${pid_file}" 2>/dev/null || echo "")
    if [[ -z "${pid}" ]]; then
        return 1
    fi
    
    if kill -0 "${pid}" 2>/dev/null; then
        return 0
    else
        rm -f "${pid_file}"
        return 1
    fi
}

restart_process() {
    local process_name=$1
    local start_function=$2
    local pid_file=$3
    
    log_warn "🔄 Starte GNOME ${process_name} neu..."
    
    # Alten Prozess beenden falls noch vorhanden
    if [[ -f "${pid_file}" ]]; then
        local old_pid=$(cat "${pid_file}" 2>/dev/null || echo "")
        if [[ -n "${old_pid}" ]]; then
            kill -TERM "${old_pid}" 2>/dev/null || true
            sleep 2
            kill -KILL "${old_pid}" 2>/dev/null || true
        fi
        rm -f "${pid_file}"
    fi
    
    sleep ${RESTART_DELAY}
    
    if ${start_function}; then
        log_success "✅ GNOME ${process_name} erfolgreich neugestartet"
        return 0
    else
        log_error "❌ Neustart von GNOME ${process_name} fehlgeschlagen"
        return 1
    fi
}

# =============================================================================
# MONITORING UND MAIN LOOP
# =============================================================================

monitor_processes() {
    log_gnome "👁️  Starte GNOME Prozess-Monitoring..."
    
    local overlay_restarts=0
    local finder_restarts=0
    
    while true; do
        # Overlay prüfen
        if ! check_process_health "Overlay" "${OVERLAY_PID_FILE}"; then
            if [[ ${overlay_restarts} -lt ${MAX_RESTARTS} ]]; then
                log_warn "⚠️  GNOME Overlay nicht erreichbar, starte neu..."
                if restart_process "Overlay" "start_overlay" "${OVERLAY_PID_FILE}"; then
                    ((overlay_restarts++))
                else
                    log_error "❌ GNOME Overlay Neustart fehlgeschlagen"
                    return 1
                fi
            else
                log_error "❌ Maximale GNOME Overlay-Neustarts erreicht (${MAX_RESTARTS})"
                return 1
            fi
        fi
        
        # Finder prüfen
        if ! check_process_health "Finder" "${FINDER_PID_FILE}"; then
            if [[ ${finder_restarts} -lt ${MAX_RESTARTS} ]]; then
                log_warn "⚠️  GNOME Finder nicht erreichbar, starte neu..."
                if restart_process "Finder" "start_finder" "${FINDER_PID_FILE}"; then
                    ((finder_restarts++))
                else
                    log_error "❌ GNOME Finder Neustart fehlgeschlagen"
                    return 1
                fi
            else
                log_error "❌ Maximale GNOME Finder-Neustarts erreicht (${MAX_RESTARTS})"
                return 1
            fi
        fi
        
        # Health Check Status
        if [[ $(($(date +%s) % 60)) -eq 0 ]]; then
            log_gnome "💚 GNOME System läuft (Overlay: ${overlay_restarts}/${MAX_RESTARTS} Restarts, Finder: ${finder_restarts}/${MAX_RESTARTS} Restarts)"
        fi
        
        sleep ${HEALTH_CHECK_INTERVAL}
    done
}

# =============================================================================
# GNOME DESKTOP INTEGRATION
# =============================================================================

create_desktop_entry() {
    log_gnome "🖥️  Erstelle Desktop-Integration..."
    
    local desktop_file="$HOME/.local/share/applications/qa-system-gnome.desktop"
    local autostart_file="$HOME/.config/autostart/qa-system-gnome.desktop"
    
    # Desktop Entry erstellen
    cat > "${desktop_file}" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Q&A System GNOME
Comment=Question and Answer Overlay System for GNOME
Exec=${SCRIPT_DIR}/start_qa_gnome.sh
Icon=applications-education
Terminal=false
Categories=Education;Utility;
Keywords=qa;question;answer;overlay;gnome;
StartupNotify=false
NoDisplay=false
EOF
    
    # Autostart Entry (optional)
    if [[ ! -f "${autostart_file}" ]]; then
        mkdir -p "$(dirname "${autostart_file}")"
        cp "${desktop_file}" "${autostart_file}"
        echo "X-GNOME-Autostart-enabled=false" >> "${autostart_file}"
        log_info "📝 Desktop-Integration erstellt (Autostart deaktiviert)"
        log_info "   Aktiviere Autostart mit: cp \"${desktop_file}\" \"${autostart_file}\""
    fi
    
    # Desktop-Datei aktualisieren
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    fi
}

# =============================================================================
# MAIN FUNCTION
# =============================================================================

main() {
    log_gnome "🚀 Q&A System GNOME Starter v1.0"
    log_info "📍 Arbeitsverzeichnis: ${SCRIPT_DIR}"
    log_info "📝 Log-Datei: ${LOG_FILE}"
    
    # Cleanup alte PID-Dateien
    rm -f "${OVERLAY_PID_FILE}" "${FINDER_PID_FILE}"
    
    # System-Tests durchführen
    if ! run_all_tests; then
        log_error "❌ GNOME System-Tests fehlgeschlagen - Abbruch"
        exit 1
    fi
    
    # GNOME Desktop-Integration
    create_desktop_entry
    
    # Prozesse starten
    if ! start_overlay; then
        log_error "❌ GNOME Overlay-Start fehlgeschlagen"
        exit 1
    fi
    
    if ! start_finder; then
        log_error "❌ GNOME Finder-Start fehlgeschlagen"
        exit 1
    fi
    
    log_success "🎉 GNOME Q&A System erfolgreich gestartet!"
    log_gnome "📋 Das System überwacht jetzt die Zwischenablage unter GNOME"
    log_info "🛑 Zum Beenden: Strg+C drücken"
    
    # Monitoring starten
    monitor_processes
}

# =============================================================================
# SCRIPT EXECUTION
# =============================================================================

# Prüfe ob bereits eine Instanz läuft
if pgrep -f "qa_overlay_gnome.py" > /dev/null || pgrep -f "qa_finder_gnome.py" > /dev/null; then
    log_warn "⚠️  GNOME Q&A System scheint bereits zu laufen"
    read -p "Trotzdem starten? (j/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[JjYy]$ ]]; then
        log_info "Abgebrochen"
        exit 0
    fi
    
    # Alte Prozesse beenden
    log_info "🧹 Beende bestehende GNOME Prozesse..."
    pkill -f "qa_overlay_gnome.py" 2>/dev/null || true
    pkill -f "qa_finder_gnome.py" 2>/dev/null || true
    sleep 2
fi

# Logging setup
setup_logging

# Main function ausführen
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
