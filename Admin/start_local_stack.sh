#!/usr/bin/env bash
# Omniverse local stack launcher (Termux, Linux, macOS, Git Bash on Windows)
# Starts: daemon (:9100 telemetry, :5000 IPC, :5005 P2P, UDP 9101) -> OmniMind agent -> live monitor.
# Run from the repo root:  bash Admin/start_local_stack.sh
# Optional: OMNI_WITH_PAYMENTS=1 also starts omni_core/omni_crypto_payment_gateway.py

set -u
cd "$(dirname "$0")/.." || exit 1
PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python
PIDS=()

cleanup() {
  trap - EXIT INT TERM
  echo
  echo "[*] Stopping local stack..."
  for pid in "${PIDS[@]:-}"; do [ -n "$pid" ] && kill "$pid" 2>/dev/null; done
}
trap cleanup EXIT INT TERM   # set BEFORE anything starts, so Ctrl+C always cleans up

echo "=================================================================="
echo " STARTING OMNIVERSE LOCAL STACK"
echo "=================================================================="

# Stop stale copies left over from an earlier run
pkill -f "Admin/omni_live_daemon_server.py" 2>/dev/null
pkill -f "Admin/omnimind_agent_telemetry_engine.py" 2>/dev/null

"$PY" Admin/omni_live_daemon_server.py > daemon.log 2>&1 &
PIDS+=($!)

# Wait up to 10s for the daemon instead of a fixed sleep
up=0
for _ in $(seq 1 20); do
  if curl -s -o /dev/null http://127.0.0.1:9100/api/v1/telemetry/node-health; then up=1; break; fi
  sleep 0.5
done
if [ "$up" -ne 1 ]; then
  echo "[!] Daemon did not come up on :9100. Last log lines:"
  tail -n 15 daemon.log
  echo "    (Port already in use? Check with: python3 Admin/check_ports_status.py)"
  exit 1
fi
echo "  - Daemon telemetry (:9100):  ONLINE   (log: daemon.log)"

"$PY" Admin/omnimind_agent_telemetry_engine.py > omnimind.log 2>&1 &
PIDS+=($!)
echo "  - OmniMind agent:            STARTED  (log: omnimind.log)"

if [ "${OMNI_WITH_PAYMENTS:-0}" = "1" ] && [ -f omni_core/omni_crypto_payment_gateway.py ]; then
  "$PY" omni_core/omni_crypto_payment_gateway.py > payments.log 2>&1 &
  PIDS+=($!)
  echo "  - Payment gateway:           STARTED  (log: payments.log)"
fi

echo "------------------------------------------------------------------"
echo " Launching live telemetry monitor (Ctrl+C stops everything)..."
sleep 1
"$PY" Admin/omni_telemetry_monitor.py "$@"
