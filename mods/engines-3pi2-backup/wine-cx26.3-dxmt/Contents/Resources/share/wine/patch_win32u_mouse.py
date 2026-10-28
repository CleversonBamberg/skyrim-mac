#!/usr/bin/env python3
"""Patch win32u.dll to make NtUserEnableMouseInPointer return TRUE.

Unity's New Input System calls NtUserEnableMouseInPointer(TRUE) and expects
WM_POINTER* messages for mouse input. Wine's win32u.dll has these as syscall
stubs that return FALSE, so Unity ignores all mouse button messages.

This patch makes three functions return TRUE (1):
  - NtUserEnableMouseInPointer
  - NtUserEnableMouseInPointerForThread
  - NtUserIsMouseInPointerEnabled

Usage: python3 patch_win32u_mouse.py <win32u.dll path>
"""
import struct
import sys
import os

# mov eax, 1; ret = B8 01 00 00 00 C3
PATCH_BYTES = b'\xB8\x01\x00\x00\x00\xC3'

TARGETS = [
    "NtUserEnableMouseInPointer",
    "NtUserEnableMouseInPointerForThread",
    "NtUserIsMouseInPointerEnabled",
]


def get_export_offsets(data):
    """Return {name: file_offset} for all named exports in a PE file."""
    if data[:2] != b'MZ':
        raise ValueError("Not an MZ file")

    pe_off = struct.unpack_from('<I', data, 0x3c)[0]
    if data[pe_off:pe_off+4] != b'PE\x00\x00':
        raise ValueError("Not a valid PE file")

    machine = struct.unpack_from('<H', data, pe_off + 4)[0]
    if machine not in (0x8664, 0x14c):
        raise ValueError(f"Not an x86/x64 PE file (machine={hex(machine)})")

    opt_hdr = pe_off + 24
    magic = struct.unpack_from('<H', data, opt_hdr)[0]
    if magic not in (0x20b, 0x10b):
        raise ValueError(f"Not a PE32/PE32+ file (magic={hex(magic)})")

    data_dir_offset = 112 if magic == 0x20b else 96
    export_rva = struct.unpack_from('<I', data, opt_hdr + data_dir_offset)[0]
    if export_rva == 0:
        raise ValueError("No export directory")

    num_sections = struct.unpack_from('<H', data, pe_off + 6)[0]
    opt_hdr_size = struct.unpack_from('<H', data, pe_off + 20)[0]
    section_table = pe_off + 24 + opt_hdr_size

    def rva_to_offset(rva):
        for i in range(num_sections):
            off = section_table + i * 40
            vaddr = struct.unpack_from('<I', data, off + 12)[0]
            vsize = struct.unpack_from('<I', data, off + 8)[0]
            raw_off = struct.unpack_from('<I', data, off + 20)[0]
            if vaddr <= rva < vaddr + vsize:
                return raw_off + (rva - vaddr)
        return None

    export_off = rva_to_offset(export_rva)
    if export_off is None:
        raise ValueError("Could not resolve export directory RVA")

    num_names = struct.unpack_from('<I', data, export_off + 24)[0]
    addr_table_rva = struct.unpack_from('<I', data, export_off + 28)[0]
    name_ptr_rva = struct.unpack_from('<I', data, export_off + 32)[0]
    ordinal_rva = struct.unpack_from('<I', data, export_off + 36)[0]

    addr_off = rva_to_offset(addr_table_rva)
    name_ptr_off = rva_to_offset(name_ptr_rva)
    ordinal_off = rva_to_offset(ordinal_rva)

    exports = {}
    for i in range(num_names):
        name_rva = struct.unpack_from('<I', data, name_ptr_off + i * 4)[0]
        noff = rva_to_offset(name_rva)
        name = b''
        j = noff
        while data[j] != 0:
            name += bytes([data[j]])
            j += 1
        ordinal = struct.unpack_from('<H', data, ordinal_off + i * 2)[0]
        func_rva = struct.unpack_from('<I', data, addr_off + ordinal * 4)[0]
        func_off = rva_to_offset(func_rva)
        if func_off is not None:
            exports[name.decode()] = func_off

    return exports


def patch_win32u(path):
    """Patch NtUserEnableMouseInPointer etc. to return TRUE."""
    with open(path, 'rb') as f:
        data = bytearray(f.read())

    exports = get_export_offsets(data)

    patched = 0
    skipped = 0
    for name in TARGETS:
        if name not in exports:
            print(f"  WARNING: {name} not found in exports")
            continue
        offset = exports[name]
        current = bytes(data[offset:offset + len(PATCH_BYTES)])
        if current == PATCH_BYTES:
            print(f"  {name}: already patched (skip)")
            skipped += 1
        else:
            data[offset:offset + len(PATCH_BYTES)] = PATCH_BYTES
            print(f"  {name}: patched at {hex(offset)}")
            patched += 1

    if patched > 0:
        with open(path, 'wb') as f:
            f.write(data)
        print(f"Patched {patched} functions ({skipped} already patched)")
    else:
        print(f"All {skipped} functions already patched")

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: patch_win32u_mouse.py <win32u.dll path>")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"ERROR: {path} not found")
        sys.exit(1)

    print(f"Patching {path}...")
    try:
        patch_win32u(path)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
