"""Mesin bersama untuk semua alur approve.

Tiap alur (approve keberadaan, bangunan kosong, dan yang mungkin menyusul)
hanya berbeda pada tiga hal: kata kunci pencarian, pertanyaan yang
diperiksa, dan nilai yang dianggap sah. Sisanya - filter, kunci wilayah,
pencatatan, kode keluar - identik, jadi ditaruh di sini agar tidak ada dua
salinan yang bisa berbeda perilaku.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from bot import alur
from bot.kunci import KunciDipakai, kunci_wilayah
from bot.perangkat import hubungkan

CATATAN = Path(__file__).resolve().parent.parent / "catatan"


def jalankan_cli(*, nama_alur: str, deskripsi: str,
                 diterima: tuple[str, ...] | None, nama_soal: str,
                 kata_cari: str | None = None, putuskan=None,
                 syarat_kolom: dict[str, str] | None = None) -> int:
    """Jalankan satu alur approve.

    `diterima=None` berarti alur ini tidak memeriksa isi kuesioner sama
    sekali - satu-satunya penyaring adalah filter Submit dan Status baris.
    """
    p = argparse.ArgumentParser(
        description=deskripsi,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--loop", type=int, required=True,
                   help="jumlah baris yang diproses (wajib)")
    p.add_argument("--kering", action="store_true",
                   help="dry-run: satu putaran, berhenti sebelum menekan Aksi")
    p.add_argument("--perangkat", default=None,
                   help="port atau serial instance BlueStacks, mis. 5666. "
                        "Wajib kalau lebih dari satu instance sedang jalan")
    p.add_argument("--abaikan-kunci", action="store_true",
                   help="jalan walau wilayahnya terkunci run lain (hati-hati)")
    a = p.parse_args()

    if a.loop < 1:
        p.error("--loop harus >= 1")

    CATATAN.mkdir(exist_ok=True)
    stempel = datetime.now().strftime("%Y%m%d-%H%M%S")
    mode = "kering" if a.kering else "hidup"
    # Nama berkas menyertakan alur dan port supaya run yang berbarengan tidak
    # saling menimpa catatan, termasuk kalau mulai pada detik yang sama.
    tanda = (a.perangkat or "auto").replace(":", "-").replace(".", "")
    log_path = CATATAN / f"{nama_alur}-{mode}-{tanda}-{stempel}.log"
    csv_path = CATATAN / f"{nama_alur}-{mode}-{tanda}-{stempel}.csv"

    with log_path.open("w", encoding="utf-8") as log:
        def catat(*bagian):
            teks = " ".join(str(b) for b in bagian)
            print(teks)
            log.write(teks + "\n")
            log.flush()   # write-ahead: log harus selamat kalau bot mati

        catat(f"# {nama_alur} mode={mode} loop={a.loop} {stempel}")
        if putuskan is not None:
            catat(f"# keputusan dari : {nama_soal}")
            catat("# alur ini bisa APPROVE maupun REJECT")
        elif diterima:
            catat(f"# soal diperiksa : {nama_soal}")
            catat(f"# nilai diterima : {list(diterima)}")
        else:
            catat("# TANPA PENGECEKAN isi kuesioner - penyaring hanya filter "
                  "Submit pada daftar + status baris harus submitted")
        if kata_cari:
            catat(f"# kata pencarian : {kata_cari!r}")
        if syarat_kolom:
            catat(f"# syarat kolom   : {syarat_kolom}")
        if not a.kering:
            catat("# MODE HIDUP: menekan BUKA, YA, APPROVE sungguhan")

        try:
            d = hubungkan(a.perangkat)
        except RuntimeError as e:
            catat(f"GAGAL: {e}")
            return 1

        # Wilayah dibaca lebih dulu supaya bisa dikunci sebelum ada aksi.
        try:
            wilayah = alur.tunggu_daftar_siap(d)
        except alur.AlurGagal as e:
            catat(f"GAGAL: {e}")
            catat("Buka wilayahnya di BlueStacks sampai tabel assignment tampil.")
            return 1

        try:
            pengunci = kunci_wilayah(CATATAN, wilayah, d.serial,
                                     paksa=a.abaikan_kunci)
            pengunci.__enter__()
        except KunciDipakai as e:
            catat(f"GAGAL: {e}")
            return 1

        try:
            # CSV ditulis per baris, bukan di akhir: run yang terputus di
            # tengah tetap meninggalkan catatan lengkap.
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                # 'nomor' wajib: banyak assignment bernama identik.
                w.writerow(["nama", "nomor", "status", "nilai_soal",
                            "keputusan", "catatan"])
                f.flush()

                def simpan(r):
                    w.writerow([r.nama, r.nomor, r.status,
                                r.detail.get("NilaiSoal", ""),
                                r.detail.get("Keputusan", ""),
                                "; ".join(r.catatan)])
                    f.flush()

                hasil = alur.jalankan(d, loop=a.loop, kering=a.kering,
                                      catat=catat, simpan=simpan,
                                      diterima=diterima, nama_soal=nama_soal,
                                      kata_cari=kata_cari, putuskan=putuskan,
                                      syarat_kolom=syarat_kolom)
        finally:
            pengunci.__exit__(None, None, None)

        selesai = [r for r in hasil if "approved" in r.catatan]
        ditolak = [r for r in hasil if "rejected" in r.catatan]
        terlantar = [r for r in hasil
                     if any(c.startswith("TERLANTAR") for c in r.catatan)]
        catat(f"\nPutaran dijalankan : {len(hasil)}")
        catat(f"Ter-approve        : {len(selesai)}")
        if ditolak:
            catat(f"Ter-reject         : {len(ditolak)}")
            for r in ditolak:
                catat(f"  - {r.label}  nilai={r.detail.get('NilaiSoal', '?')}")
        if terlantar:
            catat(f"TERLANTAR          : {len(terlantar)}")
            for r in terlantar:
                catat(f"  - {r.label}  nilai={r.detail.get('NilaiSoal', '?')!r}")

        catat(f"\nLog : {log_path}")
        catat(f"CSV : {csv_path}")

        # Baris terlantar selalu berarti run ini butuh perhatian, walau
        # jumlah putarannya genap sesuai permintaan.
        if terlantar:
            catat("\nAda baris terlantar - tangani dulu sebelum run berikutnya.")
            return 1

        # Dry-run hanya menjalankan satu putaran, jadi targetnya beda.
        target = 1 if a.kering else a.loop
        if len(hasil) < target:
            catat("\nCatatan: putaran berhenti lebih awal - baca pesan "
                  "BERHENTI di atas.")
            return 1
    return 0
