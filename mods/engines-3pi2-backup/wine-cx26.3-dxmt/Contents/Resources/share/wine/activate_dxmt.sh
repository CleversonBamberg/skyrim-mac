#!/usr/bin/env bash
# Activate DXMT in the current Wine prefix.
# Run this from inside a Wineskin wrapper after the game is installed.
#
# This script:
#   1. Copies MoltenVK + Vulkan loader to the wrapper's Frameworks
#   2. Creates the MoltenVK ICD manifest
#   3. Imports DXMT/VKD3D registry overrides (d3d12=native,builtin)
#   4. Copies d3d12.dll to prefix system32 and patches it to return E_FAIL
#      (so Unity 6 / D3D12-aware engines fall back to D3D11/DXMT)
set -euo pipefail

# Locate the engine bundle relative to this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "${SCRIPT_DIR}/../../wswine.bundle" ]]; then
    ENGINE_DIR="${SCRIPT_DIR}/../../wswine.bundle"
elif [[ -d "${SCRIPT_DIR}/../.." ]]; then
    ENGINE_DIR="${SCRIPT_DIR}/../.."
else
    echo "ERROR: cannot locate engine bundle from ${SCRIPT_DIR}"
    exit 1
fi

# WINEPREFIX is usually set by the wrapper; if not, try the default location.
if [[ -z "${WINEPREFIX:-}" ]]; then
    if [[ -d "${ENGINE_DIR}/../../prefix" ]]; then
        export WINEPREFIX="${ENGINE_DIR}/../../prefix"
    else
        echo "ERROR: WINEPREFIX is not set and no default prefix found"
        exit 1
    fi
fi

echo "Activating DXMT in prefix: ${WINEPREFIX}"

# Use the bundled wine binary.
WINE="${ENGINE_DIR}/bin/wine"
[[ -x "${WINE}" ]] || WINE="${ENGINE_DIR}/bin/wine64"
[[ -x "${WINE}" ]] || { echo "ERROR: wine binary not found in ${ENGINE_DIR}/bin"; exit 1; }

# Copy Vulkan loader and MoltenVK to the wrapper's Frameworks/moltenvkcx
# so they can be found via DYLD_FALLBACK_LIBRARY_PATH.
WRAPPER_DIR="$(cd "${ENGINE_DIR}/../../.." && pwd)"
MVKCX_DIR="${WRAPPER_DIR}/Contents/Frameworks/moltenvkcx"
mkdir -p "${MVKCX_DIR}"
if [[ -f "${ENGINE_DIR}/lib/libMoltenVK.dylib" ]]; then
    cp -f "${ENGINE_DIR}/lib/libMoltenVK.dylib" "${MVKCX_DIR}/libMoltenVK.dylib"
    echo "Copied libMoltenVK.dylib to moltenvkcx"
fi
# Also copy to Frameworks for libvulkan
if [[ -f "${ENGINE_DIR}/lib/libvulkan.1.dylib" ]]; then
    cp -f "${ENGINE_DIR}/lib/libvulkan.1.dylib" "${WRAPPER_DIR}/Contents/Frameworks/libvulkan.1.dylib"
    echo "Copied libvulkan.1.dylib to Frameworks"
fi

# Create ICD manifest with absolute path (Vulkan loader resolves @rpath
# relative to the manifest directory, so we must use absolute paths).
if [[ -f "${MVKCX_DIR}/libMoltenVK.dylib" ]]; then
    cat > "${MVKCX_DIR}/MoltenVK_icd.json" <<ICDEOF
{"file_format_version":"1.0.0","ICD":{"library_path":"${MVKCX_DIR}/libMoltenVK.dylib","api_version":"1.4.0","is_portability_driver":true}}
ICDEOF
    echo "Created MoltenVK ICD manifest at ${MVKCX_DIR}/MoltenVK_icd.json"
fi

# DXMT DLLs (d3d9.dll, d3d11.dll, dxgi.dll) are winebuiltin and loaded from
# lib/wine/ automatically. No need to copy to system32 or set DllOverrides.
#
# VKD3D-Proton d3d12.dll is also winebuiltin, but Unity 6 and some other
# engines try to LoadLibrary("d3d12.dll") even when D3D11 is the active
# backend. If d3d12.dll is not in the prefix's system32, the load fails
# with STATUS_DLL_NOT_FOUND and the game crashes.
#
# If we copy the VKD3D-Proton d3d12.dll as-is, it tries to init Vulkan and
# crashes with an LLVM PassManager assertion if Vulkan/MoltenVK is not
# available. To avoid this, we copy the DLL and binary-patch all exported
# functions to return E_FAIL, so D3D12CreateDevice() fails gracefully and
# the game falls back to D3D11 (DXMT/D3DMetal).

SYSTEM32="${WINEPREFIX}/drive_c/windows/system32"
SYSWOW64="${WINEPREFIX}/drive_c/windows/syswow64"
D3D12_SRC="${ENGINE_DIR}/lib/wine/x86_64-windows/d3d12.dll"
D3D12_DST="${SYSTEM32}/d3d12.dll"
PATCH_SCRIPT="${SCRIPT_DIR}/patch_d3d12.py"

if [[ -f "${D3D12_SRC}" ]]; then
    echo "Installing patched d3d12.dll to prefix..."
    cp -f "${D3D12_SRC}" "${D3D12_DST}"

    if [[ -f "${PATCH_SCRIPT}" ]]; then
        python3 "${PATCH_SCRIPT}" "${D3D12_DST}" || {
            echo "WARNING: patch_d3d12.py failed, d3d12.dll is unpatched"
            echo "         Games that probe d3d12.dll may crash if Vulkan is unavailable"
        }
    else
        echo "WARNING: patch_d3d12.py not found at ${PATCH_SCRIPT}"
        echo "         d3d12.dll copied but not patched"
    fi

    # Re-sign the patched DLL (required on macOS with Rosetta 2)
    codesign --remove-signature "${D3D12_DST}" 2>/dev/null || true
    codesign --force --sign - "${D3D12_DST}" 2>/dev/null || true
    echo "Patched and signed d3d12.dll"

    # Also handle 32-bit d3d12.dll if the engine has one
    D3D12_SRC_32="${ENGINE_DIR}/lib/wine/i386-windows/d3d12.dll"
    D3D12_DST_32="${SYSWOW64}/d3d12.dll"
    if [[ -f "${D3D12_SRC_32}" ]]; then
        cp -f "${D3D12_SRC_32}" "${D3D12_DST_32}"
        if [[ -f "${PATCH_SCRIPT}" ]]; then
            python3 "${PATCH_SCRIPT}" "${D3D12_DST_32}" 2>/dev/null || true
        fi
        codesign --remove-signature "${D3D12_DST_32}" 2>/dev/null || true
        codesign --force --sign - "${D3D12_DST_32}" 2>/dev/null || true
        echo "Patched and signed 32-bit d3d12.dll"
    fi
else
    echo "NOTE: d3d12.dll not found in engine (VKD3D not bundled)"
fi

# Import VKD3D registry overrides (d3d12 needs native,builtin).
REG_FILE="${ENGINE_DIR}/share/wine/dxmt-vkd3d.reg"
if [[ -f "${REG_FILE}" ]]; then
    echo "Importing ${REG_FILE}"
    "${WINE}" regedit /S "${REG_FILE}" 2>/dev/null || {
        echo "WARNING: regedit failed, trying with Z: path"
        "${WINE}" regedit /S "Z:${ENGINE_DIR}/share/wine/dxmt-vkd3d.reg"
    }
fi

# ── Unity mouse pointer fix ─────────────────────────────────────────────────
# Unity's New Input System calls NtUserEnableMouseInPointer(TRUE) and expects
# WM_POINTER* messages for mouse input. Without this fix, mouse clicks are
# ignored in Unity games (e.g. Citadelum).
#
# The fix is entirely in win32u.so (the unix library), which is already
# compiled into the engine bundle with the pointer message conversion code
# from Wine 11.12 backported to Wine 11.0. The win32u.dll syscall stubs call
# through to win32u.so, which:
#   1. NtUserEnableMouseInPointer: sets _enable_mouse_in_pointer = 1
#   2. process_mouse_message: converts WM_LBUTTONDOWN -> WM_POINTERDOWN etc.
#
# Do NOT binary-patch win32u.dll to bypass the syscalls — this prevents
# _enable_mouse_in_pointer from being set, which disables the conversion.

echo "DXMT activation complete."
