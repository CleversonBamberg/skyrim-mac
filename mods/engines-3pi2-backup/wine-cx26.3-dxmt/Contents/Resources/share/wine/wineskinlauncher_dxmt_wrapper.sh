#!/usr/bin/env bash
# DXMT auto-activation wrapper for wineskinlauncher.
# Place this script as Contents/MacOS/wineskinlauncher in a Wineskin wrapper
# and rename the original binary to wineskinlauncher.real.
# When the wrapper's Info.plist has DXMT=1, this script runs activate_dxmt.sh
# once per prefix before launching the real wineskinlauncher.
set -euo pipefail

MACOS_DIR="$(cd "$(dirname "$0")" && pwd)"
WRAPPER_DIR="$(cd "${MACOS_DIR}/../.." && pwd)"
INFO_PLIST="${WRAPPER_DIR}/Contents/Info.plist"
REAL_LAUNCHER="${MACOS_DIR}/wineskinlauncher.real"

if [[ ! -x "${REAL_LAUNCHER}" ]]; then
    echo "ERROR: real wineskinlauncher not found at ${REAL_LAUNCHER}" >&2
    exit 1
fi

DXMT_FLAG=0
if [[ -f "${INFO_PLIST}" ]]; then
    DXMT_FLAG=$(plutil -extract DXMT raw "${INFO_PLIST}" 2>/dev/null || echo "0")
fi

if [[ "${DXMT_FLAG}" == "1" ]]; then
    PREFIX_DIR="${WRAPPER_DIR}/Contents/SharedSupport/prefix"
    MARKER="${PREFIX_DIR}/.dxmt_activated"
    ENGINE_DIR="${WRAPPER_DIR}/Contents/SharedSupport/wine"
    ACTIVATE="${ENGINE_DIR}/share/wine/activate_dxmt.sh"

    # Set Vulkan/MoltenVK environment variables so Wine can find the Vulkan
    # loader and MoltenVK ICD. These are required for vkd3d-proton (D3D12)
    # and any Vulkan-based rendering path.
    FRAMEWORKS_DIR="${WRAPPER_DIR}/Contents/Frameworks"
    MVKCX_DIR="${FRAMEWORKS_DIR}/moltenvkcx"
    WINE_LIB_DIR="${ENGINE_DIR}/lib"

    # DYLD_FALLBACK_LIBRARY_PATH lets dlopen("libvulkan.1.dylib") succeed
    # and also lets MoltenVK find its dependencies.
    export DYLD_FALLBACK_LIBRARY_PATH="${FRAMEWORKS_DIR}:${MVKCX_DIR}:${WINE_LIB_DIR}:${DYLD_FALLBACK_LIBRARY_PATH:-}"

    # VK_ICD_FILENAMES tells the Vulkan loader which ICD to load.
    # Prefer the wrapper's moltenvkcx manifest; fall back to engine's.
    if [[ -f "${MVKCX_DIR}/MoltenVK_icd.json" ]]; then
        export VK_ICD_FILENAMES="${MVKCX_DIR}/MoltenVK_icd.json"
    elif [[ -f "${ENGINE_DIR}/share/vulkan/icd.d/MoltenVK_icd.json" ]]; then
        export VK_ICD_FILENAMES="${ENGINE_DIR}/share/vulkan/icd.d/MoltenVK_icd.json"
    fi

    if [[ -x "${ACTIVATE}" && ! -f "${MARKER}" ]]; then
        echo "[DXMT] Auto-activating DXMT for ${WRAPPER_DIR}"
        WINEPREFIX="${PREFIX_DIR}" "${ACTIVATE}"
        touch "${MARKER}"
    fi
fi

exec "${REAL_LAUNCHER}" "$@"
