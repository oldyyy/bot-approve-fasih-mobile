"""Pembantu argumen baris perintah yang dipakai bersama alat-alat pemetaan.

Sejak beberapa instance BlueStacks berjalan sekaligus, setiap alat harus bisa
diarahkan ke instance tertentu. Logikanya ditaruh di satu tempat supaya tiap
alat tidak perlu argparse sendiri hanya untuk satu opsi.
"""

from __future__ import annotations

import sys


def ambil_perangkat(argv: list[str] | None = None) -> str | None:
    """Cabut '--perangkat <port>' dari argv dan kembalikan nilainya.

    argv diubah di tempat, jadi sisa argumen posisional tetap bisa dibaca
    alat pemanggil seperti biasa.
    """
    argv = sys.argv if argv is None else argv
    for i, a in enumerate(argv):
        if a == "--perangkat" and i + 1 < len(argv):
            nilai = argv[i + 1]
            del argv[i:i + 2]
            return nilai
        if a.startswith("--perangkat="):
            nilai = a.split("=", 1)[1]
            del argv[i]
            return nilai
    return None
