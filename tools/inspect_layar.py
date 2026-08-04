"""Cetak semua elemen yang sedang tampil di layar FASIH.

Dipakai untuk memetakan tiap layar sebelum menulis langkah bot.
Jalankan: .venv\\Scripts\\python.exe tools\\inspect_layar.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.cli import ambil_perangkat
from bot.perangkat import hubungkan


def main() -> int:
    d = hubungkan(ambil_perangkat())
    info = d.info
    print(f"Layar   : {info['displayWidth']}x{info['displayHeight']} (SDK {info['sdkInt']})")
    print(f"App aktif: {d.app_current()}")
    print("-" * 70)
    print(f"{'TEXT':<38} {'RESOURCE-ID':<32} CLASS")
    print("-" * 70)
    for el in d.xpath("//*").all():
        a = el.attrib
        text = (a.get("text") or "").strip()
        rid = (a.get("resource-id") or "").replace("id.go.bpsfasih:id/", "")
        desc = (a.get("content-desc") or "").strip()
        if not (text or rid or desc):
            continue
        label = text or f"[desc] {desc}"
        cls = (a.get("class") or "").rsplit(".", 1)[-1]
        clickable = " *" if a.get("clickable") == "true" else ""
        print(f"{label[:38]:<38} {rid[:32]:<32} {cls}{clickable}")
    print("-" * 70)
    print("* = clickable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
