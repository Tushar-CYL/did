"""Package webapp/out into a deployable zip (forward-slash paths).

Azure / Netlify / any static host need the site files at the ZIP ROOT and with
forward-slash separators. Windows' Compress-Archive writes backslashes, which
makes hosts serve a blank page - this script avoids that.

    python tools/make_site_zip.py            -> AccountSignal_site_deploy.zip
    python tools/make_site_zip.py out.zip    -> custom name
"""
from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "webapp" / "out"


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "AccountSignal_site_deploy.zip"
    if not SRC.exists():
        print(f"ERROR: {SRC} not found. Build it first:  cd webapp && npm run build")
        return 1
    if out.exists():
        out.unlink()

    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(SRC):
            for f in files:
                full = Path(root) / f
                arc = str(full.relative_to(SRC)).replace(os.sep, "/")  # force "/"
                z.write(full, arc)
                count += 1

    names = zipfile.ZipFile(out).namelist()
    ok_root = "index.html" in names
    ok_sep = all("\\" not in n for n in names)
    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"wrote {out}  ({count} files, {size_mb:.1f} MB)")
    print(f"  index.html at root : {ok_root}")
    print(f"  forward slashes    : {ok_sep}")
    if not (ok_root and ok_sep):
        print("  WARNING: zip layout looks wrong for a static host")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
