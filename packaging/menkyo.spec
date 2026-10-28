# PyInstaller spec: builds dist/Menkyo.app from src/gui.py.
# Run via packaging/build_app.sh, not directly.
import os

from PyInstaller.utils.hooks import copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(ROOT, "src", "gui.py")],
    pathex=[os.path.join(ROOT, "src")],
    datas=[
        # Beside the package's modules, where paths.resource() looks.
        (os.path.join(ROOT, "src", "menkyo", "fonts"), "menkyo/fonts"),
        (os.path.join(ROOT, "src", "menkyo", "example.toml"), "menkyo"),
        (os.path.join(ROOT, "LICENSE"), "."),
        (os.path.join(ROOT, "NOTICE"), "."),
        # menkyo.__version__ reads the installed package's metadata.
        *copy_metadata("menkyo"),
    ],
    excludes=["matplotlib", "pandas", "IPython", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Menkyo",
          console=False, target_arch=os.environ.get("TARGET_ARCH") or None,
          codesign_identity=os.environ.get("CODESIGN_IDENTITY") or None,
          entitlements_file=os.path.join(SPECPATH, "entitlements.plist"))
coll = COLLECT(exe, a.binaries, a.datas, name="Menkyo")
app = BUNDLE(
    coll, name="Menkyo.app",
    bundle_identifier="be.wboelen.menkyo",
    info_plist={
        "CFBundleDisplayName": "Menkyo",
        "CFBundleShortVersionString": os.environ.get("VERSION", "0.1.0"),
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
