#!/usr/bin/env python3
"""
patch_skyrimse_exe.py — Aplica os 4 patches de áudio no SkyrimSE.exe (Skyrim SE 1.6.x)

Root cause: no Wine, o decoder WMA (MFT/wmadmod) é um stub e retorna pointer
inválido. O jogo chama 4 funções de áudio que crasham em `MOV RAX,[RCX]`.
Os patches pulam essas 4 chamadas (JE → JMP): o jogo fica sem o path de
decode WMA (que resolvermos off-line convertendo xWMA→PCM nos .fuz).

Layout do patch (file offsets, SkyrimSE.exe 1.6.1170):
    0x100e5b8, 0x100e5c6, 0x100e5f3, 0x100f290   (0x74 JE → 0xEB JMP)

Uso:
    python3 patch_skyrimse_exe.py "<caminho>/SkyrimSE.exe"

Idempotente: se já aplicado, apenas reporta. Faz backup .pre-audio-patch.
"""
import os
import shutil
import sys

PATCHES = [
    (0x100e5b8, "audio_init_call_1"),
    (0x100e5c6, "audio_init_call_2"),
    (0x100e5f3, "audio_init_call_3"),
    (0x100f290, "audio_init_call_4"),
]


def main(path):
    if not os.path.exists(path):
        print(f"ERRO: não achei {path}")
        sys.exit(1)
    with open(path, "rb") as f:
        data = bytearray(f.read())

    changed = 0
    already = 0
    for off, name in PATCHES:
        if off >= len(data):
            print(f"ERRO: offset {off:#x} fora do arquivo — versão do exe não suportada")
            sys.exit(1)
        b = data[off]
        if b == 0xEB:
            print(f"  ✓ {name} @{off:#x}: já aplicado")
            already += 1
        elif b == 0x74:
            data[off] = 0xEB
            print(f"  ✓ {name} @{off:#x}: JE → JMP aplicado")
            changed += 1
        else:
            print(f"ERRO: byte {b:#x} em {off:#x} (esperado 0x74/0xEB) — "
                  f"versão do SkyrimSE.exe não suportada por este patch")
            sys.exit(1)

    if changed:
        bak = path + ".pre-audio-patch"
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
            print(f"  backup salvo: {bak}")
        with open(path, "wb") as f:
            f.write(bytes(data))
        print(f"\n✓ {changed} patches aplicados ({already} já estavam)")
    else:
        print(f"\n✓ Nada a fazer — todos os {already} patches já estavam aplicados")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
