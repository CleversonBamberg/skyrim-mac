#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  INSTALAR.command — Skyrim Special Edition no macOS (Apple Silicon)
#  Assistente de primeira instalação: duplo-clique e siga as instruções.
#
#  O que este assistente faz:
#    [1] Checa o ambiente (Apple Silicon, Python)
#    [2] Localiza a engine Wine+D3DMetal (pasta engine/ ou 3Pi2) e linka
#    [3] Cria o prefixo Wine (se não existir)
#    [4] Instala o Steam dentro do prefixo (baixa da Valve se necessário)
#    [5] VOCÊ faz login e instala o Skyrim pela Biblioteca do Steam
#    [6] Detecta dublagem/tradução (.7z) colocadas nesta pasta
#    [7] Roda instalar-mac.sh (patches + vozes + música + legendas + compressão)
#    [8] Cria o atalho "Skyrim.command" na Mesa (duplo-clique pra jogar!)
#
#  Requisitos (não podem ir no pacote, por licença):
#    - Engine Wine+D3DMetal (veja README: ~/Library/Application Support/3Pi2)
#    - Skyrim Special Edition no Steam (o próprio usuário baixa)
#    - Opcional: dublagem PT-BR (Nexus #105861) e tradução (Nexus #58406)
# ═══════════════════════════════════════════════════════════════════════════
set -uo pipefail

PROJECT="$(cd "$(dirname "$0")" && pwd)"
TOOLS="$PROJECT/tools"
PREFIX="$PROJECT/prefix"

negrito() { printf "\033[1m%s\033[0m\n" "$1"; }
ok()      { printf "  \033[32m✓\033[0m %s\n" "$1"; }
falha()   { printf "  \033[31m✗ %s\033[0m\n" "$1"; }
pergunta() { printf "\033[1m%s\033[0m" "$1"; read -r; }

clear 2>/dev/null || true
echo "════════════════════════════════════════════════════════"
echo "   Skyrim Special Edition no Mac — instalação assistida"
echo "════════════════════════════════════════════════════════"
echo ""

# ─── [1] Ambiente ───
echo "─── [1/7] Checando o ambiente ───"
ARCH="$(uname -m)"
if [ "$ARCH" != "arm64" ]; then
    falha "Este pacote é para Apple Silicon (M1–M6). Seu Mac: $ARCH"
    exit 1
fi
ok "Apple Silicon ✓"
if ! command -v python3 >/dev/null; then
    falha "Python 3 não encontrado. Instale com: xcode-select --install"
    exit 1
fi
ok "python3 ✓"

# ─── [2] Engine Wine+D3DMetal ───
echo ""
echo "─── [2/7] Engine Wine + D3DMetal ───"

detectar_engine() {
    # 1) já presente no projeto
    if [ -x "$PROJECT/engine/bin/wine64" ]; then ok "engine presente em engine/"; return 0; fi
    # 2) variável manual ENGINE_DIR
    if [ -n "${ENGINE_DIR:-}" ] && [ -x "$ENGINE_DIR/bin/wine64" ]; then
        ln -sfn "$ENGINE_DIR" "$PROJECT/engine"
        ok "engine linkada (ENGINE_DIR): $ENGINE_DIR"; return 0
    fi
    # 3) app 3Pi2 (engines em bundle: <engine>/Contents/Resources/bin/wine64)
    ENGS="$HOME/Library/Application Support/3Pi2/Engines"
    if [ -d "$ENGS" ]; then
        CAND="$(find "$ENGS" -maxdepth 6 \( -type f -o -type l \) -name wine64 -path "*bin*" 2>/dev/null \
                | grep -iE "sikarugir|d3dmetal" | head -1)"
        [ -z "$CAND" ] && CAND="$(find "$ENGS" -maxdepth 6 \( -type f -o -type l \) -name wine64 -path "*bin*" 2>/dev/null | head -1)"
        if [ -n "$CAND" ]; then
            ED="$(dirname "$(dirname "$CAND")")"
            ln -sfn "$ED" "$PROJECT/engine"
            ok "engine do 3Pi2 linkada: $ED"; return 0
        fi
    fi
    # 4) Apple Game Porting Toolkit oficial (o .pkg instala em /usr/local/lib/wine)
    if [ -x "/usr/local/lib/wine/bin/wine64" ]; then
        ln -sfn "/usr/local/lib/wine" "$PROJECT/engine"
        ok "engine do Apple GPTK (/usr/local/lib/wine)"; return 0
    fi
    return 1
}

if ! detectar_engine; then
    falha "Engine Wine+D3DMetal não encontrada"
    echo ""
    echo "  Vou abrir o site oficial da Apple no seu navegador."
    echo "  Faça login com Apple ID (de graça) e baixe o “Game Porting Toolkit”,"
    echo "  depois rode o .pkg que baixar. Alternativas: instalar o app 3Pi2,"
    echo "  ou apontar uma engine que você já tenha:"
    echo "    ENGINE_DIR=\"/caminho/da/engine\" ./INSTALAR.command"
    echo ""
    open "https://developer.apple.com/games/game-porting-toolkit/" 2>/dev/null || true
    while ! detectar_engine; do
        pergunta "  Aperte ENTER quando terminar a instalação (Ctrl+C pra sair)…"
    done
fi
WINE64="$PROJECT/engine/bin/wine64"

# ─── [3] Prefixo Wine ───
echo ""
echo "─── [3/7] Prefixo Wine ───"
export WINEPREFIX="$PREFIX"
export PATH="$PROJECT/engine/bin:$PATH"
export DYLD_FALLBACK_LIBRARY_PATH="$PROJECT/engine/lib:$PROJECT/engine/lib/external:$PROJECT/engine/dylibs"
if [ ! -d "$PREFIX/drive_c/windows" ]; then
    echo "  criando prefixo (wineboot)…"
    export WINEDLLOVERRIDES="mscoree,mshtml="
    "$WINE64" wineboot -i >/dev/null 2>&1 && ok "prefixo criado" || { falha "wineboot falhou"; exit 1; }
else
    ok "prefixo já existe"
fi

# ─── [4] Steam ───
echo ""
echo "─── [4/7] Steam dentro do prefixo ───"
STEAM_EXE="$PREFIX/drive_c/Program Files (x86)/Steam/Steam.exe"
if [ ! -f "$STEAM_EXE" ]; then
    SETUP="$TOOLS/SteamSetup.exe"
    if [ ! -f "$SETUP" ]; then
        echo "  baixando instalador oficial da Valve…"
        curl -fsSL -o "$SETUP" "https://cdn.cloudflare.steamstatic.com/client/installer/SteamSetup.exe" \
            || { falha "download do SteamSetup falhou — verifique sua internet"; exit 1; }
    fi
    negrito "  → Vai abrir o instalador do Steam. Clique em Install/Instalar."
    "$WINE64" "$SETUP" || true
    sleep 2
fi
if [ -f "$STEAM_EXE" ]; then
    ok "Steam instalado"
else
    falha "Steam não instalado — rode de novo quando o instalador terminar"
    exit 1
fi

# ─── [5] Skyrim via Steam ───
echo ""
echo "─── [5/7] Skyrim Special Edition ───"
GAME_DIR="$PREFIX/drive_c/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition"
if [ ! -f "$GAME_DIR/SkyrimSE.exe" ]; then
    negrito "Agora é com você:"
    echo "   1. Abra o Steam (vai subir junto com o passo anterior — se não abriu,"
    echo "      rode: ./run-steam.sh steam) e faça LOGIN."
    echo "   2. Biblioteca → The Elder Scrolls V: Skyrim Special Edition → Instalar."
    echo "   3. Aguarde o download terminar (~15GB)."
    echo ""
    while [ ! -f "$GAME_DIR/SkyrimSE.exe" ]; do
        pergunta "  Aperte ENTER quando o Skyrim terminar de instalar…"
    done
fi
ok "SkyrimSE.exe encontrado"

# ─── [6] Mods PT-BR (.7z na pasta = auto-detect) ───
echo ""
echo "─── [6/7] Procurando dublagem/tradução nesta pasta ───"
PTBR=""; TRAD=""
python3 -c "import py7zr" 2>/dev/null || pip3 install --quiet py7zr
shopt -s nullglob
for f in "$PROJECT"/*.7z; do
    TIPO="$(python3 - "$f" << 'PYEOF'
import py7zr, sys
try:
    with py7zr.SevenZipFile(sys.argv[1]) as z:
        ns = z.getnames()
    if any("sound/voice" in n or "sound\\voice" in n for n in ns):
        print("dublagem")
    elif any("strings" in n.lower() for n in ns):
        print("traducao")
    else:
        print("?")
except Exception:
    print("erro")
PYEOF
)"
    case "$TIPO" in
        dublagem)
            echo "  Achei a dublagem PT-BR: $(basename "$f")"
            pergunta "  Vozes DUBLADAS ou ORIGINAIS? [S]=dubladas, n=originais: "
            case "$REPLY" in
                n|N)
                    echo "  ✓ vozes ORIGINAIS em inglês (as legendas continuam PT-BR!)"
                    ;;
                *)
                    PTBR="$f"
                    ok "vozes: DUBLAGEM PT-BR"
                    ;;
            esac
            ;;
        traducao) TRAD="$f"; ok "tradução: $(basename "$f")" ;;
        *) echo "  ? ignorando $(basename "$f") (não parece dublagem nem tradução)" ;;
    esac
done
[ -z "$PTBR" ] && echo "  – sem dublagem (vozes ficarão em inglês — sem problema)"
[ -z "$TRAD" ] && echo "  – sem tradução (textos em inglês — sem problema)"

# ─── [7] Instalação completa ───
echo ""
echo "─── [7/7] Instalação completa (patches + vozes + música + legendas) ───"
export PTBR TRAD
"$PROJECT/instalar-mac.sh" || { falha "instalador falhou — veja as mensagens acima"; exit 1; }

# ─── Atalho na Mesa ───
echo ""
echo "─── Criando atalho na Mesa ───"
bash "$TOOLS/criar_atalho.sh"

echo ""
echo "════════════════════════════════════════════════════════"
echo "   🎉 PRONTO! Procure “Skyrim.command” na sua Mesa."
echo "      Duplo-clique e o jogo abre (Steam + Skyrim)."
echo ""
echo "      Legendas/dublagem PT-BR, vozes e música: tudo pronto!"
echo "════════════════════════════════════════════════════════"
