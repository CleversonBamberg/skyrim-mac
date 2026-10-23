#!/bin/bash
# run-cx.sh — lança comandos com a engine CX26.3+DXMT (experimento 007+)
# DXMT tem diagnóstico próprio: DXMT_LOG_LEVEL
set -u

PROJECT="/Volumes/SSD120GB/skyrim-mac"
export WINEPREFIX="$PROJECT/prefix"
export PATH="$PROJECT/engine-cx/bin:$PATH"
export DYLD_FALLBACK_LIBRARY_PATH="$PROJECT/engine-cx/lib:$PROJECT/engine-cx/lib/external:$PROJECT/engine-cx/dylibs${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
export WINEDLLOVERRIDES="*dxgi,*d3d10core,*d3d11,*d3d12=b"
export WINEESYNC=1
export WINEMSYNC=1
export DXMT_LOG_LEVEL="${DXMT_LOG_LEVEL:-warn}"
export WINEDEBUG="${WINEDEBUG:--all}"

if [ "$1" = "steam" ]; then
    "$PROJECT/engine-cx/bin/wine64" "C:\\Program Files (x86)\\Steam\\Steam.exe" -no-cef-sandbox
else
    "$PROJECT/engine-cx/bin/wine64" "$@"
fi
