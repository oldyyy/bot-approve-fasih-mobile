"""Mesin bersama untuk alur yang digerakkan daftar nama.

Berbeda dari `bot/runner.py` yang memproses N baris pertama, alur di sini
mencari nama satu per satu dan memutuskan berdasarkan WARNA barisnya. Yang
membedakan antar alur hanya tiga hal: warna yang jadi syarat, warna yang
menandakan selesai, dan aksi yang dijalankan.
"""

from __future__ import annotations

import argparse
import csv
import time
from datetime import datetime
from pathlib import Path

from bot import alur, layar, warna
from bot.kunci import KunciDipakai, kunci_wilayah
from bot.perangkat import hubungkan

CATATAN = Path(__file__).resolve().parent.parent / "catatan"
MAKS_PERCOBAAN = 4

BERMASALAH = {"GAGAL", "ambigu", "tidak ditemukan", "warna tak terduga",
              "hilang setelah aksi", "belum berubah"}


def cari_baris(d, nama: str, jeda: float = 2.5):
    """Isi kotak Search lalu kembalikan (pohon, baris yang cocok)."""
    hit = layar.cari_kelas(layar.pohon(d), alur.KELAS_INPUT)
    if hit is None:
        raise alur.AlurGagal("Kotak Search tidak ada di layar.")
    d.click(*layar.titik_tengah(hit[1]))
    time.sleep(0.3)
    d(className=alur.KELAS_INPUT).set_text(nama)
    time.sleep(jeda)
    root = layar.pohon(d)
    return root, layar.baris_terlihat(root)


def baca_warna(d, hwnd, baris) -> tuple[str, tuple[int, int, int]]:
    img = warna.tangkap(hwnd)
    skala, offset = warna.kalibrasi(img)
    rgb = warna.warna_di(img, skala, offset, baris.bounds)
    return warna.klasifikasi(rgb), rgb


def _proses(d, hwnd, nama, syarat, selesai, aksi, catat) -> tuple[str, str]:
    root, baris = cari_baris(d, nama)
    if not baris:
        return "tidak ditemukan", ""
    if len(baris) > 1:
        return "ambigu", f"{len(baris)} baris cocok: {[b.nama for b in baris]}"

    b = baris[0]
    catat(f"    baris  : {b.label}")

    for percobaan in range(1, MAKS_PERCOBAAN + 1):
        w, rgb = baca_warna(d, hwnd, b)
        st = layar.nilai_kolom(layar.pohon(d), b, "Status") or "-"
        catat(f"    warna  : {w} {rgb}  status={st}")

        if w == selesai:
            return ("sudah " + selesai if percobaan == 1 else "selesai"), st
        if w != syarat:
            return "warna tak terduga", f"{w} {rgb}, status={st}"

        catat(f"    siklus ke-{percobaan}")
        alur.set_bentang(d, b.kunci, True)
        alur.buka_kuesioner(d, b.kunci, catat=catat)
        alur.tunggu_kuesioner_siap(d)
        aksi(d, catat=catat)
        alur.pastikan_daftar_siap(d, catat=catat)

        root, baris = cari_baris(d, nama)
        if not baris:
            return "hilang setelah aksi", ""
        b = baris[0]

    return "belum berubah", f"masih {syarat} setelah {MAKS_PERCOBAAN} percobaan"


def jalankan_daftar(*, nama_alur: str, deskripsi: str, warna_syarat: str,
                    warna_selesai: str, aksi, nama_aksi: str) -> int:
    p = argparse.ArgumentParser(
        description=deskripsi,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--nama", action="append", default=[],
                   help="nama yang akan diproses (boleh diulang)")
    p.add_argument("--berkas", default=None,
                   help="berkas teks berisi satu nama per baris")
    p.add_argument("--perangkat", default=None,
                   help="port instance BlueStacks, mis. 5665")
    p.add_argument("--kering", action="store_true",
                   help="hanya baca warna tiap nama, tidak melakukan aksi")
    p.add_argument("--abaikan-kunci", action="store_true")
    a = p.parse_args()

    daftar = list(a.nama)
    if a.berkas:
        daftar += [b.strip() for b in Path(a.berkas).read_text(
            encoding="utf-8").splitlines() if b.strip()]
    if not daftar:
        p.error("beri --nama atau --berkas")

    CATATAN.mkdir(exist_ok=True)
    stempel = datetime.now().strftime("%Y%m%d-%H%M%S")
    mode = "kering" if a.kering else "hidup"
    tanda = (a.perangkat or "auto").replace(":", "-").replace(".", "")
    log_path = CATATAN / f"{nama_alur}-{mode}-{tanda}-{stempel}.log"
    csv_path = CATATAN / f"{nama_alur}-{mode}-{tanda}-{stempel}.csv"

    with log_path.open("w", encoding="utf-8") as log:
        def catat(*bagian):
            teks = " ".join(str(b) for b in bagian)
            print(teks)
            log.write(teks + "\n")
            log.flush()

        catat(f"# {nama_alur} mode={mode} {stempel}  {len(daftar)} nama")
        catat(f"# syarat warna {warna_syarat} -> {nama_aksi} -> "
              f"selesai kalau {warna_selesai}")
        if not a.kering:
            catat(f"# MODE HIDUP: menekan BUKA, YA, {nama_aksi} sungguhan")

        try:
            d = hubungkan(a.perangkat)
            judul = warna.nama_instance(d.serial)
            hwnd = warna.cari_jendela(judul)
            wilayah = alur.tunggu_daftar_siap(d)
        except (RuntimeError, warna.GagalTangkap, alur.AlurGagal) as e:
            catat(f"GAGAL: {e}")
            return 1
        catat(f"Wilayah terkunci: {wilayah}  jendela {judul!r}")

        try:
            pengunci = kunci_wilayah(CATATAN, wilayah, d.serial,
                                     paksa=a.abaikan_kunci)
            pengunci.__enter__()
        except KunciDipakai as e:
            catat(f"GAGAL: {e}")
            return 1

        hasil = []
        try:
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["nama", "hasil", "keterangan"])
                f.flush()

                for i, nama in enumerate(daftar, 1):
                    catat(f"\n[{i}/{len(daftar)}] {nama}")
                    try:
                        if a.kering:
                            root, baris = cari_baris(d, nama)
                            if not baris:
                                res, ket = "tidak ditemukan", ""
                            else:
                                wr, rgb = baca_warna(d, hwnd, baris[0])
                                st = layar.nilai_kolom(root, baris[0], "Status")
                                catat(f"    {baris[0].label}")
                                catat(f"    warna  : {wr} {rgb}  status={st}")
                                res, ket = f"warna {wr}", f"{rgb}, status={st}"
                        else:
                            res, ket = _proses(d, hwnd, nama, warna_syarat,
                                               warna_selesai, aksi, catat)
                    except (alur.AlurGagal, warna.GagalTangkap) as e:
                        res, ket = "GAGAL", str(e)
                    catat(f"    hasil  : {res} {ket}".rstrip())
                    hasil.append((nama, res, ket))
                    w.writerow([nama, res, ket])
                    f.flush()
        finally:
            pengunci.__exit__(None, None, None)

        catat("\n--- ringkasan ---")
        for nama, res, ket in hasil:
            catat(f"  {nama:<22} {res} {ket}".rstrip())
        catat(f"\nLog : {log_path}")
        catat(f"CSV : {csv_path}")

        perlu = [h for h in hasil if h[1] in BERMASALAH]
        if perlu:
            catat(f"\n{len(perlu)} nama perlu diperiksa manual.")
            return 1
    return 0
