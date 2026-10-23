#!/usr/bin/env python3
"""
fuz_convert.py — Extrai XMA de .fuz, decodifica via GStreamer, repackea com PCM
Formato FUZ:
  0x00: "FUZC" magic (4 bytes)
  0x04: version (4 bytes)
  0x08: xma_size (4 bytes)
  0x0C: lip_size (4 bytes)
  0x10: XMA data (xma_size bytes) — é um RIFF/WAVE/XMA
  0x10+xma_size: LIP sync data (lip_size bytes)
"""
import struct
import os
import subprocess
import sys
import tempfile

GST_BIN = "/Volumes/SSD120GB/skyrim-mac/GStreamer.framework/Versions/1.0/bin"
GST_LIB = "/Volumes/SSD120GB/skyrim-mac/GStreamer.framework/Versions/1.0/lib"
GST_PLUGINS = f"{GST_LIB}/gstreamer-1.0"

ENV = {
    "PATH": f"{GST_BIN}:/usr/bin:/bin",
    "DYLD_FALLBACK_LIBRARY_PATH": GST_LIB,
    "GST_PLUGIN_SYSTEM_PATH": GST_PLUGINS,
    "GST_PLUGIN_SYSTEM_PATH_1_0": GST_PLUGINS,
}


def parse_fuz(path):
    """Extrai os componentes de um arquivo .fuz"""
    data = open(path, "rb").read()
    if data[:4] not in (b"FUZC", b"FUZE"):
        return None
    
    version = struct.unpack_from("<I", data, 4)[0]
    xma_size = struct.unpack_from("<I", data, 8)[0]
    lip_size = struct.unpack_from("<I", data, 12)[0]
    
    xma_data = data[16:16+xma_size]
    lip_data = data[16+xma_size:16+xma_size+lip_size]
    
    return {
        "version": version,
        "xma": xma_data,
        "lip": lip_data,
        "xma_size": xma_size,
        "lip_size": lip_size,
    }


def decode_xma_to_wav(xma_data, output_path):
    """Decodifica XMA (RIFF/WAVE) para WAV PCM usando gst-launch"""
    # Salva o XMA num arquivo temporário
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(xma_data)
        tmp_path = tmp.name
    
    try:
        # Usa gst-launch-1.0 para decodificar
        cmd = [
            f"{GST_BIN}/gst-launch-1.0",
            "-v",
            "filesrc", f"location={tmp_path}",
            "!", "wavparse",
            "!", "audioconvert",
            "!", "audioresample",
            "!", "audio/x-raw,format=S16LE,rate=44100,channels=1",
            "!", "wavenc",
            "!", "filesink", f"location={output_path}",
        ]
        
        result = subprocess.run(
            cmd, capture_output=True, env=ENV, timeout=30
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            if size > 100:  # arquivo válido
                return True
            else:
                return False
        else:
            stderr = result.stderr.decode("utf-8", errors="replace")
            if "error" in stderr.lower():
                print(f"  gst erro: {stderr[:200]}")
            return False
    finally:
        os.unlink(tmp_path)


def repack_fuz_with_wav(wav_path, lip_data, output_path):
    """Cria novo .fuz com WAV PCM em vez de XMA"""
    wav_data = open(wav_path, "rb").read()
    
    with open(output_path, "wb") as f:
        f.write(b"FUZC")
        f.write(struct.pack("<I", 0x00010000))  # version
        f.write(struct.pack("<I", len(wav_data)))  # xma_size (agora wav_size)
        f.write(struct.pack("<I", len(lip_data)))  # lip_size
        f.write(wav_data)  # audio data (PCM WAV em vez de XMA)
        f.write(lip_data)  # lip sync data preservado


def convert_fuz(input_path, output_path):
    """Converte um .fuz de XMA para PCM"""
    parsed = parse_fuz(input_path)
    if not parsed:
        return False, "não é .fuz válido"
    
    if not parsed["xma"]:
        return False, "sem dados XMA"
    
    # Decodifica XMA → PCM
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = tmp.name
    
    try:
        if not decode_xma_to_wav(parsed["xma"], tmp_wav):
            return False, "falha na decodificação XMA"
        
        # Repackea com PCM
        repack_fuz_with_wav(tmp_wav, parsed["lip"], output_path)
        
        orig_size = os.path.getsize(input_path)
        new_size = os.path.getsize(output_path)
        return True, f"OK ({orig_size} → {new_size} bytes)"
    finally:
        if os.path.exists(tmp_wav):
            os.unlink(tmp_wav)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: fuz_convert.py <input.fuz> <output.fuz>")
        print("     fuz_convert.py --batch <dir> <output_dir>")
        sys.exit(1)
    
    if sys.argv[1] == "--batch":
        input_dir = sys.argv[2]
        output_dir = sys.argv[3]
        os.makedirs(output_dir, exist_ok=True)
        
        converted = 0
        failed = 0
        for root, dirs, files in os.walk(input_dir):
            for fname in files:
                if fname.lower().endswith(".fuz"):
                    in_path = os.path.join(root, fname)
                    rel = os.path.relpath(in_path, input_dir)
                    out_path = os.path.join(output_dir, rel)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    
                    ok, msg = convert_fuz(in_path, out_path)
                    if ok:
                        converted += 1
                    else:
                        failed += 1
                    if (converted + failed) % 100 == 0:
                        print(f"  progresso: {converted} ok, {failed} falha")
        
        print(f"\n✓ {converted} convertidos, {failed} falhas")
    else:
        ok, msg = convert_fuz(sys.argv[1], sys.argv[2])
        print(f"{'✓' if ok else '✗'} {msg}")
