"""Tampilkan instance BlueStacks yang siap dipakai, beserta layar aktifnya.

Dipakai untuk tahu nilai --perangkat mana yang harus diberikan ke jalankan.py
saat lebih dari satu instance berjalan.

Jalankan: .venv\\Scripts\\python.exe tools\\daftar_perangkat.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uiautomator2 as u2

from bot import layar
from bot.perangkat import daftar_perangkat

CATATAN = Path(__file__).resolve().parent.parent / "catatan"


def main() -> int:
    try:
        serial = daftar_perangkat()
    except RuntimeError as e:
        print(f"GAGAL: {e}")
        return 1

    print(f"{len(serial)} instance siap:\n")
    for s in serial:
        port = s.split(":")[1]
        print(f"  {s}   (--perangkat {port})")
        try:
            d = u2.connect(s)
            kini = d.app_current()
            print(f"    paket    : {kini.get('package')}")
            print(f"    activity : {kini.get('activity')}")
            info = layar.baca_status_filter(layar.pohon(d))
            if info.get("wilayah1"):
                print(f"    wilayah  : {info['wilayah1']}")
                print(f"    filter   : {info.get('filtered', '-')}")
        except Exception as e:  # noqa: BLE001 - sekadar laporan keadaan
            print(f"    (tidak bisa dibaca: {type(e).__name__}: {e})")
        print()

    kunci = sorted(CATATAN.glob("kunci-*.json")) if CATATAN.exists() else []
    if kunci:
        print("Wilayah yang sedang terkunci:")
        for k in kunci:
            print(f"  {k.stem.removeprefix('kunci-')}  ({k})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
