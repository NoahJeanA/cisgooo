#!/bin/bash
# stop_qa_system.sh - Sicheres Stoppen des Q&A Systems

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OVERLAY_PID_FILE="${SCRIPT_DIR}/qa_overlay.pid"
FINDER_PID_FILE="${SCRIPT_DIR}/qa_finder.pid"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

stop_process() {
    local name=$1
    local pid_file=$2
    
    if [[ -f "${pid_file}" ]]; then
        local pid=$(cat "${pid_file}" 2>/dev/null || echo "")
        if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
            log_info "Stoppe ${name} (PID: ${pid})"
            
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
                log_warn "Force kill für ${name} (PID: ${pid})"
                kill -KILL "${pid}" 2>/dev/null || true
            fi
            
            log_success "${name} gestoppt"
        else
            log_info "${name} war nicht aktiv"
        fi
        rm -f "${pid_file}"
    else
        log_info "Keine PID-Datei für ${name} gefunden"
    fi
}

main() {
    log_info "🛑 Stoppe Q&A System..."
    
    # Stoppe Prozesse über PID-Dateien
    stop_process "Finder" "${FINDER_PID_FILE}"
    stop_process "Overlay" "${OVERLAY_PID_FILE}"
    
    # Fallback: Alle relevanten Python-Prozesse beenden
    log_info "🧹 Suche nach verwaisten Prozessen..."
    
    local overlay_pids=$(pgrep -f "qa_overlay.py" 2>/dev/null || true)
    local finder_pids=$(pgrep -f "qa_finder.py" 2>/dev/null || true)
    
    if [[ -n "${overlay_pids}" ]]; then
        log_warn "Gefundene Overlay-Prozesse: ${overlay_pids}"
        echo "${overlay_pids}" | xargs -r kill -TERM 2>/dev/null || true
        sleep 2
        echo "${overlay_pids}" | xargs -r kill -KILL 2>/dev/null || true
    fi
    
    if [[ -n "${finder_pids}" ]]; then
        log_warn "Gefundene Finder-Prozesse: ${finder_pids}"
        echo "${finder_pids}" | xargs -r kill -TERM 2>/dev/null || true
        sleep 2
        echo "${finder_pids}" | xargs -r kill -KILL 2>/dev/null || true
    fi
    
    # Prüfe ob wirklich alles gestoppt ist
    if pgrep -f "qa_overlay.py" > /dev/null || pgrep -f "qa_finder.py" > /dev/null; then
        log_warn "⚠️  Einige Prozesse laufen noch"
    else
        log_success "✅ Q&A System vollständig gestoppt"
    fi
}

main "$@"