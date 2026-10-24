#!/usr/bin/env python3
"""
bsa_extract.py — Extrai arquivos de BSA Skyrim SE (version 105) sem ferramentas externas.

Layout BSA v105 (decifrado no projeto skyrim-mac, validado em Voices/Sounds BSAs):

    @0:        header 36B: magic "BSA\\0", version u32 (=105), offset u32 (=36),
               archiveFlags u32, folderCount u32, fileCount u32,
               totalFolderNameLen u32, totalFileNameLen u32, fileFlags u32
    @36:       folder records (folderCount × 24B):
               hash u64, count u32, unknown u32 (=0), offset u64
    @36+fc*24: POR PASTA, EM ORDEM DO FOLDER RECORD:
               [u8 len_total (INCLUINDO o null)][nome (len_total-1 bytes)\\0]
               count × file record (16B): hash u64, size u32, offset u32
    depois:    bloco de file names (fileCount nomes null-terminated, = totalFileNameLen)
    fim:       DATA contíguo, na ordem dos file records (offset direto, sem correção)

Aritmética de validação: 36 + fc*24 + Σ(1+len) + 16*fileCount + totalFileNameLen
deve terminar exatamente onde começa o DATA.

Uso:
    python3 bsa_extract.py <arquivo.bsa> <pasta_saida> [--ext .xwm] [--filter substr] [--list]
"""
import struct
import mmap
import os
import sys
import bisect


def parse_bsa(path):
    """Retorna (file_entries, data_start) — entries: (path_completo, size, offset)."""
    f = open(path, "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    if mm[:4] != b"BSA\x00":
        raise ValueError("não é um BSA (magic errado)")
    version = struct.unpack_from("<I", mm, 4)[0]
    if version != 105:
        raise ValueError(f"versão {version} não suportada (apenas 105 = Skyrim SE)")
    _, _, aflags, fc, filec, tfnl, tfnl2, _ = struct.unpack_from("<IIIIIIII", mm, 4)

    frs = [struct.unpack_from("<QIIQ", mm, 36 + i * 24) for i in range(fc)]
    counts = [r[1] for r in frs]

    # blocos intercalados: [len][nome\0][records]
    pos = 36 + fc * 24
    file_records = []
    folder_names = []
    for i in range(fc):
        ln = mm[pos]  # inclui o \0
        folder_names.append(mm[pos + 1:pos + ln].decode("ascii"))
        pos += 1 + ln
        for _ in range(counts[i]):
            file_records.append(struct.unpack_from("<QII", mm, pos))
            pos += 16
    if pos + tfnl2 > len(mm):
        raise ValueError("arquivo truncado?")

    names = []
    for _ in range(filec):
        e = mm.find(b"\x00", pos)
        names.append(mm[pos:e].decode("ascii"))
        pos = e + 1
    data_start = pos

    # caminhos completos
    cum = [0]
    for c in counts:
        cum.append(cum[-1] + c)
    entries = []
    for j, nm in enumerate(names):
        fi = bisect.bisect_right(cum, j) - 1
        path = folder_names[fi].replace("\\", "/") + "/" + nm
        _, size, off = file_records[j]
        entries.append((path, size & 0x3FFFFFFF, off))
    return f, mm, entries, data_start


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    bsa, out = args[0], args[1]
    ext = None
    filt = None
    do_list = "--list" in args
    if "--ext" in args:
        ext = args[args.index("--ext") + 1].lower()
    if "--filter" in args:
        filt = args[args.index("--filter") + 1].lower()
    skip_dir = None
    if "--skip-existing" in args:
        skip_dir = args[args.index("--skip-existing") + 1]

    f, mm, entries, data_start = parse_bsa(bsa)
    sel = []
    skipped = 0
    for e in entries:
        if ext is not None and not e[0].lower().endswith(ext):
            continue
        if filt is not None and filt not in e[0].lower():
            continue
        if skip_dir and os.path.exists(os.path.join(skip_dir, e[0])):
            skipped += 1
            continue
        sel.append(e)
    print(f"{os.path.basename(bsa)}: {len(entries)} arquivos | selecionados: {len(sel)}"
          f"{' | pulados (já existem): ' + str(skipped) if skipped else ''} | data @{data_start}")
    if do_list:
        for p, s, o in sel[:50]:
            print(f"  {p} ({s}B)")
        return
    os.makedirs(out, exist_ok=True)
    n = 0
    for p, s, o in sel:
        dst = os.path.join(out, p)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fh:
            fh.write(mm[o:o + s])
        n += 1
    print(f"✓ extraídos {n} arquivos em {out}")


if __name__ == "__main__":
    main()
