"""Kunci per wilayah untuk run yang berjalan bersamaan.

Dua instance BlueStacks boleh jalan sekaligus, tapi tidak boleh menggarap
wilayah yang sama: keduanya akan mengambil baris pertama yang sama, saling
membuka assignment yang sedang diproses yang lain, dan hasilnya tidak bisa
ditelusuri dari log mana pun.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class KunciDipakai(RuntimeError):
    """Wilayah sedang digarap run lain."""


@contextmanager
def kunci_wilayah(folder: Path, kode: str, serial: str, paksa: bool = False):
    """Pegang kunci untuk satu wilayah selama run berlangsung."""
    folder.mkdir(exist_ok=True)
    berkas = folder / f"kunci-{kode}.json"

    if berkas.exists() and not paksa:
        try:
            lama = json.loads(berkas.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            lama = {}
        raise KunciDipakai(
            f"Wilayah {kode} sedang dikunci oleh run lain "
            f"(perangkat={lama.get('serial', '?')}, pid={lama.get('pid', '?')}, "
            f"mulai={lama.get('mulai', '?')}).\n"
            f"Kalau run itu sudah mati, hapus berkas ini: {berkas}\n"
            "Atau jalankan ulang dengan --abaikan-kunci."
        )

    berkas.write_text(json.dumps({
        "wilayah": kode,
        "serial": serial,
        "pid": os.getpid(),
        "mulai": datetime.now().isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")

    try:
        yield berkas
    finally:
        try:
            berkas.unlink()
        except OSError:
            pass
