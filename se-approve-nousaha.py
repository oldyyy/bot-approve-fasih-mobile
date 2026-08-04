"""Approve atau reject SE2026 berdasarkan Selisih Pendapatan dan Pengeluaran.

Tiap putaran: terapkan filter Submit, ambil BARIS PERTAMA, pastikan kolom
"Jumlah Usaha" bernilai 0 (kalau bukan, bot berhenti tanpa membuka apa pun),
buka kuesioner, masuk seksi "SE2026 - L BLOK IV", gulir sampai menemukan
"Selisih Pendapatan dan Pengeluaran (Rp)", lalu:

  nilai >= 0     -> APPROVE  (nol ikut di-approve)
  nilai negatif  -> REJECT

PERHATIAN: ini satu-satunya alur yang boleh menekan REJECT. Tombol itu ada
di daftar terlarang global karena letaknya persis di sebelah APPROVE, dan
di sini dibuka lewat izin eksplisit per-panggilan.

Prasyarat: layar Daftar Assignment sudah terbuka di wilayah yang dituju.

Contoh:
  .venv\\Scripts\\python.exe se-approve-nousaha.py --loop 1 --kering --perangkat 5666
  .venv\\Scripts\\python.exe se-approve-nousaha.py --loop 5 --perangkat 5666
"""

from __future__ import annotations

import sys

from bot import alur
from bot.runner import jalankan_cli


def putuskan(d, catat) -> tuple[str, str]:
    """Baca selisih di BLOK IV, lalu tentukan approve atau reject."""
    alur.ke_seksi_target(d, catat=catat, seksi=alur.SEKSI_BLOK4)
    nilai, mentah = alur.baca_selisih(d, catat=catat)

    # Nol termasuk approve, jadi hanya nilai negatif yang di-reject.
    return ("reject" if nilai < 0 else "approve"), mentah


if __name__ == "__main__":
    sys.exit(jalankan_cli(
        nama_alur="se-approve-nousaha",
        deskripsi=__doc__,
        diterima=None,
        nama_soal="Selisih Pendapatan dan Pengeluaran",
        kata_cari=None,
        putuskan=putuskan,
        # Diperiksa dari daftar, sebelum baris dibuka - jadi baris yang tidak
        # lolos tidak pernah berubah status.
        syarat_kolom={"Jumlah Usaha": "0"},
    ))
