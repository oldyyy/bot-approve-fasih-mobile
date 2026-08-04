"""Approve assignment bangunan kosong.

Tiap putaran: terapkan filter Submit, pastikan kotak Search berisi 'kosong',
ambil BARIS PERTAMA (namanya pasti memuat kata itu), buka kuesioner, lalu
periksa "Kode Penggunaan Bangunan". Approve hanya kalau nilainya
'6. Bangunan Lainnya yang Tidak Tercakup'.

Kalau kotak Search sudah berisi 'kosong' - misalnya diisi manual sebelum
bot dijalankan - bot tidak mengetik ulang, langsung memakai hasilnya.

Prasyarat: layar Daftar Assignment sudah terbuka di wilayah yang dituju.

Contoh:
  .venv\\Scripts\\python.exe bangunan-kosong.py --loop 1 --kering --perangkat 5666
  .venv\\Scripts\\python.exe bangunan-kosong.py --loop 5 --perangkat 5666
"""

from __future__ import annotations

import sys

from bot import alur
from bot.runner import jalankan_cli

if __name__ == "__main__":
    sys.exit(jalankan_cli(
        nama_alur="bangunan-kosong",
        deskripsi=__doc__,
        diterima=alur.KODE_BANGUNAN_DITERIMA,
        nama_soal="kode penggunaan bangunan",
        kata_cari=alur.KATA_CARI_KOSONG,
    ))
