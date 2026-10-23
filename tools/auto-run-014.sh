#!/bin/bash
# auto-run-014.sh — espera Steam pronto → lança Skyrim com relay → espera a morte → informa
P="/Volumes/SSD120GB/skyrim-mac"
LOG="$P/logs/run-014-relay-steam.log"

echo "[auto] esperando Steam ficar pronto (webhelpers > 0 e estáveis)…"
READY=0
for i in $(seq 1 120); do
    WH=$(ps aux | grep -c "[s]teamwebhelper")
    if [ "$WH" -ge 4 ]; then READY=1; break; fi
    sleep 5
done
if [ "$READY" != "1" ]; then echo "[auto] Steam nunca ficou pronto — abortando"; exit 1; fi
echo "[auto] Steam pronto — lançando o jogo com relay às $(date +%H:%M:%S)"

export WINEPREFIX="$P/prefix"
export DYLD_FALLBACK_LIBRARY_PATH="$P/engine/lib:$P/engine/lib/external:$P/engine/dylibs"
export PATH="$P/engine/bin:$PATH"
export D3DMETAL_FORCE=1 MOLTENVKCX=1 WINEESYNC=1 WINEMSYNC=1
export WINEDEBUG="+relay"

"$P/engine/bin/wine64" "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Skyrim Special Edition\\SkyrimSE.exe" > "$LOG" 2>&1
CODE=$?
echo "[auto] jogo terminou com código $CODE às $(date +%H:%M:%S)"
echo "[auto] tamanho do log: $(ls -lh "$LOG" | awk '{print $5}')"
