"""Tekan 'BUKA' di menu Aksi, lalu petakan dialog konfirmasi yang muncul.

Berhenti sebelum menekan tombol konfirmasi.

Jalankan: .venv\\Scripts\\python.exe tools\\petakan_buka.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import layar
from bot.cli import ambil_perangkat
from bot.perangkat import hubungkan

# Item menu Aksi yang tidak boleh tersentuh bot dalam keadaan apa pun.
TERLARANG = {"HAPUS", "ASSIGN", "RESTORE", "PINDAH MODE", "SINKRONISASI ASSIGNMENT INI"}


def main() -> int:
    d = hubungkan(ambil_perangkat())
    root = layar.pohon(d)

    terlihat = {t.rstrip(" *") for t in layar.ringkas_layar(root)}
    if "BUKA" not in terlihat:
        print("BATAL: menu Aksi tidak terbuka (teks 'BUKA' tidak ada di layar).")
        return 1

    hit = layar.cari_teks(root, "BUKA", harus_clickable=True)
    if hit is None:
        print("BATAL: 'BUKA' ada tapi tidak clickable.")
        return 1

    node, bounds = hit
    # Pengaman: pastikan node yang akan ditekan benar-benar bertuliskan BUKA
    # dan bukan salah satu item berbahaya di menu yang sama.
    teks = node.get("text", "")
    if teks != "BUKA" or teks in TERLARANG:
        print(f"BATAL: node target bertuliskan {teks!r}, bukan 'BUKA'.")
        return 1

    titik = layar.titik_tengah(bounds)
    print(f"Menekan 'BUKA' di {titik} (bounds {bounds})")
    d.click(*titik)
    time.sleep(2)

    sesudah = layar.pohon(d)
    print(f"\nActivity: {d.app_current()['activity']}")
    print("\n--- isi layar setelah 'BUKA' ---")
    for teks in layar.ringkas_layar(sesudah):
        print(f"  {teks}")

    print("\nBERHENTI. Tombol konfirmasi belum ditekan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
