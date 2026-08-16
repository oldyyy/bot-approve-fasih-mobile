"""Reject assignment berdasarkan daftar nama.

Untuk tiap nama: cari di kotak Search, baca WARNA barisnya, lalu

  biru  (Submit) -> buka assignment, Approval, REJECT, ulangi sampai merah
  merah (Reject) -> sudah selesai, lanjut ke nama berikutnya
  lain           -> dicatat dan dilewati, tidak disentuh

PERHATIAN: REJECT ada di daftar terlarang global karena letaknya persis di
sebelah APPROVE pada layar pilihan. Di sini tombol itu dibuka lewat izin
per-panggilan di `alur.reject`, dan tetap melalui verifikasi teks yang sama.

Contoh:
  .venv\\Scripts\\python.exe reject-list.py --perangkat 5665 --kering --nama "BUDI"
  .venv\\Scripts\\python.exe reject-list.py --perangkat 5665 --berkas daftar.txt
"""

from __future__ import annotations

import sys

from bot import alur
from bot.daftar import jalankan_daftar

if __name__ == "__main__":
    sys.exit(jalankan_daftar(
        nama_alur="reject",
        deskripsi=__doc__,
        warna_syarat="biru",
        warna_selesai="merah",
        aksi=alur.reject,
        nama_aksi="REJECT",
    ))
