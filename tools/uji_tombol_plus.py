"""Uji apakah tanda '+' di sisi kiri nama keluarga bisa ditekan.

Menekan '+' pada DataTables Responsive hanya membentangkan baris anak
(tidak mengirim apa pun ke server), dan bisa dibatalkan dengan menekan
ulang di titik yang sama.

Jalankan: .venv\\Scripts\\python.exe tools\\uji_tombol_plus.py
"""

import re
import sys
import time
import xml.etree.ElementTree as ET

import uiautomator2 as u2

SERIAL = "127.0.0.1:5615"
BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
# Lebar kira-kira glyph '+' di tepi kiri sel (DataTables dtr-control).
OFFSET_X = 16


def bounds(node):
    m = BOUNDS_RE.match(node.get("bounds", ""))
    return tuple(int(g) for g in m.groups()) if m else (0, 0, 0, 0)


def sel_nama(d):
    """Kumpulkan sel yang teksnya diawali '+' atau '-' (baris data)."""
    root = ET.fromstring(d.dump_hierarchy())
    out = []
    for node in root.iter("node"):
        text = node.get("text", "")
        if re.match(r"^[+-] \S", text):
            out.append((text, bounds(node)))
    return out


def main() -> int:
    d = u2.connect(SERIAL)

    sebelum = sel_nama(d)
    if not sebelum:
        print("Tidak ada baris data di layar. Pastikan daftar sudah termuat.")
        return 1

    teks, (x1, y1, x2, y2) = sebelum[0]
    tx, ty = x1 + OFFSET_X, (y1 + y2) // 2
    print(f"Baris uji : {teks!r}")
    print(f"Sel       : ({x1},{y1})-({x2},{y2})")
    print(f"Titik tap : ({tx},{ty})")
    print(f"Jumlah node teks sebelum tap: {len(ET.fromstring(d.dump_hierarchy()).findall('.//node'))}")

    d.click(tx, ty)
    time.sleep(1.5)

    sesudah = sel_nama(d)
    akt = d.app_current()["activity"]
    print(f"\nActivity setelah tap: {akt}")
    if sesudah:
        print(f"Teks baris pertama sekarang: {sesudah[0][0]!r}")
        berubah = sesudah[0][0][0] != teks[0]
        print(f"Tanda +/- berubah: {berubah}")
    print(f"Jumlah node teks sesudah tap: {len(ET.fromstring(d.dump_hierarchy()).findall('.//node'))}")

    print("\n--- teks yang muncul/hilang ---")
    a = {t for t, _ in sebelum}
    b = {t for t, _ in sesudah}
    for t in sorted(b - a):
        print(f"  + {t}")
    for t in sorted(a - b):
        print(f"  - {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
