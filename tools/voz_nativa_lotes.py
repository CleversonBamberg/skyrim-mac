#!/usr/bin/env python3
"""
voz_nativa_lotes.py — Vozes ORIGINAIS (inglês) em PCM de qualidade NATIVA.

Substitui todas as vozes do jogo pelas originais do BSA vanilla, convertidas
1:1 com a fonte (44.1kHz, canais originais — as vozes do jogo são mono 44.1kHz
nativas). Processa em LOTES por voicetype com compressão APFS entre lotes para
caber no disco, monitorando o espaço livre a cada lote.

Fluxo:
  [1] modo completo: apaga os .fuz atuais | incremental: mantém os instalados
  [2] por lote: extrai do BSA → converte nativo (fuz_xwma_to_pcm) →
      instala direto em Data/sound/voice/ → comprime pastas (afsctool)
  [3] resumo final

Uso:  python3 tools/voz_nativa_lotes.py
Env:  VOZ_DATA=<dir Data>  VOZ_BSA=<path do BSA>  VOZ_INCREMENTAL=1
      VOZ_MAX_LOTE=2500   VOZ_MIN_LIVRE_GB=2
"""
import os
import sys
import tempfile
import shutil
import subprocess
import concurrent.futures
import importlib.util
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.environ.get("VOZ_DATA") or "/Volumes/SSD120GB/skyrim-mac/prefix/drive_c/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition/Data"
BSA = os.environ.get("VOZ_BSA") or os.path.join(GAME, "Skyrim - Voices_en0.bsa")
VOICE = os.path.join(GAME, "sound/voice")
AFS = os.path.expanduser("~/bin/afsctool")
MAX_LOTE = int(os.environ.get("VOZ_MAX_LOTE", "2500"))
MIN_LIVRE_GB = float(os.environ.get("VOZ_MIN_LIVRE_GB", "2"))
INCREMENTAL = os.environ.get("VOZ_INCREMENTAL", "0") == "1"

sys.path.insert(0, HERE)
from bsa_extract import parse_bsa  # parser BSA v105 do projeto

spec = importlib.util.spec_from_file_location(
    "fuztool", os.path.join(HERE, "fuz_xwma_to_pcm.py"))
fuztool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fuztool)
# Sem FUZ_RATE/FUZ_CH no ambiente → o conversor mantém 44.1kHz stereo nativo


def livre_gb(path="/Volumes/SSD120GB"):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / 1e9


def comprimir(pastas):
    if not os.path.exists(AFS):
        print("  ⚠ afsctool não encontrado — sem compressão (ok, só ocupa mais)")
        return
    r = subprocess.run([AFS, "-c", "-j8"] + pastas,
                       capture_output=True, timeout=3600)
    linhas = [l for l in r.stdout.decode(errors="replace").splitlines() if l.strip()]
    for l in linhas[-2:]:
        print("  afs:", l)


def main():
    print(f"espaço livre inicial: {livre_gb():.1f}GB | BSA: {BSA}")

    # ── [1] apaga as vozes atuais (só no modo completo)
    if INCREMENTAL:
        print("modo incremental: mantém as instaladas, só converte as faltantes")
    else:
        n_antigos = sum(len(fs) for _, _, fs in os.walk(VOICE))
        print(f"apagando {n_antigos} .fuz atuais…")
        for entry in os.listdir(VOICE):
            p = os.path.join(VOICE, entry)
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
        print(f"  ✓ apagado | livre: {livre_gb():.1f}GB")

    # ── [2] parse do BSA + lotes por voicetype
    f, mm, entries, data_start = parse_bsa(BSA)
    por_pasta = defaultdict(list)
    for path, size, off in entries:
        por_pasta[os.path.dirname(path)].append((path, size, off))
    pastas = sorted(por_pasta)

    lotes, cur, n = [], [], 0
    for p in pastas:
        cur.append(p)
        n += len(por_pasta[p])
        if n >= MAX_LOTE:
            lotes.append(cur)
            cur, n = [], 0
    if cur:
        lotes.append(cur)
    print(f"{len(entries)} falas em {len(pastas)} voicetypes → {len(lotes)} lotes de ≤{MAX_LOTE}")

    temp = tempfile.mkdtemp(prefix="vozes-en-")
    total_ok = total_err = 0

    def conv(args):
        path, size, off = args
        if INCREMENTAL and os.path.exists(os.path.join(GAME, path)):
            return "skip"
        try:
            src = os.path.join(temp, path)
            os.makedirs(os.path.dirname(src), exist_ok=True)
            with open(src, "wb") as fh:
                fh.write(mm[off:off + size])
            dst = os.path.join(GAME, path)  # path relativo ao Data
            res = fuztool.convert_file(src, dst)
            os.remove(src)
            return res[0] if isinstance(res, tuple) else str(res)
        except Exception as e:
            return f"error: {e}"

    for i, lote in enumerate(lotes, 1):
        tasks = [e for p in lote for e in por_pasta[p]]
        print(f"\n══ lote {i}/{len(lotes)}: {len(tasks)} falas | livre: {livre_gb():.1f}GB")
        with concurrent.futures.ThreadPoolExecutor(max_workers=11) as ex:
            results = list(ex.map(conv, tasks))
        ok = sum(1 for r in results if r == "ok")
        skip = sum(1 for r in results if r == "skip")
        err = len(results) - ok - skip
        total_ok += ok
        total_err += err
        if err:
            for r in [r for r in results if r != "ok" and r != "skip"][:5]:
                print("  !", r)
        if ok > 0:
            comprimir([os.path.join(GAME, p) for p in lote])
        print(f"  ✓ {ok} ok, {skip} já existentes, {err} err | acumulado: {total_ok} | livre: {livre_gb():.1f}GB")
        if livre_gb() < MIN_LIVRE_GB:
            print("  ⛔ ESPAÇO BAIXO — parando para não encher o disco.")
            print("     Rode de novo quando liberar espaço (continua de onde parou)")
            break

    shutil.rmtree(temp, ignore_errors=True)
    n_final = sum(len(fs) for _, _, fs in os.walk(VOICE))
    print(f"\n════════════════════════════════════════")
    print(f"FINAL: {total_ok} vozes INGLESAS instaladas (44.1kHz stereo nativo), {total_err} erros")
    print(f"total .fuz no jogo: {n_final} | espaço livre: {livre_gb():.1f}GB")


if __name__ == "__main__":
    main()
