"""Pembacaan warna baris lewat tangkapan jendela BlueStacks di sisi Windows.

Warna tidak ada di accessibility tree, dan screencap Android pada konfigurasi
ini selalu menghasilkan gambar hitam. Jalan yang tersisa adalah menangkap
jendela BlueStacks sebagai jendela Windows biasa, lalu memetakan koordinat
Android ke koordinat jendela.
"""

from __future__ import annotations

import ctypes
import re
from ctypes import wintypes
from pathlib import Path

from PIL import Image

CONF = Path(r"C:\ProgramData\BlueStacks_nxt\bluestacks.conf")
LEBAR_ANDROID = 900
TINGGI_ANDROID = 1600

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


class GagalTangkap(RuntimeError):
    """Jendela tidak bisa ditangkap atau tidak bisa dikalibrasi."""


def nama_instance(serial: str) -> str | None:
    """Nama tampilan instance untuk sebuah port ADB, dari bluestacks.conf.

    Tiap instance punya dua entri port - `adb_port` dan `status.adb_port` -
    dan koneksi bisa memakai salah satunya, jadi keduanya dicocokkan.
    """
    port = serial.rsplit(":", 1)[-1]
    if not CONF.exists():
        return None
    teks = CONF.read_text(encoding="utf-8", errors="ignore")
    for inst in set(re.findall(r"bst\.instance\.([^.]+)\.(?:status\.)?adb_port", teks)):
        pola = (rf'bst\.instance\.{re.escape(inst)}\.(?:status\.)?adb_port'
                rf'="{port}"')
        if not re.search(pola, teks):
            continue
        nama = re.search(
            rf'bst\.instance\.{re.escape(inst)}\.display_name="([^"]*)"', teks)
        return nama.group(1) if nama else None
    return None


def cari_jendela(judul: str) -> int:
    """Handle jendela BlueStacks berdasarkan judulnya (nama instance)."""
    hasil = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def per_jendela(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        panjang = user32.GetWindowTextLengthW(hwnd)
        if not panjang:
            return True
        buf = ctypes.create_unicode_buffer(panjang + 1)
        user32.GetWindowTextW(hwnd, buf, panjang + 1)
        if buf.value == judul:
            hasil.append(hwnd)
        return True

    user32.EnumWindows(per_jendela, 0)
    if not hasil:
        raise GagalTangkap(
            f"Jendela BlueStacks berjudul {judul!r} tidak ditemukan. "
            "Pastikan instance-nya terbuka dan tidak diminimalkan."
        )
    return hasil[0]


def tangkap(hwnd: int) -> Image.Image:
    """Ambil gambar area klien jendela.

    PrintWindow dipakai lebih dulu karena bisa menangkap jendela yang
    tertutup jendela lain; kalau hasilnya kosong, disalin dari layar.
    """
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w <= 0 or h <= 0:
        raise GagalTangkap("Ukuran area klien tidak valid (jendela diminimalkan?).")

    hdc = user32.GetDC(hwnd)
    memdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(memdc, bmp)

    # 2 = PW_RENDERFULLCONTENT, wajib untuk jendela ber-akselerasi.
    user32.PrintWindow(hwnd, memdc, 2)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth, bi.biHeight = w, -h      # negatif = baris atas lebih dulu
    bi.biPlanes, bi.biBitCount = 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(memdc, bmp, 0, h, buf, ctypes.byref(bi), 0)

    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(hwnd, hdc)

    return Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1)


def _gelap(piksel) -> bool:
    return sum(piksel[:3]) < 200


def kalibrasi(img: Image.Image) -> tuple[float, int]:
    """Cari (skala, offset_y) pemetaan koordinat Android ke jendela.

    Area Android menempel di tepi kiri jendela; sisi kanan ditempati bilah
    alat BlueStacks yang berwarna gelap. Lebar area Android dicari dari batas
    itu, lalu tingginya mengikuti rasio layar Android sehingga offset atas
    (tinggi bilah judul) bisa dihitung, bukan ditebak.
    """
    w, h = img.size
    px = img.load()

    # Bilah samping memuat banyak ikon terang, jadi satu piksel per kolom
    # tidak cukup - yang dipakai proporsi piksel gelap sepanjang kolom.
    # Tepi jendela sendiri berupa garis terang, jadi yang dicari adalah tepi
    # kiri dari pita gelap paling kanan, bukan kolom gelap pertama.
    contoh_y = list(range(h // 5, 4 * h // 5, max(1, h // 40)))

    def kolom_gelap(x: int) -> bool:
        return sum(_gelap(px[x, y]) for y in contoh_y) >= 0.7 * len(contoh_y)

    x = w - 1
    while x > w // 2 and not kolom_gelap(x):
        x -= 1                      # lewati garis tepi jendela
    if x <= w // 2:
        raise GagalTangkap("Bilah samping BlueStacks tidak terdeteksi.")
    while x > w // 2 and kolom_gelap(x):
        x -= 1                      # susuri pita gelap sampai habis
    lebar = x + 1
    skala = lebar / LEBAR_ANDROID
    offset_y = round(h - TINGGI_ANDROID * skala)
    if not (0 <= offset_y < h // 2):
        raise GagalTangkap(
            f"Kalibrasi tidak masuk akal (skala={skala:.3f}, offset_y={offset_y}). "
            "Ubah ukuran jendela BlueStacks lalu coba lagi."
        )
    return skala, offset_y


def warna_di(img: Image.Image, skala: float, offset_y: int,
             bounds: tuple[int, int, int, int]) -> tuple[int, int, int]:
    """Warna dominan pada area Android tertentu, dibaca dari tangkapan."""
    x1, y1, x2, y2 = bounds
    px = img.load()
    w, h = img.size

    hitung: dict[tuple[int, int, int], int] = {}
    for i in range(1, 8):
        for j in range(1, 8):
            ax = x1 + (x2 - x1) * i / 8
            ay = y1 + (y2 - y1) * j / 8
            wx, wy = int(ax * skala), int(ay * skala + offset_y)
            if 0 <= wx < w and 0 <= wy < h:
                c = px[wx, wy][:3]
                hitung[c] = hitung.get(c, 0) + 1
    if not hitung:
        raise GagalTangkap(f"Area {bounds} berada di luar tangkapan jendela.")
    return max(hitung, key=hitung.get)


def klasifikasi(rgb: tuple[int, int, int]) -> str:
    """Kelompokkan warna baris menjadi nama yang dipakai alur.

    Urutan pemeriksaan menentukan: kuning (255,209,102) juga berkomponen
    merah tinggi, jadi ia harus diuji sebelum merah (239,71,111) agar baris
    Draft tidak terbaca sebagai Reject.
    """
    r, g, b = rgb
    if g > 120 and g > r + 40 and g > b + 20:
        return "hijau"          # Approve
    if b > 120 and b > r + 40 and b > g + 10:
        return "biru"           # Submit
    if r > 200 and g > 150 and b < 150:
        return "kuning"         # Draft
    if r > 150 and r > g + 80 and r > b + 80:
        return "merah"          # Reject
    if r > 200 and g > 200 and b > 200:
        return "putih"          # Open
    return f"lain{rgb}"
