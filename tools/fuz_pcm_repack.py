#!/usr/bin/env python3
"""
fuz_pcm_repack.py — Repackea .fuz files substituindo XMA por PCM WAV
Mantém LIP sync. Gera PCM silencioso do mesmo tamanho.
"""
import struct
import os
import sys


def create_silent_wav(pcm_size, sample_rate=22050, channels=1):
    """Cria WAV PCM silencioso DIRETO em memória (sem tempfile)"""
    bytes_per_sample = channels * 2
    num_samples = max(pcm_size // bytes_per_sample, 1)
    data_size = num_samples * bytes_per_sample
    
    # Monta o WAV em bytes
    wav = b"RIFF"
    wav += struct.pack("<I", 36 + data_size)
    wav += b"WAVE"
    wav += b"fmt "
    wav += struct.pack("<I", 16)
    wav += struct.pack("<H", 1)  # PCM
    wav += struct.pack("<H", channels)
    wav += struct.pack("<I", sample_rate)
    wav += struct.pack("<I", sample_rate * bytes_per_sample)
    wav += struct.pack("<H", bytes_per_sample)
    wav += struct.pack("<H", 16)
    wav += b"data"
    wav += struct.pack("<I", data_size)
    wav += b"\x00" * data_size
    return wav


def parse_fuz(path):
    data = open(path, "rb").read()
    if data[:4] not in (b"FUZC", b"FUZE"):
        return None
    version = struct.unpack_from("<I", data, 4)[0]
    audio_size = struct.unpack_from("<I", data, 8)[0]
    lip_size = struct.unpack_from("<I", data, 12)[0]
    audio_data = data[16:16+audio_size]
    lip_data = data[16+audio_size:16+audio_size+lip_size]
    return {
        "version": version,
        "audio": audio_data,
        "lip": lip_data,
        "audio_size": audio_size,
        "lip_size": lip_size,
    }


def repack_with_pcm(parsed):
    """Cria novo .fuz com PCM WAV em vez de XMA"""
    if parsed["audio"][:4] == b"RIFF":
        # Já é WAV — mantém
        wav = parsed["audio"]
    else:
        # XMA cru — primeiro 4 bytes = tamanho PCM decodificado
        if len(parsed["audio"]) >= 4:
            pcm_size = struct.unpack_from("<I", parsed["audio"], 0)[0]
        else:
            pcm_size = parsed["audio_size"] * 3
        # Limita o tamanho (evita memory error)
        pcm_size = min(pcm_size, 2_000_000)
        wav = create_silent_wav(pcm_size)
    
    lip = parsed["lip"]
    
    result = b"FUZE"
    result += struct.pack("<I", parsed["version"])
    result += struct.pack("<I", len(wav))
    result += struct.pack("<I", len(lip))
    result += wav
    result += lip
    return result


def convert_batch(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    converted = 0
    failed = 0
    
    for root, dirs, files in os.walk(input_dir):
        for fname in files:
            if not fname.lower().endswith(".fuz"):
                continue
            
            in_path = os.path.join(root, fname)
            rel = os.path.relpath(in_path, input_dir)
            out_path = os.path.join(output_dir, rel)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            
            parsed = parse_fuz(in_path)
            if parsed is None:
                failed += 1
                continue
            
            try:
                new_data = repack_with_pcm(parsed)
                with open(out_path, "wb") as f:
                    f.write(new_data)
                converted += 1
            except Exception as e:
                failed += 1
            
            if (converted + failed) % 5000 == 0:
                print(f"  progresso: {converted} ok, {failed} falha")
    
    print(f"\n✓ {converted} convertidos, {failed} falhas")
    return converted


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: fuz_pcm_repack.py <input_dir> <output_dir>")
        sys.exit(1)
    convert_batch(sys.argv[1], sys.argv[2])
