#!/usr/bin/env bash
# Enable DXMT auto-activation for a Wineskin wrapper.
# Usage: ./enable_dxmt_auto.sh /path/to/Wrapper.app
#
# This script sets DXMT=1 in the wrapper's Info.plist.
# The actual DXMT activation (copying d3d12.dll, patching, registry) is
# handled by wine-wrapper.sh on first game launch, so this script only
# needs to set the flag.
set -euo pipefail

WRAPPER="${1:-}"

if [[ -z "${WRAPPER}" || ! -d "${WRAPPER}/Contents/MacOS" ]]; then
    echo "Usage: $0 /path/to/Wrapper.app" >&2
    exit 1
fi

INFO_PLIST="${WRAPPER}/Contents/Info.plist"
if [[ ! -f "${INFO_PLIST}" ]]; then
    echo "ERROR: Info.plist not found at ${INFO_PLIST}" >&2
    exit 1
fi

DXMT_FLAG=$(plutil -extract DXMT raw "${INFO_PLIST}" 2>/dev/null || echo "0")
if [[ "${DXMT_FLAG}" != "1" ]]; then
    echo "Setting DXMT=1 in ${INFO_PLIST}"
    plutil -replace DXMT -integer 1 "${INFO_PLIST}" 2>/dev/null || \
        plutil -insert DXMT -integer 1 "${INFO_PLIST}"
else
    echo "DXMT=1 already set in ${INFO_PLIST}"
fi

echo "DXMT auto-activation enabled for ${WRAPPER}"
echo "The wine-wrapper.sh will activate DXMT on first game launch."
echo "To disable: plutil -replace DXMT -integer 0 ${INFO_PLIST}"
