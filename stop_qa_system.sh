#!/bin/bash
# stop_qa_gnome.sh - Sicheres Stoppen des GNOME Q&A Systems

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OVERLAY_PID_FILE="${SCRIPT_DIR}/qa_overlay_gnome.pid"
FINDER_PID_FILE="${SCRIPT_DIR}/qa_finder_gnome.pid"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

log_info() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}[SUCCESS]${NC} $*"
}

log_warn() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}[WARN]${NC} $*"
}

log_gnome() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${PURPLE}[GNOME]${NC} $*"
}

stop_process() {
    local name=$1
    local pid_file=$2
    
    if [[ -f "${pid_file}" ]]; then
        local pid=$(cat "${pid_file}" 2>/dev/null || echo "")
        if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
            log_info "Stoppe GNOME ${name} (PID: ${pid})"
            
            # Graceful shutdown
            kill -TERM "${pid}" 2>/dev/null || true
            
            # Warte bis zu 10 Sekunden
            local count=0
            while kill -0 "${pid}" 2>/dev/null && [[ ${count} -lt 10 ]]; do
                sleep 1
                ((count++))
            done
            
            # Force kill falls nötig
            if kill -0 "${pid}" 2>/dev/null; then
                log_warn "Force kill für GNOME ${name} (PID: ${pid})"
                kill -KILL "${pid}" 2>/dev/null || true
            fi
            
            log_success "GNOME ${name} gestoppt"
        else
            log_info "GNOME ${name} war nicht aktiv"
        fi
        rm -f "${pid_file}"
    else
        log_info "Keine PID-Datei für GNOME ${name} gefunden"
    fi
}

check_gnome_processes() {
    log_info "🔍 Suche nach GNOME Q&A Prozessen..."
    
    local overlay_pids=$(pgrep -f "qa_overlay_gnome.py" 2>/dev/null || true)
    local finder_pids=$(pgrep -f "qa_finder_gnome.py" 2>/dev/null || true)
    
    if [[ -n "${overlay_pids}" ]]; then
        log_info "Gefundene GNOME Overlay-Prozesse: ${overlay_pids}"
        return 0
    fi
    
    if [[ -n "${finder_pids}" ]]; then
        log_info "Gefundene GNOME Finder-Prozesse: ${finder_pids}"
        return 0
    fi
    
    return 1
}

cleanup_gnome_processes() {
    log_info "🧹 Cleanup verwaister GNOME Prozesse..."
    
    local overlay_pids=$(pgrep -f "qa_overlay_gnome.py" 2>/dev/null || true)
    local finder_pids=$(pgrep -f "qa_finder_gnome.py" 2>/dev/null || true)
    
    if [[ -n "${overlay_pids}" ]]; then
        log_warn "Cleanup GNOME Overlay-Prozesse: ${overlay_pids}"
        echo "${overlay_pids}" | xargs -r kill -TERM 2>/dev/null || true
        sleep 2
        echo "${overlay_pids}" | xargs -r kill -KILL 2>/dev/null || true
    fi
    
    if [[ -n "${finder_pids}" ]]; then
        log_warn "Cleanup GNOME Finder-Prozesse: ${finder_pids}"
        echo "${finder_pids}" | xargs -r kill -TERM 2>/dev/null || true
        sleep 2
        echo "${finder_pids}" | xargs -r kill -KILL 2>/dev/null || true
    fi
}

send_gnome_notification() {
    local title="$1"
    local message="$2"
    local icon="${3:-dialog-information}"
    
    # Versuche GNOME-Benachrichtigung zu senden
    if command -v notify-send &> /dev/null; then
        notify-send --icon="${icon}" "${title}" "${message}" 2>/dev/null || true
    fi
}

main() {
    log_gnome "🛑 Stoppe GNOME Q&A System..."
    
    # Prüfe ob überhaupt Prozesse laufen
    if ! check_gnome_processes; then
        log_info "ℹ️  Keine GNOME Q&A Prozesse gefunden"
        send_gnome_notification "Q&A System" "Keine aktiven Prozesse gefunden" "dialog-information"
        exit 0
    fi
    
    # Stoppe Prozesse über PID-Dateien
    stop_process "Finder" "${FINDER_PID_FILE}"
    stop_process "Overlay" "${FINDER_PID_FILE}"
    
    # Fallback: Cleanup verwaister Prozesse
    cleanup_gnome_processes
    
    # Finale Prüfung
    sleep 1
    if pgrep -f "qa_overlay_gnome.py" > /dev/null || pgrep -f "qa_finder_gnome.py" > /dev/null; then
        log_warn "⚠️  Einige GNOME Prozesse laufen noch"
        send_gnome_notification "Q&A System" "Einige Prozesse konnten nicht gestoppt werden" "dialog-warning"
    else
        log_success "✅ GNOME Q&A System vollständig gestoppt"
        send_gnome_notification "Q&A System" "System erfolgreich gestoppt" "dialog-information"
    fi
    
    # Optional: Desktop-Cache aktualisieren
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    fi
}

# Hilfe anzeigen
show_help() {
    echo "GNOME Q&A System Stopper"
    echo ""
    echo "Verwendung: $0 [OPTIONEN]"
    echo ""
    echo "Optionen:"
    echo "  -h, --help     Zeige diese Hilfe"
    echo "  -f, --force    Erzwinge das Stoppen aller Prozesse"
    echo "  -q, --quiet    Stiller Modus (keine Benachrichtigungen)"
    echo ""
    echo "Beispiele:"
    echo "  $0              # Normales Stoppen"
    echo "  $0 --force      # Erzwungenes Stoppen"
    echo "  $0 --quiet      # Stilles Stoppen"
}

# Parameter verarbeiten
FORCE_STOP=false
QUIET_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--force)
            FORCE_STOP=true
            shift
            ;;
        -q|--quiet)
            QUIET_MODE=true
            shift
            ;;
        *)
            echo "Unbekannte Option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Überschreibe Notification-Funktion im quiet mode
if [[ "$QUIET_MODE" == true ]]; then
    send_gnome_notification() {
        return 0
    }
fi

# Force-Stop Modus
if [[ "$FORCE_STOP" == true ]]; then
    log_warn "⚡ Force-Stop Modus aktiviert"
    
    # Alle relevanten Prozesse sofort beenden
    pkill -KILL -f "qa_overlay_gnome.py" 2>/dev/null || true
    pkill -KILL -f "qa_finder_gnome.py" 2>/dev/null || true
    
    # PID-Dateien entfernen
    rm -f "${OVERLAY_PID_FILE}" "${FINDER_PID_FILE}"
    
    log_success "✅ Force-Stop abgeschlossen"
    send_gnome_notification "Q&A System" "Force-Stop abgeschlossen" "dialog-warning"
    exit 0
fi

# Normaler Stop
main "$@"
