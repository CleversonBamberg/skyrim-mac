#!/bin/bash
# criar_atalho.sh — cria "Skyrim.command" na Mesa do usuário (duplo-clique = jogar)
# O atalho sobe o Steam dentro do prefixo (se não estiver rodando) e lança o jogo.
set -euo pipefail

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
DESKTOP="$HOME/Desktop"
if [ ! -w "$DESKTOP" ]; then
    DESKTOP="$PROJECT"
    echo "⚠ Mesa não disponível — atalho criado em: $PROJECT"
fi

TARGET="$DESKTOP/Skyrim.command"
cat > "$TARGET" << EOF
#!/bin/bash
# Skyrim no Mac — atalho gerado por skyrim-mac
P="$PROJECT"
export WINEPREFIX="\$P/prefix"
W="\$P/engine/bin/wine64"
export PATH="\$P/engine/bin:\$PATH"
export DYLD_FALLBACK_LIBRARY_PATH="\$P/engine/lib:\$P/engine/lib/external:\$P/engine/dylibs"
export D3DMETAL_FORCE=1
export MOLTENVKCX=1
export WINEESYNC=1
export WINEMSYNC=1
export WINEDEBUG=-all
export SteamAppId=489830

STEAM="\$WINEPREFIX/drive_c/Program Files (x86)/Steam/Steam.exe"
GAME="\$WINEPREFIX/drive_c/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition/SkyrimSE.exe"

# Steam rodando? Se não, sobe e espera
if ! "\$W" tasklist 2>/dev/null | grep -qi "steam.exe"; then
    echo "Iniciando Steam…"
    nohup "\$W" "\$STEAM" -no-cef-sandbox >/dev/null 2>&1 &
    for i in \$(seq 1 45); do
        sleep 2
        if "\$W" tasklist 2>/dev/null | grep -qi "steam.exe"; then
            echo "Steam pronto!"
            break
        fi
    done
    sleep 5
fi

echo "Lançando Skyrim… (mantenha esta janela aberta enquanto joga)"
exec "\$W" "\$GAME"
EOF

chmod +x "$TARGET"
echo "✓ atalho criado: $TARGET"
