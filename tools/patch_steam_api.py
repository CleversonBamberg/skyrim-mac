#!/usr/bin/env python3
"""
Patch cirúrgico: steam_api64.dll → SteamAPI_RestartAppIfNecessary retorna FALSE.
Motivo: SkyrimSE chama RestartAppIfNecessary no boot; sem Steam, ele relança via
steam:// e sai (exit 53). Este patch isola a variável Steam nos testes.
Modo diagnóstico — o recipe final usa Steam real.
"""
import struct, shutil, sys

path = sys.argv[1]
shutil.copy(path, path + ".orig")

data = bytearray(open(path, "rb").read())

# DOS header → e_lfanew
e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
assert data[e_lfanew:e_lfanew+4] == b"PE\x00\x00", "não é PE"
coff = e_lfanew + 4
num_sections = struct.unpack_from("<H", data, coff + 2)[0]
opt_header_size = struct.unpack_from("<H", data, coff + 16)[0]
opt = coff + 20
magic = struct.unpack_from("<H", data, opt)[0]
assert magic == 0x20B, "esperado PE32+ (x86-64)"
# Data directory[0] = Export Table
export_rva, export_size = struct.unpack_from("<II", data, opt + 112)
assert export_rva != 0, "sem export table"

# Sections (para converter RVA→file offset)
sections = []
sec_off = opt + opt_header_size
for i in range(num_sections):
    s = sec_off + 40 * i
    virt_size, virt_addr, raw_size, raw_ptr = struct.unpack_from("<IIII", data, s + 8)
    sections.append((virt_addr, virt_size, raw_ptr, raw_size))

def rva_to_offset(rva):
    for va, vsz, ptr, rsz in sections:
        if va <= rva < va + max(vsz, rsz):
            return ptr + (rva - va)
    raise ValueError(f"RVA fora das seções: {rva:#x}")

exp_off = rva_to_offset(export_rva)
num_names = struct.unpack_from("<I", data, exp_off + 24)[0]
addr_funcs = struct.unpack_from("<I", data, exp_off + 28)[0]
addr_names = struct.unpack_from("<I", data, exp_off + 32)[0]
addr_ords  = struct.unpack_from("<I", data, exp_off + 36)[0]

target = b"SteamAPI_RestartAppIfNecessary"
func_rva = None
names_off = rva_to_offset(addr_names)
funcs_off = rva_to_offset(addr_funcs)
ords_off  = rva_to_offset(addr_ords)
for i in range(num_names):
    name_rva = struct.unpack_from("<I", data, names_off + 4 * i)[0]
    name_off = rva_to_offset(name_rva)
    end = data.index(b"\x00", name_off)
    if bytes(data[name_off:end]) == target:
        ordinal = struct.unpack_from("<H", data, ords_off + 2 * i)[0]
        func_rva = struct.unpack_from("<I", data, funcs_off + 4 * ordinal)[0]
        break

assert func_rva is not None, f"export {target.decode()} não encontrado"
patch_off = rva_to_offset(func_rva)

print(f"export encontrado: RVA {func_rva:#x} → offset de arquivo {patch_off:#x}")
print(f"bytes originais: {data[patch_off:patch_off+6].hex()}")
# xor eax, eax ; ret  →  retorna 0 (FALSE)
data[patch_off:patch_off+3] = bytes([0x31, 0xC0, 0xC3])
open(path, "wb").write(bytes(data))
print(f"patch aplicado: 31 C0 C3 (xor eax,eax; ret) → RestartAppIfNecessary = FALSE")
print(f"backup salvo: {path}.orig")
