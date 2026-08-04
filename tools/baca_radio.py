"""Laporkan pilihan aktif pada semua radiogroup yang tampil di layar.

Read-only: tidak menekan apa pun.

Jalankan: .venv\\Scripts\\python.exe tools\\baca_radio.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import layar
from bot.cli import ambil_perangkat
from bot.perangkat import hubungkan


def main() -> int:
    d = hubungkan(ambil_perangkat())
    root = layar.pohon(d)
    print(f"Activity: {d.app_current()['activity']}\n")

    prefiks = sorted({
        m.group(1)
        for n in root.iter("node")
        if (m := re.match(r"^(radiogroup-cl-\d+)-item-", n.get("resource-id", "")))
    })
    if not prefiks:
        print("Tidak ada radiogroup di layar ini.")
        return 0

    for p in prefiks:
        terpilih, tombol = layar.baca_radiogroup(root, p)
        print(f"{p}")
        print(f"  TERPILIH: {terpilih!r}" if terpilih
              else "  TERPILIH: (tidak ada / tidak terdeteksi)")
        for label, b in tombol.items():
            tanda = "->" if label == terpilih else "  "
            print(f"  {tanda} {label:<45} target tap {layar.titik_tengah(b)}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
