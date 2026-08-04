"""Koneksi ke instance BlueStacks.

Port ADB BlueStacks tidak tetap: tiap instance punya port sendiri dan
berubah kalau instance di-restart atau berganti. Modul ini menemukan
port yang sedang hidup, jadi script lain tidak perlu menghardcode angka.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import uiautomator2 as u2
import uiautomator2.base

# Bawaan uiautomator2 300 detik: kalau agen di device mati, tiap pembacaan
# layar menggantung 5 menit dan bot tampak diam tanpa penjelasan.
BATAS_HTTP = 60
uiautomator2.base.HTTP_TIMEOUT = BATAS_HTTP

ADB = Path(r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe")
CONF = Path(r"C:\ProgramData\BlueStacks_nxt\bluestacks.conf")
PAKET = "id.go.bpsfasih"


def _port_terdaftar() -> list[int]:
    """Semua port ADB yang terdaftar di bluestacks.conf."""
    if not CONF.exists():
        return []
    teks = CONF.read_text(encoding="utf-8", errors="ignore")
    port = re.findall(r'adb_port="(\d+)"', teks)
    return sorted({int(p) for p in port})


def _port_mendengar(kandidat: list[int]) -> list[int]:
    """Saring kandidat ke port yang benar-benar sedang LISTENING."""
    try:
        out = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True, text=True, timeout=20,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return kandidat
    hidup = {
        int(m) for m in re.findall(r"127\.0\.0\.1:(\d+)\s+\S+\s+LISTENING", out)
    }
    return [p for p in kandidat if p in hidup]


def _adb(*args: str) -> str:
    return subprocess.run(
        [str(ADB), *args], capture_output=True, text=True, timeout=30
    ).stdout


def daftar_perangkat() -> list[str]:
    """Semua serial BlueStacks yang hidup dan bisa dihubungi ADB."""
    port = _port_mendengar(_port_terdaftar())
    if not port:
        raise RuntimeError(
            "Tidak ada instance BlueStacks yang mendengarkan di port ADB. "
            "Pastikan instance sudah jalan dan ADB aktif di Settings > Advanced."
        )

    siap = []
    for p in port:
        serial = f"127.0.0.1:{p}"
        _adb("connect", serial)
        if re.search(rf"{re.escape(serial)}\s+device\b", _adb("devices")):
            siap.append(serial)

    if not siap:
        raise RuntimeError(
            f"Port {port} terbuka tapi ADB menolak koneksi. "
            "Coba matikan lalu nyalakan ulang ADB di pengaturan BlueStacks."
        )
    return siap


def cari_serial(pilih: str | None = None) -> str:
    """Tentukan instance mana yang dipakai.

    Kalau ada lebih dari satu instance hidup dan tidak disebutkan yang mana,
    fungsi ini menolak memilih sendiri. Menebak berbahaya: run bisa mendarat
    di instance yang salah dan meng-approve wilayah yang bukan targetnya.
    """
    tersedia = daftar_perangkat()

    if pilih:
        target = pilih if ":" in pilih else f"127.0.0.1:{pilih}"
        if target not in tersedia:
            raise RuntimeError(
                f"Perangkat {target} tidak siap. Yang tersedia: {tersedia}"
            )
        return target

    if len(tersedia) > 1:
        raise RuntimeError(
            f"Ada {len(tersedia)} instance aktif: {tersedia}. "
            "Sebutkan yang mana dengan --perangkat <port>, "
            f"misalnya --perangkat {tersedia[0].split(':')[1]}"
        )
    return tersedia[0]


def hubungkan(pilih: str | None = None) -> u2.Device:
    """Sambungkan uiautomator2 ke satu instance BlueStacks."""
    serial = cari_serial(pilih)
    d = u2.connect(serial)
    d.settings["wait_timeout"] = 20.0
    print(f"[perangkat] tersambung ke {serial}")
    return d
