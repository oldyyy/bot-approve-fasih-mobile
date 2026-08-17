"""Approve assignment yang nomor urut bangunannya kosong.

Adaptasi dari `jalankan.py`. Tiap putaran: terapkan filter Submit, ambil
BARIS PERTAMA, pastikan kolom "Nomor Urut Bangunan / IDSBR" nomor urutnya
'-' (kalau bukan, bot berhenti tanpa membuka apa pun), buka kuesioner,
periksa pertanyaan keberadaan, lalu approve.

Kolom itu berisi gabungan "<nomor urut> / <IDSBR>", jadi yang diperiksa
hanya bagian sebelum garis miring: "- /" dan "- / 43974516" sama-sama lolos,
"17 /" tidak.

Prasyarat: layar Daftar Assignment sudah terbuka di wilayah yang dituju.

Tanpa --loop, bot mengerjakan sampai daftarnya habis.

Contoh:
  .venv\\Scripts\\python.exe approve-nofound.py --kering --perangkat 5665
  .venv\\Scripts\\python.exe approve-nofound.py --perangkat 5665
  .venv\\Scripts\\python.exe approve-nofound.py --loop 5 --perangkat 5665
"""

from __future__ import annotations

import sys

from bot import alur
from bot.runner import jalankan_cli

KOLOM_NOURUT = "Nomor Urut Bangunan / IDSBR"


def nourut_kosong(nilai: str) -> bool:
    """Benar kalau nomor urut bangunan pada sel bernilai '-'."""
    return nilai.split("/")[0].strip() == "-"


nourut_kosong.penjelasan = "nomor urut bangunan harus '-'"


if __name__ == "__main__":
    sys.exit(jalankan_cli(
        nama_alur="approve-nofound",
        deskripsi=__doc__,
        diterima=alur.KEBERADAAN_DITERIMA,
        nama_soal="keberadaan",
        kata_cari=None,
        syarat_kolom={KOLOM_NOURUT: nourut_kosong},
    ))
