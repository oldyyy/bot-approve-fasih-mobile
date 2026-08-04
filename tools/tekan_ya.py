"""Tekan 'YA' pada dialog konfirmasi buka assignment, lalu catat akibatnya.

Hanya jalan kalau dialog konfirmasi yang benar sedang tampil. Judul dan
pertanyaannya diverifikasi lebih dulu supaya tombol 'YA' milik dialog lain
tidak pernah tertekan.

Jalankan: .venv\\Scripts\\python.exe tools\\tekan_ya.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import layar
from bot.perangkat import hubungkan

PERTANYAAN = "Anda akan membuka assignment ini?"


def main() -> int:
    d = hubungkan()
    root = layar.pohon(d)

    terlihat = {t.rstrip(" *") for t in layar.ringkas_layar(root)}
    if PERTANYAAN not in terlihat:
        print(f"BATAL: dialog {PERTANYAAN!r} tidak sedang tampil.")
        print("Yang terlihat di layar:")
        for t in sorted(terlihat):
            print(f"  {t}")
        return 1

    hit = layar.cari_teks(root, "YA", harus_clickable=True)
    if hit is None:
        print("BATAL: tombol 'YA' tidak ditemukan atau tidak clickable.")
        return 1

    node, bounds = hit
    if node.get("text") != "YA":
        print(f"BATAL: node target bertuliskan {node.get('text')!r}.")
        return 1

    titik = layar.titik_tengah(bounds)
    print(f"Dialog terverifikasi: {PERTANYAAN!r}")
    print(f"Menekan 'YA' di {titik} (bounds {bounds})")
    d.click(*titik)
    time.sleep(3)

    sesudah = layar.pohon(d)
    print(f"\nActivity: {d.app_current()['activity']}")

    status = layar.baca_status_filter(sesudah)
    if status:
        print(f"Wilayah : {status.get('wilayah1', '?')}")
        print(f"Filter  : {status.get('filtered', '?')}")

    print("\n--- isi layar setelah 'YA' ---")
    for teks in layar.ringkas_layar(sesudah):
        print(f"  {teks}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
