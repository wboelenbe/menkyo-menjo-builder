"""P-2 phase 1, run inside python:3.13-slim-bookworm with only pip on top.

Imports a module, then runs ldd on every native extension and bundled shared
library under site-packages and classifies each resolved library:
glibc/libstdc++/libgcc_s/ld-linux, a file inside site-packages, or OTHER.
Usage: python ldd_check.py <import-name>
"""
import importlib, os, re, subprocess, sys, sysconfig
mod = sys.argv[1]
try:
    importlib.import_module(mod)
    imp = "import OK"
except Exception as e:
    imp = f"import FAILED: {type(e).__name__}: {e}"
site = sysconfig.get_paths()["purelib"]
ALLOWED = re.compile(r"^(libc|libm|libpthread|libdl|librt|libstdc\+\+|libgcc_s|ld-linux[^ ]*|linux-vdso)\.")
bad, notfound, n = set(), set(), 0
for root, _, files in os.walk(site):
    for f in files:
        if not re.search(r"\.so(\.|$)", f):
            continue
        p = os.path.join(root, f)
        n += 1
        out = subprocess.run(["ldd", p], capture_output=True, text=True).stdout
        for line in out.splitlines():
            line = line.strip()
            if "not found" in line:
                notfound.add(f"{os.path.relpath(p, site)}: {line}")
                continue
            m = re.match(r"(\S+)(?: => (\S+))?", line)
            if not m: continue
            name, target = m.group(1), m.group(2) or m.group(1)
            if ALLOWED.match(os.path.basename(name)) or target.startswith(site) or name.startswith("/lib") and ALLOWED.match(os.path.basename(name)):
                continue
            if "statically linked" in line: continue
            bad.add(f"{name} => {target}")
print(f"[{mod}] {imp}; {n} shared objects; not found: {len(notfound)}; other libs: {len(bad)}")
for x in sorted(notfound)[:15]: print("   NOT FOUND", x)
for x in sorted(bad)[:15]: print("   OTHER", x)
