"""Approve pemutakhiran Sakernas tanpa pengecekan isi kuesioner.

Tiap putaran: terapkan filter Submit, ambil BARIS PERTAMA, buka kuesioner,
lalu langsung approve. Tidak ada seksi yang dibuka dan tidak ada pertanyaan
yang diperiksa.

PERHATIAN: alur ini sengaja tanpa verifikasi isi. Penyaringnya hanya dua -
filter 'Submit' pada daftar, dan Status baris harus 'SUBMITTED BY Pencacah'.
Pastikan wilayah yang terbuka memang wilayah Sakernas yang dituju, karena
bot tidak punya cara lain untuk mengenali salah sasaran.

Prasyarat: layar Daftar Assignment sudah terbuka di wilayah yang dituju.

Contoh:
  .venv\\Scripts\\python.exe sakernas-pemutakhiran.py --loop 1 --kering --perangkat 5666
  .venv\\Scripts\\python.exe sakernas-pemutakhiran.py --loop 5 --perangkat 5666
"""

from __future__ import annotations

import sys

from bot.runner import jalankan_cli

if __name__ == "__main__":
    sys.exit(jalankan_cli(
        nama_alur="sakernas-pemutakhiran",
        deskripsi=__doc__,
        diterima=None,          # None = lewati seluruh pengecekan kuesioner
        nama_soal="(tanpa pengecekan)",
        kata_cari=None,
    ))
