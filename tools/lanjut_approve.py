"""Tuntaskan assignment yang terlantar (sudah terbuka, belum di-approve).

Dijalankan dari dalam kuesioner. Nilai keberadaan diverifikasi ulang di
sini, jadi alat ini tidak bisa dipakai untuk meng-approve baris yang tidak
memenuhi syarat.

Jalankan: .venv\\Scripts\\python.exe tools\\lanjut_approve.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import alur, layar
from bot.cli import ambil_perangkat
from bot.perangkat import hubungkan


def main() -> int:
    d = hubungkan(ambil_perangkat())
    aktivitas = d.app_current().get("activity", "")
    print(f"Activity: {aktivitas}")

    if alur.AKTIVITAS_FORM not in aktivitas:
        print(f"BATAL: bukan layar kuesioner (butuh {alur.AKTIVITAS_FORM}).")
        return 1

    try:
        alur.ke_seksi_target(d, catat=lambda *b: print("   ", *b))
        cocok, nilai = alur.verifikasi_keberadaan(d)
    except alur.AlurGagal as e:
        print(f"BATAL: {e}")
        return 1

    print(f"Keberadaan terbaca: {nilai!r}")
    if not cocok:
        print(f"BATAL: bukan salah satu dari {list(alur.KEBERADAAN_DITERIMA)}.")
        return 1

    try:
        alur.approve(d, catat=lambda *b: print("   ", *b))
        alur.tunggu_daftar_siap(d)
    except alur.AlurGagal as e:
        print(f"\nBERHENTI: {e}")
        return 1

    info = layar.baca_status_filter(layar.pohon(d))
    print("\nSELESAI - kembali ke Daftar Assignment.")
    print(f"  wilayah : {info.get('wilayah1')}")
    print(f"  filter  : {info.get('filtered')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
