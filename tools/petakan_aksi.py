"""Petakan menu yang muncul setelah menekan 'Aksi'.

BERHENTI setelah menu terbuka. Tidak menekan 'Buka' dan tidak menyentuh
dialog konfirmasi, karena kedua langkah itu mengubah status assignment
di server.

Jalankan: .venv\\Scripts\\python.exe tools\\petakan_aksi.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import layar
from bot.cli import ambil_perangkat
from bot.perangkat import hubungkan


def main() -> int:
    d = hubungkan(ambil_perangkat())
    root = layar.pohon(d)

    status = layar.baca_status_filter(root)
    print(f"Wilayah : {status.get('wilayah1', '?')}")
    print(f"Filter  : {status.get('filtered', '?')}")
    print(f"Sortir  : {status.get('sorted', '?')}")
    print(f"Jumlah  : {status.get('example_info', '?')}")

    if status.get("filtered") != "Filter By Submit":
        print("\nBATAL: filter bukan 'Filter By Submit'. Terapkan filter dulu.")
        return 1

    baris = layar.baris_terlihat(root)
    if not baris:
        print("\nBATAL: tidak ada baris data di layar.")
        return 1

    target = next((b for b in baris if not b.terbentang), None)
    if target is None:
        print("\nSemua baris terlihat sudah terbentang.")
        target = baris[0]
    else:
        print(f"\nMembentangkan: {target.nama!r} di {target.titik_kontrol}")
        d.click(*target.titik_kontrol)
        time.sleep(2)
        root = layar.pohon(d)
        cek = next((b for b in layar.baris_terlihat(root) if b.nama == target.nama), None)
        if cek is None or not cek.terbentang:
            print("BATAL: baris gagal terbentang.")
            return 1
        print("Baris terbentang.")

    # Baca detail baris yang terbentang sebelum menyentuh Aksi.
    print("\n--- detail baris terbentang ---")
    for teks in layar.ringkas_layar(root):
        if any(k in teks for k in ("Status", "Mode", "User saat ini", "Skala Usaha",
                                   "Jumlah Usaha", "Kode Pos", "Perubahan SLS", "IDSBR")):
            print(f"  {teks}")

    hit = layar.cari_teks(root, "Aksi", harus_clickable=True)
    if hit is None:
        print("\nBATAL: tombol 'Aksi' yang clickable tidak ditemukan.")
        return 1

    _, bounds = hit
    titik = layar.titik_tengah(bounds)
    print(f"\nMenekan 'Aksi' di {titik} (bounds {bounds})")
    d.click(*titik)
    time.sleep(2)

    sesudah = layar.pohon(d)
    print(f"\nActivity: {d.app_current()['activity']}")
    print("\n--- isi layar setelah 'Aksi' ---")
    for teks in layar.ringkas_layar(sesudah):
        print(f"  {teks}")

    print("\nBERHENTI DI SINI. 'Buka' dan konfirmasi tidak ditekan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
