"""Baca keadaan pilihan (radio/checkbox) pada kuesioner FormGear.

Teks saja tidak cukup untuk tahu opsi mana yang aktif, jadi di sini
atribut checked/selected/content-desc ditampilkan apa adanya.

Jalankan: .venv\\Scripts\\python.exe tools\\inspect_pilihan.py [kata_kunci]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import layar
from bot.cli import ambil_perangkat
from bot.perangkat import hubungkan

MENARIK = ("checkable", "checked", "selected", "clickable", "focusable", "focused")


def main() -> int:
    kunci = sys.argv[1] if len(sys.argv) > 1 else "Ditemukan"
    d = hubungkan(ambil_perangkat())
    root = layar.pohon(d)
    print(f"Activity: {d.app_current()['activity']}")
    print(f"Kata kunci: {kunci!r}\n")

    ketemu = 0
    for node in root.iter("node"):
        teks = (node.get("text") or "").strip()
        desc = (node.get("content-desc") or "").strip()
        rid = node.get("resource-id", "")
        if kunci.lower() not in f"{teks} {desc} {rid}".lower():
            continue
        ketemu += 1
        atr = " ".join(
            f"{k}={node.get(k)}" for k in MENARIK if node.get(k) == "true"
        )
        print(f"teks={teks!r}")
        print(f"  resource-id : {rid or '-'}")
        print(f"  content-desc: {desc or '-'}")
        print(f"  class       : {node.get('class')}")
        print(f"  bounds      : {node.get('bounds')}")
        print(f"  atribut aktif: {atr or '(tidak ada)'}")
        print()

    if not ketemu:
        print("Tidak ada node yang cocok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
