"""Petakan struktur tabel DataTables di dalam WebView FASIH.

Menampilkan tiap baris beserta koordinat sel-selnya, supaya kelihatan
elemen mana yang node tersendiri dan mana yang menyatu dalam satu sel.

Jalankan: .venv\\Scripts\\python.exe tools\\inspect_tabel.py
"""

import re
import sys
import xml.etree.ElementTree as ET

import uiautomator2 as u2

SERIAL = "127.0.0.1:5615"
BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def bounds(node):
    m = BOUNDS_RE.match(node.get("bounds", ""))
    return tuple(int(g) for g in m.groups()) if m else (0, 0, 0, 0)


def main() -> int:
    d = u2.connect(SERIAL)
    print(f"App aktif: {d.app_current()['activity']}")
    root = ET.fromstring(d.dump_hierarchy())

    # Baris tabel = node yang punya >=2 anak bertekstext dan tinggi seragam.
    rows = []
    for node in root.iter("node"):
        kids = list(node)
        if len(kids) < 2:
            continue
        if not all(k.get("text") for k in kids):
            continue
        rows.append((node, kids))

    if not rows:
        print("Tidak ada baris tabel terdeteksi di layar ini.")
        return 0

    print(f"\nTerdeteksi {len(rows)} baris.\n")
    print("Struktur 3 baris pertama (x1,y1)-(x2,y2):")
    print("=" * 78)
    for node, kids in rows[:3]:
        x1, y1, x2, y2 = bounds(node)
        print(f"BARIS  ({x1},{y1})-({x2},{y2})  tinggi={y2 - y1}")
        for i, k in enumerate(kids):
            kx1, ky1, kx2, ky2 = bounds(k)
            flags = []
            if k.get("clickable") == "true":
                flags.append("clickable")
            if k.get("checkable") == "true":
                flags.append(f"checkable checked={k.get('checked')}")
            tag = f"  [{', '.join(flags)}]" if flags else ""
            print(f"  sel{i}: ({kx1},{ky1})-({kx2},{ky2}) lebar={kx2 - kx1:<4} "
                  f"{k.get('text')!r}{tag}")
        print("-" * 78)

    print("\nSemua teks sel pertama tiap baris:")
    for node, kids in rows:
        x1, y1, x2, y2 = bounds(kids[0])
        print(f"  ({x1},{y1})-({x2},{y2})  {kids[0].get('text')!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
