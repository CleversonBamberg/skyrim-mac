#!/bin/bash
# run-skyrim.sh — lançamento do Skyrim no projeto skyrim-mac
# Recipe validada (mesma do 3Pi2): Sikarugir 10.0 + D3DMetal
set -u

PROJECT="/Volumes/SSD120GB/skyrim-mac"
GAME="/Volumes/SSD120GB/Skyrim Special Edition"
export WINEPREFIX="$PROJECT/prefix"
export PATH="$PROJECT/engine/bin:$PATH"
export DYLD_FALLBACK_LIBRARY_PATH="$PROJECT/engine/lib:$PROJECT/engine/lib/external:$PROJECT/engine/dylibs"
export D3DMETAL_FORCE=1
export MOLTENVKCX=1
export WINEESYNC=1
export WINEMSYNC=1
export WINEDEBUG="${WINEDEBUG:--all}"

# 1) inicializa o prefixo se necessário
if [ ! -d "$WINEPREFIX/drive_c/windows" ]; then
    echo "[run] Inicializando prefixo Wine…"
    export WINEDLLOVERRIDES="mscoree,mshtml="
    "$PROJECT/engine/bin/wine64" wineboot -i
fi

# 2) lança o jogo DIRETO (sem launcher)
"$PROJECT/engine/bin/wine64" "$GAME/SkyrimSE.exe" "$@"
