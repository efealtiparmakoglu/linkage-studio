"""Add-on paketini hazırlar: math kök dosyasını pakete kopyalar + zip üretir.

    python3 scripts/make_addon.py
"""

import os
import shutil
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(REPO, "linkage_studio")
ZIP = os.path.join(REPO, "linkage_studio.zip")

# tek kaynak: kökteki linkage.py pakete kopyalanır (drift yok)
shutil.copy2(os.path.join(REPO, "linkage.py"), os.path.join(PKG, "linkage.py"))

if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for fn in ("__init__.py", "builder.py", "linkage.py"):
        z.write(os.path.join(PKG, fn), f"linkage_studio/{fn}")

print(f"OK: {ZIP} ({os.path.getsize(ZIP):,} bayt)")
