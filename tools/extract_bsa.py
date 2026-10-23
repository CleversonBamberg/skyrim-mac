#!/usr/bin/env python3
"""
extract_bsa.py — Extrai arquivos .xwm (música) de um BSA Skyrim SE (v105)
"""
import struct
import os
import sys

def extract_bsa(bsa_path, output_dir):
    f = open(bsa_path, "rb")
    data = f.read()
    f.close()

    # Header (36 bytes)
    assert data[0:4] == b"BSA\x00", "não é BSA"
    version = struct.unpack_from("<I", data, 4)[0]
    folder_off = struct.unpack_from("<I", data, 8)[0]
    folder_count = struct.unpack_from("<I", data, 12)[0]
    file_count = struct.unpack_from("<I", data, 16)[0]
    total_folder_names = struct.unpack_from("<I", data, 20)[0]
    total_file_names = struct.unpack_from("<I", data, 24)[0]
    file_flags = struct.unpack_from("<I", data, 28)[0]
    arch_flags = struct.unpack_from("<I", data, 32)[0]

    compress_flag = bool(arch_flags & 0x100)
    print(f"versão: {version} | pastas: {folder_count} | arquivos: {file_count} | comprimido: {compress_flag}")

    # Folder Records (24 bytes cada, começam em folder_off)
    folders = []
    pos = folder_off
    for i in range(folder_count):
        name_hash = struct.unpack_from("<Q", data, pos)[0]
        num_files = struct.unpack_from("<I", data, pos + 8)[0]
        unknown = struct.unpack_from("<I", data, pos + 12)[0]
        file_records_off = struct.unpack_from("<I", data, pos + 16)[0]
        unknown2 = struct.unpack_from("<I", data, pos + 20)[0]
        folders.append({
            "hash": name_hash,
            "num_files": num_files,
            "file_records_off": file_records_off,
        })
        pos += 24

    # Folder Names (após folder records) — null-terminated
    pos = folder_off + folder_count * 24
    folder_names = []
    for i in range(folder_count):
        end = data.index(b"\x00", pos)
        name = data[pos:end].decode("utf-8", errors="replace")
        folder_names.append(name)
        pos = end + 1

    # File Records + File Names (intercalados por pasta)
    files = []
    for i, folder in enumerate(folders):
        pos = folder["file_records_off"]
        for j in range(folder["num_files"]):
            name_hash = struct.unpack_from("<Q", data, pos)[0]
            file_size_raw = struct.unpack_from("<I", data, pos + 8)[0]
            file_data_off = struct.unpack_from("<I", data, pos + 12)[0]

            # tamanho real: bit 30 = comprimido neste arquivo
            is_compressed = bool(file_size_raw & (1 << 30))
            file_size = file_size_raw & 0x3FFFFFFF

            # o nome do arquivo vem logo após o record (16 bytes)
            name_end = data.index(b"\x00", pos + 16)
            name = data[pos + 16:name_end].decode("utf-8", errors="replace")

            files.append({
                "folder": folder_names[i],
                "name": name,
                "size": file_size,
                "offset": file_data_off,
                "compressed": is_compressed,
                "hash": name_hash,
            })
            pos = name_end + 1

    print(f"extraídos {len(files)} registros de arquivo")

    # Filtra .xwm e .fuz
    os.makedirs(output_dir, exist_ok=True)
    music_count = 0
    for f_rec in files:
        if f_rec["name"].lower().endswith(".xwm"):
            out_path = os.path.join(output_dir, f_rec["folder"], f_rec["name"])
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            fdata = data[f_rec["offset"]:f_rec["offset"] + f_rec["size"]]
            with open(out_path, "wb") as of:
                of.write(fdata)
            music_count += 1
            print(f"  ✓ {f_rec['folder']}/{f_rec['name']} ({f_rec['size']} bytes)")

    print(f"\n{music_count} arquivos .xwm extraídos para {output_dir}")
    return music_count


if __name__ == "__main__":
    bsa = sys.argv[1]
    out = sys.argv[2]
    extract_bsa(bsa, out)
