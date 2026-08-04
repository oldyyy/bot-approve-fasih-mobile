"""Jalankan alur approve FASIH sebanyak N putaran.

Tiap putaran: terapkan filter Submit, ambil BARIS PERTAMA, buka kuesioner,
periksa pertanyaan keberadaan, lalu approve kalau nilainya termasuk yang
diterima (kode 0/3/4/5 sesuai varian usaha maupun keluarga).

Prasyarat: layar Daftar Assignment sudah terbuka di wilayah yang dituju.

Contoh:
  .venv\\Scripts\\python.exe jalankan.py --loop 1 --kering
  .venv\\Scripts\\python.exe jalankan.py --loop 5 --perangkat 5666
"""

from __future__ import annotations

import sys

from bot import alur
from bot.runner import jalankan_cli

if __name__ == "__main__":
    sys.exit(jalankan_cli(
        nama_alur="jalan",
        deskripsi=__doc__,
        diterima=alur.KEBERADAAN_DITERIMA,
        nama_soal="keberadaan",
        kata_cari=None,
    ))
