"""Periksa dan hidupkan ulang agen uiautomator2 di device.

Agen ini bisa mati sendiri di tengah run panjang. Kalau itu terjadi,
setiap panggilan dump_hierarchy menggantung tanpa batas waktu - bot
terlihat "diam" padahal sedang menunggu jawaban yang tidak akan datang.

Jalankan: .venv\\Scripts\\python.exe tools\\pulihkan_agen.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uiautomator2 as u2

from bot.perangkat import cari_serial


def main() -> int:
    serial = cari_serial()
    print(f"Serial: {serial}")
    d = u2.connect(serial)

    print(f"\nSetting: {d.settings}")
    print(f"Modul u2 punya HTTP_TIMEOUT? "
          f"{getattr(u2, 'HTTP_TIMEOUT', None)!r}")

    print("\nMenghidupkan ulang agen...")
    try:
        d.stop_uiautomator()
        time.sleep(2)
    except Exception as e:  # noqa: BLE001
        print(f"  (stop diabaikan: {e})")
    d.start_uiautomator()
    time.sleep(3)
    print("  agen dijalankan ulang")

    print("\nUji dump_hierarchy...")
    mulai = time.monotonic()
    xml = d.dump_hierarchy()
    print(f"  BERHASIL: {len(xml)} karakter dalam {time.monotonic() - mulai:.1f} detik")
    print(f"  Activity: {d.app_current()['activity']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
