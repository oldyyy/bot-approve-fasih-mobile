"""Laporkan warna tiap baris yang tampil, plus status teksnya.

Dipakai untuk memverifikasi kalibrasi pemetaan koordinat Android ke jendela.

Jalankan: .venv\\Scripts\\python.exe tools\\baca_warna.py --perangkat 5665
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import layar, warna
from bot.cli import ambil_perangkat
from bot.perangkat import hubungkan


def main() -> int:
    d = hubungkan(ambil_perangkat())
    judul = warna.nama_instance(d.serial)
    if judul is None:
        print(f"BATAL: nama instance untuk {d.serial} tidak ditemukan.")
        return 1
    print(f"instance {d.serial} -> jendela {judul!r}")

    try:
        hwnd = warna.cari_jendela(judul)
        img = warna.tangkap(hwnd)
        skala, offset_y = warna.kalibrasi(img)
    except warna.GagalTangkap as e:
        print(f"BATAL: {e}")
        return 1

    print(f"tangkapan {img.size}  skala {skala:.4f}  offset_y {offset_y}")

    root = layar.pohon(d)
    baris = layar.baris_terlihat(root)
    if not baris:
        print("Tidak ada baris di layar.")
        return 0

    print(f"\n{'nama':<40} {'warna':<10} {'rgb':<18} status")
    print("-" * 100)
    for b in baris:
        rgb = warna.warna_di(img, skala, offset_y, b.bounds)
        st = layar.nilai_kolom(root, b, "Status") or ""
        print(f"{b.nama[:38]:<40} {warna.klasifikasi(rgb):<10} {str(rgb):<18} {st}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
