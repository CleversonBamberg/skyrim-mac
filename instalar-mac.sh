#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# instalar-mac.sh — Skyrim Special Edition no macOS (Apple Silicon)
# Instalação completa em 1 comando: patches + vozes + música + legendas PT-BR
#
# O QUE ELE FAZ:
#   [1] ffmpeg (via pip imageio-ffmpeg) — decoder WMA/voz
#   [2] patch no steam_api64.dll (Steam handshake no Wine)
#   [3] patch no SkyrimSE.exe (4× JE→JMP — não crashar no áudio)
#   [4] vozes: converte a dublagem PT-BR (se você tiver) + as falas que
#       faltam do BSA (inglês) → WAV PCM (o XAudio2 toca sem decoder WMA)
#   [5] música: converte TODAS as .xwm do Sounds.bsa → .wav PCM
#   [6] legendas PT-BR: instala a tradução (se você tiver)
#   [7] steam_appid.txt
#   [8] compressão APFS transparente (economiza ~50-99% do espaço dos PCM)
#
# PRÉ-REQUISITOS (veja README.md):
#   - macOS 26+ em Apple Silicon, com o engine Wine+D3DMetal já instalado
#   - Skyrim SE legítimo instalado pelo Steam (dentro do prefixo Wine)
#   - Opcional: dublagem PT-BR (Nexus #105861) e tradução de textos (Nexus #58406)
#
# USO:
#   ./instalar-mac.sh                          # só patches + vozes inglês + música
#   PTBR=/caminho/da/dublagem ./instalar-mac.sh # + dublagem PT-BR (pasta ou .7z)
#   TRAD=/caminho/da/traducao ./instalar-mac.sh # + legendas PT-BR (pasta ou .7z)
#
# ÁUDIO: vozes convertidas SEMPRE em qualidade NATIVA (1:1 com a fonte:
#       dublagem → 44.1kHz stereo | originais → 44.1kHz mono, como o jogo)
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLS="$SCRIPT_DIR/tools"

# ─── Configuração (variáveis de ambiente opcionais) ───
GAME_DIR="${GAME_DIR:-}"
PTBR="${PTBR:-}"
TRAD="${TRAD:-}"
COMPACTAR="${COMPACTAR:-1}"

WORK="$(mktemp -d -t skyrim-mac-instalacao)"
echo "temporários: $WORK (pode apagar ao final)"

# ─── [0] Detecta o jogo ───
echo ""
echo "═══ [0/8] Detectando o jogo ═══"
if [ -z "$GAME_DIR" ]; then
    for cand in \
        "$SCRIPT_DIR/prefix/drive_c/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition" \
        "$HOME/Library/Application Support/3Pi2/prefix/drive_c/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition"
    do
        if [ -f "$cand/SkyrimSE.exe" ]; then GAME_DIR="$cand"; break; fi
    done
fi
if [ -z "$GAME_DIR" ] || [ ! -f "$GAME_DIR/SkyrimSE.exe" ]; then
    echo "✗ Não achei o SkyrimSE.exe."
    echo "  Exporte o caminho do jogo e rode de novo:"
    echo "  GAME_DIR=\"/caminho/para/Skyrim Special Edition\" ./instalar-mac.sh"
    exit 1
fi
DATA="$GAME_DIR/Data"
echo "✓ jogo: $GAME_DIR"

# ─── [1] Ferramentas (ffmpeg via pip) ───
echo ""
echo "═══ [1/8] Ferramentas Python (ffmpeg) ═══"
if ! python3 -c "import imageio_ffmpeg" 2>/dev/null; then
    echo "  instalando imageio-ffmpeg (decoder WMA)…"
    pip3 install --quiet imageio-ffmpeg
fi
FFMPEG="$(python3 -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")"
echo "✓ ffmpeg: $FFMPEG"

# ─── [2] Patch steam_api64.dll ───
echo ""
echo "═══ [2/8] Patch Steam (steam_api64.dll) ═══"
DLL=""
for cand in "$GAME_DIR/steam_api64.dll" "$GAME_DIR/Data/steam_api64.dll"; do
    [ -f "$cand" ] && DLL="$cand" && break
done
if [ -z "$DLL" ]; then
    DLL="$(find "$GAME_DIR" -name "steam_api64.dll" -not -name "*.orig" | head -1)"
fi
if [ -n "$DLL" ]; then
    if [ -f "$DLL.orig" ]; then
        echo "✓ já patcheado (backup .orig existe): $DLL"
    else
        python3 "$TOOLS/patch_steam_api.py" "$DLL"
    fi
else
    echo "⚠ não achei steam_api64.dll (o jogo roda pelo Steam real — ok)"
fi

# ─── [3] Patch SkyrimSE.exe (áudio) ───
echo ""
echo "═══ [3/8] Patch SkyrimSE.exe (4× JE→JMP) ═══"
python3 "$TOOLS/patch_skyrimse_exe.py" "$GAME_DIR/SkyrimSE.exe"

# ─── [4] Vozes ═──
echo ""
echo "═══ [4/8] Vozes (xWMA → PCM; sem isso, o jogo fica MUDO no Wine) ═══"
mkdir -p "$DATA/sound/voice"

# [4a] dublagem PT-BR (opcional)
if [ -n "$PTBR" ]; then
    echo "── dublagem PT-BR: $PTBR"
    PTBR_DIR="$PTBR"
    if [ -f "$PTBR" ] && [[ "$PTBR" == *.7z ]]; then
        python3 -c "import py7zr" 2>/dev/null || pip3 install --quiet py7zr
        PTBR_DIR="$WORK/ptbr"
        python3 -c "import py7zr,sys; py7zr.SevenZipFile('$PTBR').extractall('$PTBR_DIR')"
    fi
    VOICES_SRC="$(find "$PTBR_DIR" -type d -name voice -path "*sound*" | head -1)"
    if [ -n "$VOICES_SRC" ]; then
        echo "  convertendo $(find "$VOICES_SRC" -name '*.fuz' | wc -l | tr -d ' ') falas da dublagem (nativa: 44.1kHz)…"
        python3 "$TOOLS/fuz_xwma_to_pcm.py" "$VOICES_SRC" "$WORK/ptbr-pcm/sound/voice"
        cp -R "$WORK/ptbr-pcm/sound/voice/." "$DATA/sound/voice/"
        echo "  ✓ dublagem instalada"
    else
        echo "  ⚠ não achei 'sound/voice' dentro da dublagem — pulando (vozes ficarão em inglês)"
    fi
fi

# [4b] completa com as vozes ORIGINAIS do BSA (inglês nativo, lotes, compressão)
echo "── completando com as vozes originais do jogo (inglês, qualidade nativa)…"
VOZ_DATA="$DATA" VOZ_INCREMENTAL=1 VOZ_MIN_LIVRE_GB=0.5 \
    python3 "$TOOLS/voz_nativa_lotes.py" 2>&1 | grep -vE "^  afs:" || true
echo "✓ total de .fuz no jogo: $(find "$DATA/sound/voice" -name '*.fuz' | wc -l | tr -d ' ')"

# ─── [5] Música ───
echo ""
echo "═══ [5/8] Música (269 .xwm → .wav PCM) ═══"
python3 "$TOOLS/bsa_extract.py" "$DATA/Skyrim - Sounds.bsa" "$WORK/musica-orig" --ext .xwm
NM=0
find "$WORK/musica-orig/music" -name "*.xwm" 2>/dev/null | while read -r fxwm; do
    rel="${fxwm#"$WORK/musica-orig/"}"      # ex: music/explore/xxx.xwm
    relsem="${rel%.xwm}"
    dst="$DATA/${relsem}.wav"
    mkdir -p "$(dirname "$dst")"
    if [ ! -f "$dst" ]; then
        "$FFMPEG" -y -hide_banner -loglevel error -i "$fxwm" -c:a pcm_s16le -f wav "$dst"
    fi
done
echo "✓ músicas em Data/music: $(find "$DATA/music" -name '*.wav' | wc -l | tr -d ' ')"

# ─── [6] Tradução de legendas (opcional) ───
echo ""
echo "═══ [6/8] Legendas PT-BR ═══"
if [ -n "$TRAD" ]; then
    TRAD_DIR="$TRAD"
    if [ -f "$TRAD" ] && [[ "$TRAD" == *.7z ]]; then
        python3 -c "import py7zr" 2>/dev/null || pip3 install --quiet py7zr
        TRAD_DIR="$WORK/trad"
        python3 -c "import py7zr,sys; py7zr.SevenZipFile('$TRAD').extractall('$TRAD_DIR')"
    fi
    PRINCIPAL="$(find "$TRAD_DIR" -type d -name "1.6.1130+" | head -1)"
    if [ -n "$PRINCIPAL" ]; then
        mkdir -p "$DATA/Strings" "$DATA/interface"
        cp "$PRINCIPAL/strings/"* "$DATA/Strings/" 2>/dev/null || true
        cp "$PRINCIPAL/interface/"* "$DATA/interface/" 2>/dev/null || true
        [ -f "$PRINCIPAL/Disease Description_DESC.ini" ] && cp "$PRINCIPAL/Disease Description_DESC.ini" "$DATA/" || true
        CC="$(find "$TRAD_DIR" -type d -path "*Creation Club*strings" | head -1)"
        if [ -n "$CC" ]; then
            cp "$CC/"* "$DATA/Strings/" 2>/dev/null || true
            echo "  ✓ strings do Creation Club instaladas"
        fi
        echo "✓ legendas PT-BR instaladas ($(ls "$DATA/Strings" | wc -l | tr -d ' ') arquivos de strings)"
    else
        echo "⚠ não achei a pasta '1.6.1130+' na tradução — verifique a estrutura"
    fi
else
    echo "– sem TRAD= definido — legendas ficam no idioma original (sem problema)"
fi

# ─── [7] steam_appid.txt ───
echo ""
echo "═══ [7/8] steam_appid.txt ═══"
if [ ! -f "$GAME_DIR/steam_appid.txt" ]; then
    echo "489830" > "$GAME_DIR/steam_appid.txt"
    echo "✓ criado (489830)"
else
    echo "✓ já existe: $(cat "$GAME_DIR/steam_appid.txt")"
fi

# ─── [8] Compressão APFS (opcional) ───
echo ""
echo "═══ [8/8] Compressão APFS (opcional — economiza muito espaço) ═══"
AFS="$(command -v afsctool || echo "$HOME/bin/afsctool")"
if [ "$COMPACTAR" = "1" ] && [ -x "$AFS" ]; then
    "$AFS" -c -j8 "$DATA/sound/voice" "$DATA/music" 2>&1 | tail -3 || true
    echo "✓ compressão aplicada (transparente — o jogo lê normal)"
else
    echo "– afsctool não encontrado ou COMPACTAR=0 — pulando (recomendado: https://github.com/RiatH/afsctool)"
fi

# ─── Fim ───
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✓ INSTALAÇÃO COMPLETA!                                       ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Pra jogar (com o Steam rodando dentro do prefixo):          ║"
echo "║    ./run-steam.sh steam     # abre o Steam (logue se pedir)   ║"
echo "║    ./run-skyrim.sh          # lança o jogo                    ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Dúvidas? README.md e LOG.md do repositório skyrim-mac       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
