"""Pindai daftar assignment di wilayah yang sedang terbuka.

Aman: hanya membentangkan dan menutup baris DataTables (murni lokal),
tidak menekan Aksi/BUKA/YA dan tidak mengirim apa pun ke server.

Prasyarat: layar Daftar Assignment sudah terbuka di wilayah yang dituju,
dengan filter 'Filter By Submit' sudah diterapkan.

Contoh:
  .venv\\Scripts\\python.exe pindai.py
  .venv\\Scripts\\python.exe pindai.py --maks 5
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

from bot import alur
from bot.kunci import KunciDipakai, kunci_wilayah
from bot.perangkat import hubungkan

CATATAN = Path(__file__).resolve().parent / "catatan"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--maks", type=int, default=None,
                   help="berhenti setelah N baris (untuk uji cepat)")
    p.add_argument("--perangkat", default=None,
                   help="port atau serial instance BlueStacks, mis. 5665")
    p.add_argument("--abaikan-kunci", action="store_true",
                   help="jalan walau wilayahnya terkunci run lain (hati-hati)")
    a = p.parse_args()

    CATATAN.mkdir(exist_ok=True)
    stempel = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = CATATAN / f"pindai-{stempel}.log"
    csv_path = CATATAN / f"pindai-{stempel}.csv"

    with log_path.open("w", encoding="utf-8") as log:
        def catat(*bagian):
            teks = " ".join(str(b) for b in bagian)
            print(teks)
            log.write(teks + "\n")
            log.flush()

        catat(f"# pindai {stempel}")
        try:
            d = hubungkan(a.perangkat)
        except RuntimeError as e:
            catat(f"GAGAL: {e}")
            return 1

        # Pindai tidak mengubah data, tapi tetap mengendalikan UI: kalau bot
        # lain sedang bekerja di wilayah yang sama, keduanya saling merusak
        # navigasi. Jadi wilayahnya ikut dikunci.
        try:
            wilayah = alur.tunggu_daftar_siap(d)
        except alur.AlurGagal as e:
            catat(f"GAGAL: {e}")
            return 1

        try:
            pengunci = kunci_wilayah(CATATAN, wilayah, d.serial,
                                     paksa=a.abaikan_kunci)
            pengunci.__enter__()
        except KunciDipakai as e:
            catat(f"GAGAL: {e}")
            return 1

        try:
            hasil = alur.pindai(d, maks=a.maks, catat=catat)
        except alur.AlurGagal as e:
            catat(f"\nBERHENTI: {e}")
            return 1
        finally:
            pengunci.__exit__(None, None, None)

        layak = [r for r in hasil if r.layak]
        catat(f"\nTotal terpindai : {len(hasil)}")
        catat(f"Layak diproses  : {len(layak)}")
        catat(f"Dilewati        : {len(hasil) - len(layak)}")

        kolom = ["nama", "Status", "Skala Usaha / Jenis Prelist", "Jumlah Usaha",
                 "Perubahan SLS", "Kode Pos", "IDSBR UMKM SLS Sama",
                 "User saat ini", "Mode", "layak", "catatan"]
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=kolom)
            w.writeheader()
            for r in hasil:
                baris = {"nama": r.nama, "layak": "ya" if r.layak else "tidak",
                         "catatan": "; ".join(r.catatan)}
                baris.update({k: v for k, v in r.detail.items() if k in kolom})
                w.writerow(baris)

        catat(f"\nLog : {log_path}")
        catat(f"CSV : {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
