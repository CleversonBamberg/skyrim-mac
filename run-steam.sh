#!/bin/bash
# run-steam.sh — lança o CLIENTE Steam dentro do prefixo do projeto
# Com WINEDEBUG herdado: o jogo iniciado pelo Steam cai no mesmo log.
set -u

PROJECT="/Volumes/SSD120GB/skyrim-mac"
export WINEPREFIX="$PROJECT/prefix"
export PATH="$PROJECT/engine/bin:$PATH"
export DYLD_FALLBACK_LIBRARY_PATH="$PROJECT/engine/lib:$PROJECT/engine/lib/external:$PROJECT/engine/dylibs"
export D3DMETAL_FORCE=1
export MOLTENVKCX=1
export WINEESYNC=1
export WINEMSYNC=1
export WINEDEBUG="${WINEDEBUG:--all}"

if [ "$1" = "setup" ]; then
    # Instalador do Steam (janela gráfica — você clica em Instalar)
    "$PROJECT/engine/bin/wine64" "$PROJECT/tools/SteamSetup.exe"
elif [ "$1" = "steam" ]; then
    # Cliente Steam (atualiza sozinho na primeira execução)
    "$PROJECT/engine/bin/wine64" "$WINEPREFIX/drive_c/Program Files (x86)/Steam/Steam.exe" -no-cef-sandbox
fi
