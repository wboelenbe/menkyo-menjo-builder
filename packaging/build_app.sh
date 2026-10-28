#!/bin/bash
# Build dist/Menkyo.app and dist/Menkyo-<version>.dmg.
#
#   packaging/build_app.sh                       unsigned; fine for your own Mac
#   CODESIGN_IDENTITY="Developer ID Application: Name (TEAMID)" \
#   NOTARY_PROFILE=menkyo-notary \
#       packaging/build_app.sh                   signed + notarized, for others
#
# One-time notarization setup (stores credentials in the keychain):
#   xcrun notarytool store-credentials menkyo-notary \
#       --apple-id YOU@EXAMPLE.COM --team-id TEAMID --password APP-SPECIFIC-PASSWORD
#
# Needs a Python 3.11+ whose Tk is 8.6 (python.org installer, or
# `brew install python-tk@3.13`).  Set PYTHON to choose one.
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3.13}"
VERSION="${VERSION:-0.1.0}"
export VERSION
VENV=packaging/.venv

"$PYTHON" -c "import tkinter; assert tkinter.TkVersion >= 8.6, tkinter.TkVersion"

[ -d "$VENV" ] || "$PYTHON" -m venv "$VENV"
"$VENV/bin/pip" install -q -r requirements.txt pyinstaller

rm -rf build-app dist
"$VENV/bin/pyinstaller" --noconfirm --workpath build-app --distpath dist packaging/menkyo.spec

APP=dist/Menkyo.app
if [ -n "${CODESIGN_IDENTITY:-}" ]; then
    # PyInstaller signs what it collects; sign the bundle itself, deeply, last.
    codesign --force --deep --options runtime --timestamp \
        --entitlements packaging/entitlements.plist \
        --sign "$CODESIGN_IDENTITY" "$APP"
    codesign --verify --deep --strict "$APP"
fi

DMG="dist/Menkyo-$VERSION.dmg"
STAGE=$(mktemp -d)
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cat > "$STAGE/READ ME FIRST.txt" <<'TXT'
Drag Menkyo to Applications.

Menkyo needs two free programs to draw the certificates:
  Inkscape     https://inkscape.org/release/
  Ghostscript  only for the optional press-ready files (brew install ghostscript)
TXT
hdiutil create -quiet -volname "Menkyo" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
rm -rf "$STAGE"

if [ -n "${CODESIGN_IDENTITY:-}" ]; then
    codesign --force --timestamp --sign "$CODESIGN_IDENTITY" "$DMG"
    if [ -n "${NOTARY_PROFILE:-}" ]; then
        xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait
        xcrun stapler staple "$DMG"
    else
        echo "NOTARY_PROFILE not set: signed but NOT notarized; Gatekeeper will still object." >&2
    fi
else
    echo "Unsigned build: other Macs will refuse to open it without a right-click > Open." >&2
fi
echo "built $DMG"
