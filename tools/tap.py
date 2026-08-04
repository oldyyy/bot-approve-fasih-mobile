"""Tap satu elemen lalu tampilkan isi layar sesudahnya.

Alat pemetaan manual. Target dipilih dengan pencocokan persis, dan item
berbahaya ditolak, supaya tidak ada aksi tak sengaja saat menjelajah.

Contoh:
  .venv\\Scripts\\python.exe tools\\tap.py --id sidebar-toggle
  .venv\\Scripts\\python.exe tools\\tap.py --teks "SE2026 - P"
  .venv\\Scripts\\python.exe tools\\tap.py --lihat
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import layar
from bot.alur import TERLARANG  # satu sumber daftar hitam, jangan disalin
from bot.perangkat import hubungkan


def tampilkan(root) -> None:
    for teks in layar.ringkas_layar(root):
        print(f"  {teks}")


def main() -> int:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--id", dest="rid", help="resource-id target")
    g.add_argument("--teks", dest="teks", help="teks persis target")
    g.add_argument("--lihat", action="store_true", help="hanya tampilkan layar")
    p.add_argument("--jeda", type=float, default=2.5, help="detik tunggu setelah tap")
    p.add_argument("--cari", action="store_true",
                   help="hanya cari targetnya, jangan ditekan")
    p.add_argument("--perangkat", default=None,
                   help="port atau serial instance BlueStacks, mis. 5665")
    a = p.parse_args()

    d = hubungkan(a.perangkat)
    root = layar.pohon(d)
    print(f"Activity: {d.app_current()['activity']}")

    if a.lihat:
        print("\n--- isi layar ---")
        tampilkan(root)
        return 0

    if a.teks:
        if layar.normalisasi(a.teks) in TERLARANG:
            print(f"DITOLAK: {a.teks!r} ada di daftar terlarang.")
            return 1
        # Pakai pencocokan ternormalisasi supaya tombol berspasi seperti
        # "A P P R O V E" ikut ketemu.
        hit = layar.cari_teks_mana_saja(root, [a.teks], harus_clickable=True)
        if hit is None:
            hit = layar.cari_teks_mana_saja(root, [a.teks])
        label = repr(a.teks)
    else:
        hit = layar.cari_id(root, a.rid)
        label = f"id={a.rid}"

    if hit is None:
        print(f"\nTIDAK DITEMUKAN: {label}")
        print("\n--- isi layar ---")
        tampilkan(root)
        return 1

    node, bounds = hit
    if layar.normalisasi(node.get("text", "")) in TERLARANG:
        print(f"DITOLAK: node target bertuliskan {node.get('text')!r}.")
        return 1

    titik = layar.titik_tengah(bounds)
    if a.cari:
        print(f"\nKETEMU {label}")
        print(f"  teks sebenarnya : {node.get('text')!r}")
        print(f"  ternormalisasi  : {layar.normalisasi(node.get('text', ''))!r}")
        print(f"  bounds          : {bounds}  -> titik tap {titik}")
        print(f"  clickable       : {node.get('clickable')}")
        print("\n(mode --cari: tidak ditekan)")
        return 0

    print(f"\nTap {label} di {titik} (bounds {bounds})")
    d.click(*titik)
    time.sleep(a.jeda)

    sesudah = layar.pohon(d)
    print(f"\nActivity: {d.app_current()['activity']}")
    print("\n--- isi layar sesudah tap ---")
    tampilkan(sesudah)
    return 0


if __name__ == "__main__":
    sys.exit(main())
