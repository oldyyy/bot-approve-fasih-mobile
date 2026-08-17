"""Kunci per wilayah untuk run yang berjalan bersamaan.

Dua instance BlueStacks boleh jalan sekaligus, tapi tidak boleh menggarap
wilayah yang sama: keduanya akan mengambil baris pertama yang sama, saling
membuka assignment yang sedang diproses yang lain, dan hasilnya tidak bisa
ditelusuri dari log mana pun.
"""

from __future__ import annotations

import ctypes
import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class KunciDipakai(RuntimeError):
    """Wilayah sedang digarap run lain."""


def _proses_hidup(pid: int) -> bool:
    """Apakah proses dengan pid tertentu masih berjalan.

    os.kill tidak dipakai: di Windows pemanggilan itu justru mematikan
    prosesnya, bukan sekadar memeriksa.
    """
    if not pid:
        return False
    SYNCHRONIZE = 0x00100000
    h = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not h:
        return False
    ctypes.windll.kernel32.CloseHandle(h)
    return True


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
        # Run yang dihentikan paksa meninggalkan kuncinya. Kunci seperti itu
        # tidak menjaga apa pun, jadi diambil alih - yang menahan hanya kunci
        # milik proses yang benar-benar masih berjalan.
        if _proses_hidup(int(lama.get("pid") or 0)):
            raise KunciDipakai(
                f"Wilayah {kode} sedang dikunci oleh run lain "
                f"(perangkat={lama.get('serial', '?')}, pid={lama.get('pid', '?')}, "
                f"mulai={lama.get('mulai', '?')}).\n"
                f"Kalau run itu sudah mati, hapus berkas ini: {berkas}\n"
                "Atau jalankan ulang dengan --abaikan-kunci."
            )
        print(f"[kunci] kunci lama dari pid {lama.get('pid', '?')} sudah mati, "
              "diambil alih")

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
