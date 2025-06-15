#!/bin/bash
# start_qa_system.sh - Robustes Start-Skript für Q&A System
# Führt Tests durch und sorgt für Stabilität

set -euo pipefail  # Strict error handling

# =============================================================================
# KONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
LOG_FILE="${LOG_DIR}/qa_system_$(date +%Y%m%d_%H%M%S).log"

# PID-Dateien für Prozessüberwachung
OVERLAY_PID_FILE="${SCRIPT_DIR}/qa_overlay.pid"
FINDER_PID_FILE="${SCRIPT_DIR}/qa_finder.pid"

# Restart-Konfiguration
MAX_RESTARTS=5
RESTART_DELAY=5
HEALTH_CHECK_INTERVAL=10

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# =============================================================================
# CLEANUP UND SIGNAL HANDLING
# =============================================================================

cleanup() {
    log_info "🧹 Cleanup wird durchgeführt..."
    
    # Stoppe alle Hintergrundprozesse
    if [[ -f "${OVERLAY_PID_FILE}" ]]; then
        local overlay_pid=$(cat "${OVERLAY_PID_FILE}" 2>/dev/null || echo "")
        if [[ -n "${overlay_pid}" ]] && kill -0 "${overlay_pid}" 2>/dev/null; then
            log_info "Stoppe Overlay (PID: ${overlay_pid})"
            kill -TERM "${overlay_pid}" 2>/dev/null || true
            sleep 2
            kill -KILL "${overlay_pid}" 2>/dev/null || true
        fi
        rm -f "${OVERLAY_PID_FILE}"
    fi
    
    if [[ -f "${FINDER_PID_FILE}" ]]; then
        local finder_pid=$(cat "${FINDER_PID_FILE}" 2>/dev/null || echo "")
        if [[ -n "${finder_pid}" ]] && kill -0 "${finder_pid}" 2>/dev/null; then
            log_info "Stoppe Finder (PID: ${finder_pid})"
            kill -TERM "${finder_pid}" 2>/dev/null || true
            sleep 2
            kill -KILL "${finder_pid}" 2>/dev/null || true
        fi
        rm -f "${FINDER_PID_FILE}"
    fi
    
    # Alle Python-Prozesse des Q&A Systems beenden
    pkill -f "qa_overlay.py" 2>/dev/null || true
    pkill -f "qa_finder.py" 2>/dev/null || true
    
    log_success "✅ Cleanup abgeschlossen"
}

# Signal Handler
trap cleanup EXIT
trap 'log_warn "⚠️  Signal empfangen - beende graceful..."; exit 0' INT TERM

# =============================================================================
# SYSTEM TESTS
# =============================================================================

check_system_requirements() {
    log_info "🔍 Prüfe System-Anforderungen..."
    
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
    if ! python3 -c "import PyQt5" 2>/dev/null; then
        log_error "❌ PyQt5 nicht installiert"
        log_info "   Installiere mit: pip3 install PyQt5"
        all_good=false
    else
        log_success "✅ PyQt5 verfügbar"
    fi
    
    # xclip prüfen (für Zwischenablage)
    if ! command -v xclip &> /dev/null; then
        log_error "❌ xclip nicht gefunden"
        log_info "   Installiere mit: sudo apt-get install xclip"
        all_good=false
    else
        log_success "✅ xclip verfügbar"
    fi
    
    # Display prüfen
    if [[ -z "${DISPLAY:-}" ]]; then
        log_error "❌ DISPLAY Variable nicht gesetzt"
        all_good=false
    else
        log_success "✅ Display verfügbar: ${DISPLAY}"
    fi
    
    # Freier Speicher prüfen
    local free_mem=$(free -m | awk 'NR==2{printf "%d", $7}')
    if [[ ${free_mem} -lt 100 ]]; then
        log_warn "⚠️  Wenig freier Speicher: ${free_mem}MB"
    else
        log_success "✅ Ausreichend Speicher: ${free_mem}MB"
    fi
    
    return $([ "$all_good" = true ] && echo 0 || echo 1)
}

check_file_integrity() {
    log_info "📁 Prüfe Datei-Integrität..."
    
    local all_good=true
    
    # Python-Skripte prüfen
    for script in "qa_overlay.py" "qa_finder.py"; do
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
    log_info "🌐 Teste Netzwerk-Konnektivität..."
    
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
    log_info "🧪 Führe System-Tests durch..."
    
    local test_results=0
    
    check_system_requirements || ((test_results++))
    check_file_integrity || ((test_results++))
    test_network_connectivity || ((test_results++))
    
    if [[ ${test_results} -eq 0 ]]; then
        log_success "✅ Alle Tests bestanden"
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
    log_info "🎯 Starte Overlay..."
    
    cd "${SCRIPT_DIR}"
    python3 qa_overlay.py &
    local pid=$!
    echo ${pid} > "${OVERLAY_PID_FILE}"
    
    # Warte auf Startup
    sleep 3
    
    if kill -0 ${pid} 2>/dev/null; then
        log_success "✅ Overlay gestartet (PID: ${pid})"
        return 0
    else
        log_error "❌ Overlay konnte nicht gestartet werden"
        rm -f "${OVERLAY_PID_FILE}"
        return 1
    fi
}

start_finder() {
    log_info "🔍 Starte Finder..."
    
    cd "${SCRIPT_DIR}"
    python3 qa_finder.py &
    local pid=$!
    echo ${pid} > "${FINDER_PID_FILE}"
    
    # Warte auf Startup
    sleep 2
    
    if kill -0 ${pid} 2>/dev/null; then
        log_success "✅ Finder gestartet (PID: ${pid})"
        return 0
    else
        log_error "❌ Finder konnte nicht gestartet werden"
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
    
    log_warn "🔄 Starte ${process_name} neu..."
    
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
        log_success "✅ ${process_name} erfolgreich neugestartet"
        return 0
    else
        log_error "❌ Neustart von ${process_name} fehlgeschlagen"
        return 1
    fi
}

# =============================================================================
# MONITORING UND MAIN LOOP
# =============================================================================

monitor_processes() {
    log_info "👁️  Starte Prozess-Monitoring..."
    
    local overlay_restarts=0
    local finder_restarts=0
    
    while true; do
        # Overlay prüfen
        if ! check_process_health "Overlay" "${OVERLAY_PID_FILE}"; then
            if [[ ${overlay_restarts} -lt ${MAX_RESTARTS} ]]; then
                log_warn "⚠️  Overlay nicht erreichbar, starte neu..."
                if restart_process "Overlay" "start_overlay" "${OVERLAY_PID_FILE}"; then
                    ((overlay_restarts++))
                else
                    log_error "❌ Overlay Neustart fehlgeschlagen"
                    return 1
                fi
            else
                log_error "❌ Maximale Overlay-Neustarts erreicht (${MAX_RESTARTS})"
                return 1
            fi
        fi
        
        # Finder prüfen
        if ! check_process_health "Finder" "${FINDER_PID_FILE}"; then
            if [[ ${finder_restarts} -lt ${MAX_RESTARTS} ]]; then
                log_warn "⚠️  Finder nicht erreichbar, starte neu..."
                if restart_process "Finder" "start_finder" "${FINDER_PID_FILE}"; then
                    ((finder_restarts++))
                else
                    log_error "❌ Finder Neustart fehlgeschlagen"
                    return 1
                fi
            else
                log_error "❌ Maximale Finder-Neustarts erreicht (${MAX_RESTARTS})"
                return 1
            fi
        fi
        
        # Health Check Status
        if [[ $(($(date +%s) % 60)) -eq 0 ]]; then
            log_info "💚 System läuft (Overlay: ${overlay_restarts}/${MAX_RESTARTS} Restarts, Finder: ${finder_restarts}/${MAX_RESTARTS} Restarts)"
        fi
        
        sleep ${HEALTH_CHECK_INTERVAL}
    done
}

# =============================================================================
# MAIN FUNCTION
# =============================================================================

main() {
    log_info "🚀 Q&A System Starter v1.0"
    log_info "📍 Arbeitsverzeichnis: ${SCRIPT_DIR}"
    log_info "📝 Log-Datei: ${LOG_FILE}"
    
    # Cleanup alte PID-Dateien
    rm -f "${OVERLAY_PID_FILE}" "${FINDER_PID_FILE}"
    
    # System-Tests durchführen
    if ! run_all_tests; then
        log_error "❌ System-Tests fehlgeschlagen - Abbruch"
        exit 1
    fi
    
    # Prozesse starten
    if ! start_overlay; then
        log_error "❌ Overlay-Start fehlgeschlagen"
        exit 1
    fi
    
    if ! start_finder; then
        log_error "❌ Finder-Start fehlgeschlagen"
        exit 1
    fi
    
    log_success "🎉 Q&A System erfolgreich gestartet!"
    log_info "📋 Das System überwacht jetzt die Zwischenablage"
    log_info "🛑 Zum Beenden: Strg+C drücken"
    
    # Monitoring starten
    monitor_processes
}

# =============================================================================
# SCRIPT EXECUTION
# =============================================================================

# Prüfe ob bereits eine Instanz läuft
if pgrep -f "qa_overlay.py" > /dev/null || pgrep -f "qa_finder.py" > /dev/null; then
    log_warn "⚠️  Q&A System scheint bereits zu laufen"
    read -p "Trotzdem starten? (j/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[JjYy]$ ]]; then
        log_info "Abgebrochen"
        exit 0
    fi
    
    # Alte Prozesse beenden
    log_info "🧹 Beende bestehende Prozesse..."
    pkill -f "qa_overlay.py" 2>/dev/null || true
    pkill -f "qa_finder.py" 2>/dev/null || true
    sleep 2
fi

# Logging setup
setup_logging

# Main function ausführen
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi