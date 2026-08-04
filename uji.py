"""Uji fungsi murni yang tidak butuh BlueStacks.

Semua kasus di sini diambil dari data yang benar-benar muncul di layar FASIH
selama pengembangan - termasuk yang dulu menyebabkan bug.

Jalankan: .venv\\Scripts\\python.exe uji.py
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

from bot import alur, layar

gagal = 0


def cek(nama: str, dapat, harap) -> None:
    global gagal
    ok = dapat == harap
    gagal += not ok
    tanda = "OK  " if ok else "GAGAL"
    print(f"{tanda} {nama}")
    if not ok:
        print(f"      dapat : {dapat!r}")
        print(f"      harap : {harap!r}")


print("-- urai_angka: format Indonesia, titik = pemisah ribuan --")
for teks, harap in [("1.255.952", 1255952.0), ("200.000", 200000.0),
                    ("-48.810", -48810.0), ("(1.255.952)", -1255952.0),
                    ("Rp 2.494.048", 2494048.0), ("1.234,56", 1234.56),
                    ("0", 0.0)]:
    cek(f"urai_angka({teks!r})", alur.urai_angka(teks), harap)

print("\n-- keputusan selisih: hanya negatif yang reject --")
for teks, harap in [("1.764.286", "approve"), ("0", "approve"),
                    ("-0", "approve"), ("0,00", "approve"),
                    ("-1", "reject"), ("-1.410.714", "reject")]:
    nilai = alur.urai_angka(teks)
    cek(f"selisih {teks!r}", "reject" if nilai < 0 else "approve", harap)

print("\n-- cocok_pilihan: pencocokan awalan --")
K = alur.KEBERADAAN_DITERIMA
B = alur.KODE_BANGUNAN_DITERIMA
for teks, diterima, harap in [
        ("0. Tidak Ditemukan", K, True),
        ("0. Tidak Ditemukan (STOP)", K, True),      # varian keluarga
        ("3. Meninggal", K, True),
        ("1. Ditemukan", K, False),
        ("6. Keluarga Khusus", K, False),
        ("7. Data diperoleh dari Kantor Pusat (KP)", K, False),
        ("6. Bangunan Lainnya yang Tidak Tercakup (Tempat Judi, "
         "Tempat Layanan Kencan, Bangunan Kosong/ Rusak)", B, True),
        ("1. Bangunan Khusus Usaha", B, False)]:
    cek(f"cocok_pilihan({teks[:34]!r}...)", alur.cocok_pilihan(teks, diterima), harap)

print("\n-- normalisasi: tombol berspasi antar huruf --")
cek("A P P R O V E", layar.normalisasi("A P P R O V E"), "approve")
cek("R E J E C T di daftar terlarang",
    layar.normalisasi("R E J E C T") in alur.TERLARANG, True)
cek("APPROVE tidak terlarang",
    layar.normalisasi("APPROVE") in alur.TERLARANG, False)

print("\n-- pembeda & status baris: susunan kolom beda antar survei --")
for nama, sel, pembeda, status in [
        ("SE2026 usaha", ["DUSUN I", "- / 43974516", "-", "-"],
         "DUSUN I|- / 43974516|-|-", ""),
        ("kosong nomor 17", ["-", "17 /", "-", "-"], "-|17 /|-|-", ""),
        ("sakernas", ["1", "0", "1", "SUBMITTED BY PPL", "arnoldyfatwa"],
         "1|0|1|arnoldyfatwa", "SUBMITTED BY PPL"),
        ("sakernas approved", ["1", "0", "1", "APPROVED BY PML", "arnoldyfatwa"],
         "1|0|1|arnoldyfatwa", "APPROVED BY PML")]:
    cek(f"pembeda {nama}", layar._pembeda_baris(sel), pembeda)
    cek(f"status  {nama}", layar._status_baris(sel), status)

cek("pembeda stabil walau status berubah",
    layar._pembeda_baris(["1", "0", "1", "SUBMITTED BY PPL", "x"])
    == layar._pembeda_baris(["1", "0", "1", "APPROVED BY PML", "x"]), True)

cek("lima baris bernama sama tetap unik",
    len({layar._pembeda_baris(["-", f"{n} /", "-", "-"])
         for n in (57, 59, 60, 61, 62)}), 5)

print("\n-- kolom_tabel: indeks dibaca dari nama header --")
XML = """<hierarchy>
  <node text="Nama Keluarga/Bangunan/Usaha: activate to sort column ascending"
        bounds="[22,587][336,736]"/>
  <node text="Nomor Urut Bangunan / IDSBR: activate to sort column ascending"
        bounds="[459,587][615,736]"/>
  <node text="Jumlah Usaha: activate to sort column ascending"
        bounds="[612,587][708,736]"/>
  <node text="Status: activate to sort column descending"
        bounds="[705,587][879,736]"/>
</hierarchy>"""
root = ET.fromstring(XML)
cek("urutan kolom", layar.kolom_tabel(root),
    ["Nama Keluarga/Bangunan/Usaha", "Nomor Urut Bangunan / IDSBR",
     "Jumlah Usaha", "Status"])

baris = layar.Baris(nama="X", terbentang=False, bounds=(0, 0, 0, 0),
                    sel=("+ X", "47 /", "0", "SUBMITTED BY Pencacah"))
cek("nilai_kolom Jumlah Usaha", layar.nilai_kolom(root, baris, "Jumlah Usaha"), "0")
cek("nilai_kolom kolom tak ada", layar.nilai_kolom(root, baris, "Khayalan"), None)

print("\n-- baris_terlihat: prefiks +/- dan sel IDSBR yang mirip baris --")
XML2 = """<hierarchy>
  <node bounds="[22,704][879,761]">
    <node index="0" text="+ BANGUNAN KOSONG 17" bounds="[22,704][361,761]"/>
    <node index="1" text="-" bounds="[360,704][496,761]"/>
    <node index="2" text="17 /" bounds="[495,704][675,761]"/>
  </node>
  <node bounds="[22,760][879,817]">
    <node index="0" text="- RUMAH KOSONG 24" bounds="[22,760][361,817]"/>
    <node index="1" text="-" bounds="[360,760][496,817]"/>
    <node index="2" text="- / 43974516" bounds="[495,760][675,817]"/>
  </node>
</hierarchy>"""
hasil = layar.baris_terlihat(ET.fromstring(XML2))
cek("jumlah baris (sel '- / 43974516' bukan baris)", len(hasil), 2)
cek("nama baris 1", hasil[0].nama, "BANGUNAN KOSONG 17")
cek("terbentang baris 1", hasil[0].terbentang, False)
cek("terbentang baris 2", hasil[1].terbentang, True)

print()
if gagal:
    print(f"{gagal} uji GAGAL")
    sys.exit(1)
print("semua uji lolos")
