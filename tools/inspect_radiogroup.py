"""Tampilkan seluruh atribut node di dalam satu radiogroup FormGear.

Dipakai untuk mencari tahu apakah keadaan "terpilih" benar-benar terekspos
ke accessibility tree, atau hanya ada di DOM.

Jalankan: .venv\\Scripts\\python.exe tools\\inspect_radiogroup.py radiogroup-cl-12
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import layar
from bot.cli import ambil_perangkat
from bot.perangkat import hubungkan


def cari_akar(root: ET.Element, prefiks: str) -> ET.Element | None:
    """Node terluar yang resource-id-nya diawali prefiks."""
    kandidat = [
        n for n in root.iter("node")
        if n.get("resource-id", "").startswith(prefiks)
    ]
    if not kandidat:
        return None
    # Ambil yang bounds-nya paling luas: itu wadah grupnya.
    return max(kandidat, key=lambda n: len(list(n.iter("node"))))


def main() -> int:
    prefiks = sys.argv[1] if len(sys.argv) > 1 else "radiogroup-cl-12"
    d = hubungkan(ambil_perangkat())
    root = layar.pohon(d)

    # Cetak seluruh node yang resource-id-nya mengandung prefiks, plus induknya.
    induk = {c: p for p in root.iter("node") for c in p}

    print(f"Node yang resource-id-nya diawali {prefiks!r}:\n")
    for n in root.iter("node"):
        rid = n.get("resource-id", "")
        if not rid.startswith(prefiks):
            continue
        p = induk.get(n)
        print(f"  {rid}")
        print(f"    class={n.get('class')} bounds={n.get('bounds')}")
        print(f"    text={n.get('text')!r} desc={n.get('content-desc')!r}")
        print(f"    checkable={n.get('checkable')} checked={n.get('checked')} "
              f"selected={n.get('selected')} clickable={n.get('clickable')} "
              f"focusable={n.get('focusable')} focused={n.get('focused')} "
              f"enabled={n.get('enabled')}")
        if p is not None:
            print(f"    induk: rid={p.get('resource-id')!r} class={p.get('class')} "
                  f"selected={p.get('selected')} checked={p.get('checked')}")
        print()

    print("Uji screenshot lewat agen uiautomator2 (bukan adb screencap):")
    try:
        img = d.screenshot()
        keluar = Path(__file__).resolve().parent.parent / "layar_uji.png"
        img.save(keluar)
        print(f"  BERHASIL -> {keluar} ({keluar.stat().st_size} byte, {img.size})")
    except Exception as e:  # noqa: BLE001 - sekadar laporan kemampuan
        print(f"  GAGAL: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
