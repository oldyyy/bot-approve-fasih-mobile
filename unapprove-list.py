"""Unapprove assignment berdasarkan daftar nama.

Untuk tiap nama: cari di kotak Search, baca WARNA barisnya, lalu

  hijau (Approve) -> buka assignment, Approval, UNAPPROVE, ulangi sampai biru
  biru  (Submit)  -> sudah selesai, lanjut ke nama berikutnya
  lain            -> dicatat dan dilewati, tidak disentuh

Teks kolom Status TIDAK bisa dipakai sebagai patokan: baris ber-status
REVOKED bisa tetap hijau, dan justru baris seperti itulah yang masih perlu
diproses. Satu siklus sering hanya mengubah teks status tanpa mengubah warna;
siklus kedua yang membuatnya biru.

Contoh:
  .venv\\Scripts\\python.exe unapprove-list.py --perangkat 5665 --kering --nama "BUDI"
  .venv\\Scripts\\python.exe unapprove-list.py --perangkat 5665 --berkas daftar.txt
"""

from __future__ import annotations

import sys

from bot import alur
from bot.daftar import jalankan_daftar

if __name__ == "__main__":
    sys.exit(jalankan_daftar(
        nama_alur="unapprove",
        deskripsi=__doc__,
        warna_syarat="hijau",
        warna_selesai="biru",
        aksi=alur.unapprove,
        nama_aksi="UNAPPROVE",
    ))
