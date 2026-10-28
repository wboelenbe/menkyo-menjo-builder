#!/bin/bash
# P-2 phase 1 on macOS arm64: a fresh venv per candidate, import, otool -L on every native object.
# Allowed: /usr/lib/libSystem*, /usr/lib/libc++*, /System/Library/Frameworks/*, @loader_path/@rpath.
# usage: otool.sh VENVDIR   (fresh venvs are created under it)
V="${1:?VENVDIR}"; mkdir -p "$V"
while read -r k pkgs mod; do
  rm -rf $V/$k; uv venv -q -p 3.13 $V/$k && uv pip install -q --python $V/$k/bin/python --only-binary :all: ${pkgs//,/ } || { echo "[$k] install FAILED"; continue; }
  imp=$($V/$k/bin/python -c "import $mod" 2>&1 >/dev/null | tail -1); [ -z "$imp" ] && imp="import OK"
  sp=$($V/$k/bin/python -c 'import sysconfig;print(sysconfig.get_paths()["purelib"])')
  other=$(find $sp \( -name '*.so' -o -name '*.dylib' \) | while read -r f; do self=$(otool -D "$f" | sed -n 2p); otool -L "$f" | sed 1d | grep -v ':$' | awk '{print $1}' | grep -vxF "${self:-@@none}"; done | grep -vE '^(/usr/lib/libSystem|/usr/lib/libc\+\+|/System/Library/Frameworks/|@loader_path|@rpath)' | sort -u)
  echo "[$k] $imp; non-allowed: $(echo "$other" | grep -c .)"; [ -n "$other" ] && echo "$other" | sed 's/^/   /' | head -10
done <<'L'
pypdfium2 pypdfium2==5.14.0 pypdfium2
fonttools fonttools==4.68.0 fontTools.ttLib
resvg resvg-py==0.5.0 resvg_py
base pillow==13.0.0,numpy==2.5.4,scipy==1.18.1 PIL.Image
skia skia-python==144.1 skia
pikepdf pikepdf pikepdf
L
