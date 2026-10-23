#!/usr/bin/env python3
"""
fuz_xwma_to_pcm.py — Converte o áudio xWMA (WMA v2) dentro dos .fuz de Skyrim SE
para WAV PCM 16-bit, mantendo o LIP sync intacto.

LAYOUT FUZ PC SSE (descoberto 2026-10-23, confirmado em 8000+ arquivos do mod
PT-BR e nos .fuz vanilla do Voices_en0.bsa):

    offset 0:  "FUZE" (magic)
    offset 4:  u32 version (1)
    offset 8:  u32 lipSize        ← antes erradamente interpretado como "audio_size"
    offset 12: LIP data (lipSize bytes, começa com 01 00 00 00)
    offset 12+lipSize: RIFF....XWMA   ← o SOM é um RIFF COMPLETO no final!
        fmt tag 0x0161 = WMA v2 (xWMA), 44100 Hz
        (alguns arquivos: lipSize=0 → sem LIP, RIFF direto em offset 12)

PROBLEMA: no Wine, o decoder WMA da Microsoft (wmadmod.dll) é um stub →
o jogo extrai o xWMA mas não consegue decodificar → vozes mudas.

SOLUÇÃO: decodificar o xWMA com ffmpeg (decoder WMA v2 nativo) e remontar
o .fuz com WAV PCM 16-bit. O XAudio2 toca PCM direto — sem decoder externo.

Uso:
    python3 fuz_xwma_to_pcm.py <arquivo.fuz>                     # single
    python3 fuz_xwma_to_pcm.py <dir_in> <dir_out> [filtro]      # batch
        filtro: substring de caminho (ex.: "mq101")
"""
import struct
import subprocess
import os
import sys
import tempfile
import concurrent.futures

FFMPEG = os.path.expanduser(
    "~/Library/Python/3.9/lib/python/site-packages/imageio_ffmpeg/"
    "binaries/ffmpeg-macos-aarch64-v7.1"
)
if not os.path.exists(FFMPEG):
    FFMPEG = subprocess.run(
        ["python3", "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
        capture_output=True, text=True
    ).stdout.strip()


def parse_fuz(path):
    """Retorna (lip_size, lip_data, riff) ou None se inválido."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] not in (b"FUZE", b"FUZC"):
        return None
    lip_size = struct.unpack_from("<I", data, 8)[0]
    if 12 + lip_size > len(data):
        return None
    lip = data[12:12 + lip_size]
    riff = data[12 + lip_size:]
    if riff[:4] != b"RIFF":
        return None
    return lip_size, lip, riff


def riff_fmt_tag(riff):
    """Percorre chunks do RIFF e retorna (fmt_tag, channels, rate) ou None."""
    pos = 12
    while pos + 8 <= len(riff):
        cid = riff[pos:pos + 4]
        csz = struct.unpack_from("<I", riff, pos + 4)[0]
        if cid == b"fmt " and csz >= 16:
            tag = struct.unpack_from("<H", riff, pos + 8)[0]
            ch = struct.unpack_from("<H", riff, pos + 10)[0]
            rate = struct.unpack_from("<I", riff, pos + 12)[0]
            return tag, ch, rate
        pos += 8 + csz + (csz & 1)
    return None


def build_fuz(lip_size, lip, riff):
    """Monta o .fuz layout B: FUZE + ver + lipSize + LIP + RIFF."""
    return (b"FUZE"
            + struct.pack("<I", 1)
            + struct.pack("<I", lip_size)
            + lip
            + riff)


# Overrides opcionais (0 = manter rate/canais originais do xWMA)
OUT_RATE = int(os.environ.get("FUZ_RATE", "0"))
OUT_CHANNELS = int(os.environ.get("FUZ_CH", "0"))

_TMPDIR = tempfile.mkdtemp(prefix="fuz_pcm_")
_counter = [0]


def _tmp_path(suffix):
    _counter[0] += 1
    return os.path.join(_TMPDIR, f"{os.getpid()}_{_counter[0]}{suffix}")


def xwma_to_pcm_wav(riff):
    """Decodifica RIFF/xWMA → WAV PCM 16-bit via ffmpeg. Retorna bytes."""
    src = _tmp_path("_in.xwm")
    dst = _tmp_path("_out.wav")
    with open(src, "wb") as f:
        f.write(riff)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", src]
    if OUT_RATE:
        cmd += ["-ar", str(OUT_RATE)]
    if OUT_CHANNELS:
        cmd += ["-ac", str(OUT_CHANNELS)]
    cmd += ["-c:a", "pcm_s16le", "-f", "wav", dst]
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    if r.returncode != 0 or not os.path.exists(dst):
        raise RuntimeError(f"ffmpeg: {r.stderr.decode()[:80]}")
    with open(dst, "rb") as f:
        out = f.read()
    os.remove(src)
    os.remove(dst)
    return out


def convert_file(in_path, out_path):
    """Converte um .fuz. Retorna (status, detalhe)."""
    try:
        parsed = parse_fuz(in_path)
        if parsed is None:
            return ("parse_fail", in_path)
        lip_size, lip, riff = parsed
        fmt = riff_fmt_tag(riff)
        if fmt and fmt[0] == 0x0001:
            new_riff = riff  # já é PCM — mantém
        else:
            new_riff = xwma_to_pcm_wav(riff)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(build_fuz(lip_size, lip, new_riff))
        return ("ok", in_path)
    except Exception as e:
        return ("error", f"{in_path}: {e}")


def batch(in_dir, out_dir, filtro=None, jobs=None):
    if jobs is None:
        jobs = max(1, (os.cpu_count() or 4) - 1)
    tasks = []
    for root, dirs, files in os.walk(in_dir):
        for fn in files:
            if not fn.lower().endswith(".fuz"):
                continue
            in_path = os.path.join(root, fn)
            rel = os.path.relpath(in_path, in_dir)
            if filtro and filtro.lower() not in rel.lower():
                continue
            tasks.append((in_path, os.path.join(out_dir, rel)))
    print(f"{len(tasks)} arquivos a converter | {jobs} workers | ffmpeg: {os.path.basename(FFMPEG)}")
    stats = {"ok": 0, "parse_fail": 0, "error": 0}
    errors = []
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
        for status, detail in ex.map(convert_file_wrapper, tasks):
            stats[status] += 1
            if status == "error" and len(errors) < 10:
                errors.append(detail)
            done += 1
            if done % 2000 == 0:
                print(f"  {done}/{len(tasks)} ({stats['ok']} ok, {stats['error']} err)")
    print(f"\n✓ final: {stats['ok']} ok | {stats['parse_fail']} parse_fail | {stats['error']} erros")
    for e in errors:
        print(f"  ! {e}")


def convert_file_wrapper(task):
    return convert_file(*task)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    if len(sys.argv) == 2:
        # single file → stdout
        p = sys.argv[1]
        parsed = parse_fuz(p)
        if parsed is None:
            print("não é FUZE/FUZC válido")
            sys.exit(1)
        lip_size, lip, riff = parsed
        fmt = riff_fmt_tag(riff)
        print(f"lip: {lip_size}B | som: {len(riff)}B | fmt: {fmt}")
        if fmt and fmt[0] == 0x0001:
            print("já é PCM")
        else:
            pcm = xwma_to_pcm_wav(riff)
            print(f"decodificado: {len(pcm)}B PCM")
            new = build_fuz(lip_size, lip, pcm)
            with open(p + ".pcm.fuz", "wb") as f:
                f.write(new)
            print(f"salvo: {p}.pcm.fuz")
    else:
        in_dir, out_dir = sys.argv[1], sys.argv[2]
        filtro = sys.argv[3] if len(sys.argv) > 3 else None
        batch(in_dir, out_dir, filtro)


if __name__ == "__main__":
    main()
