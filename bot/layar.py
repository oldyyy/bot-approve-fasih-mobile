"""Pembacaan layar Daftar Assignment FASIH.

Isi layar ini adalah tabel DataTables di dalam WebView. Konten web-nya
terbaca sebagai node `android.view.View` bertext, tapi tanpa resource-id,
jadi semua penelusuran dilakukan lewat teks dan koordinat bounds.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass

BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
# Prefiks '+' / '-' adalah kontrol expand DataTables Responsive. Kontrol ini
# bukan node tersendiri, melainkan menyatu dengan teks nama di sel pertama.
BARIS_RE = re.compile(r"^([+-]) (\S.*)$")
# Lebar kira-kira glyph kontrol di tepi kiri sel.
OFFSET_KONTROL_X = 16


@dataclass(frozen=True)
class Baris:
    """Satu baris data pada tabel assignment."""

    nama: str
    terbentang: bool
    bounds: tuple[int, int, int, int]
    nomor: str = ""
    status: str = ""
    sel: tuple[str, ...] = ()   # seluruh sel baris, urut kiri->kanan

    @property
    def titik_kontrol(self) -> tuple[int, int]:
        """Koordinat tap untuk membentangkan/menutup baris."""
        x1, y1, _, y2 = self.bounds
        return x1 + OFFSET_KONTROL_X, (y1 + y2) // 2

    @property
    def kunci(self) -> str:
        """Penanda baris yang dipakai bot untuk mengenalinya kembali.

        Nama saja tidak cukup: banyak assignment bernama sama persis
        ("BANGUNAN KOSONG", "KAMAR KOSONG"). Pembedanya diambil dari kolom
        lain pada baris yang sama - lihat `_pembeda_baris` untuk alasan
        mengapa kolomnya tidak dihardcode.
        """
        return f"{self.nama}│{self.nomor}"

    @property
    def label(self) -> str:
        """Bentuk yang enak dibaca manusia di log."""
        return f"{self.nama!r} [{self.nomor or '-'}]"


# Awalan nilai kolom status. Isinya berubah setelah assignment diproses,
# jadi kolom seperti ini tidak boleh masuk pembeda baris.
AWALAN_STATUS = ("submitted", "approved", "rejected", "open")


def _status_baris(sel: list[str]) -> str:
    """Ambil nilai status dari sel-sel baris, kalau tabelnya punya kolom itu.

    Tabel Sakernas menaruh Status sebagai kolom tabel, sedangkan tabel SE2026
    hanya menampilkannya di dalam baris terbentang. Keduanya harus terbaca.
    """
    for teks in sel:
        if teks.casefold().startswith(AWALAN_STATUS):
            return teks
    return ""


def _pembeda_baris(sel: list[str]) -> str:
    """Rangkai pembeda baris dari kolom-kolom selain nama.

    Kolomnya tidak dihardcode karena tiap survei punya susunan sendiri:
    di SE2026 kolom ketiga adalah "Nomor Urut Bangunan / IDSBR" yang unik,
    tapi di Sakernas kolom ketiga adalah "PMM" yang isinya cuma 0 atau 1.
    Kolom status sengaja dikecualikan: nilainya berubah setelah assignment
    diproses, dan pembeda yang ikut berubah membuat baris yang sama terbaca
    sebagai baris baru.
    """
    bagian = [t for t in sel if not t.casefold().startswith(AWALAN_STATUS)]
    return "|".join(bagian)


def _bounds(node: ET.Element) -> tuple[int, int, int, int]:
    m = BOUNDS_RE.match(node.get("bounds", ""))
    return tuple(int(g) for g in m.groups()) if m else (0, 0, 0, 0)


def pohon(d, percobaan: int = 2) -> ET.Element:
    """Baca accessibility tree, hidupkan ulang agen kalau pembacaan gagal.

    Agen uiautomator2 di device bisa mati sendiri di tengah run panjang.
    Tanpa pemulihan ini, satu kematian agen menghentikan seluruh sisa run.
    """
    galat: Exception | None = None
    for ke in range(percobaan):
        try:
            return ET.fromstring(d.dump_hierarchy())
        except Exception as e:  # noqa: BLE001 - apa pun sebabnya, coba pulihkan
            galat = e
            if ke + 1 >= percobaan:
                break
            try:
                d.stop_uiautomator()
                time.sleep(2)
                d.start_uiautomator()
                time.sleep(3)
            except Exception:  # noqa: BLE001 - kegagalan pulih dilaporkan di bawah
                pass
    raise RuntimeError(
        f"Gagal membaca layar setelah {percobaan} percobaan: {galat}"
    )


def id_cocok(rid: str, nama: str) -> bool:
    """Cocokkan resource-id, baik bentuk WebView maupun Android native.

    Elemen di dalam WebView memakai id HTML mentah ("wilayah1"), sedangkan
    View native memakai bentuk berprefiks paket ("id.go.bpsfasih:id/menu").
    """
    return rid == nama or rid.endswith(f":id/{nama}")


def cari_id(root: ET.Element, nama: str):
    """Cari node berdasarkan resource-id; kembalikan (node, bounds) atau None."""
    for node in root.iter("node"):
        if id_cocok(node.get("resource-id", ""), nama):
            return node, _bounds(node)
    return None


def baca_status_filter(root: ET.Element) -> dict[str, str]:
    """Ambil penanda wilayah/filter/sortir yang tampil di header layar."""
    hasil = {}
    for node in root.iter("node"):
        rid = node.get("resource-id", "")
        for kunci in ("wilayah1", "filtered", "sorted", "example_info"):
            if id_cocok(rid, kunci):
                hasil[kunci] = node.get("text", "")
    return hasil


HEADER_RE = re.compile(
    r"^(.*): activate to sort column (?:ascending|descending)$")


def kolom_tabel(root: ET.Element) -> list[str]:
    """Nama kolom tabel, urut kiri ke kanan, dibaca dari baris header.

    Indeks kolom tidak boleh dihardcode: tiap survei punya susunan sendiri.
    DataTables menyisipkan keterangan ": activate to sort column ..." pada
    tiap header, dan itu dipakai di sini untuk mengenalinya.
    """
    ketemu = []
    for node in root.iter("node"):
        m = HEADER_RE.match((node.get("text") or "").strip())
        if m:
            ketemu.append((_bounds(node)[0], m.group(1).strip()))

    urut: list[str] = []
    for _, nama in sorted(ketemu):
        if nama not in urut:
            urut.append(nama)
    return urut


def nilai_kolom(root: ET.Element, baris: Baris, nama_kolom: str) -> str | None:
    """Isi satu kolom pada sebuah baris, dicari lewat nama kolomnya.

    Kembalikan None kalau kolomnya tidak ada di tabel ini - pemanggil yang
    memutuskan apakah itu berarti gagal.
    """
    kolom = kolom_tabel(root)
    if nama_kolom not in kolom:
        return None
    i = kolom.index(nama_kolom)
    return baris.sel[i] if i < len(baris.sel) else None


def baris_terlihat(root: ET.Element) -> list[Baris]:
    """Semua baris data yang sedang terlihat, urut dari atas.

    Regex prefiks saja tidak cukup: kolom "Nomor Urut Bangunan / IDSBR"
    berisi nilai seperti "- / 43974516" yang juga diawali tanda dan spasi.
    Pembedanya struktural - sel nama selalu anak pertama (index="0") dari
    wadah barisnya, sedangkan kolom IDSBR berada di index="2".
    """
    out = []
    for wadah in root.iter("node"):
        anak = list(wadah)
        if not anak or anak[0].get("index") != "0":
            continue
        m = BARIS_RE.match(anak[0].get("text", ""))
        if not m:
            continue
        tanda, nama = m.groups()
        semua = [(k.get("text") or "").strip() for k in anak]
        sel = semua[1:]
        out.append(Baris(nama, tanda == "-", _bounds(anak[0]),
                         _pembeda_baris(sel), _status_baris(sel),
                         tuple(semua)))
    out.sort(key=lambda b: b.bounds[1])
    return out


def cari_teks(root: ET.Element, teks: str, harus_clickable: bool = False):
    """Cari node dengan teks tepat sama; kembalikan (node, bounds) atau None."""
    for node in root.iter("node"):
        if node.get("text", "") != teks:
            continue
        if harus_clickable and node.get("clickable") != "true":
            continue
        return node, _bounds(node)
    return None


def normalisasi(teks: str) -> str:
    """Bentuk baku sebuah label untuk dicocokkan.

    Dua hal membuat perbandingan mentah gagal di FASIH: kapitalisasi tidak
    konsisten ("BUKA" vs "Buka"), dan sebagian tombol dirender dengan spasi
    di antara tiap huruf ("A P P R O V E"). Keduanya diratakan di sini
    dengan membuang seluruh spasi lalu menyamakan huruf.
    """
    return "".join((teks or "").split()).casefold()


def cari_kelas(root: ET.Element, kelas: str):
    """Cari node pertama dengan class tertentu; kembalikan (node, bounds)."""
    for node in root.iter("node"):
        if node.get("class") == kelas:
            return node, _bounds(node)
    return None


def cari_teks_mana_saja(root: ET.Element, kandidat: list[str],
                        harus_clickable: bool = False):
    """Cari node yang labelnya sama dengan salah satu kandidat.

    Pencocokan tetap ketat - harus sama persis setelah dinormalisasi, bukan
    sekadar mengandung - supaya "A P P R O V E" cocok tapi "Approve All"
    tidak.
    """
    incar = {normalisasi(k) for k in kandidat}
    for node in root.iter("node"):
        if normalisasi(node.get("text", "")) not in incar:
            continue
        if harus_clickable and node.get("clickable") != "true":
            continue
        return node, _bounds(node)
    return None


def titik_tengah(bounds: tuple[int, int, int, int]) -> tuple[int, int]:
    x1, y1, x2, y2 = bounds
    return (x1 + x2) // 2, (y1 + y2) // 2


def baca_radiogroup(root: ET.Element, prefiks: str) -> tuple[str | None, dict[str, tuple[int, int, int, int]]]:
    """Baca radiogroup FormGear: (label terpilih, {label: bounds tombol}).

    FormGear tidak mengekspos atribut `checked` sama sekali - semua item
    selalu checked=false. Yang membedakan: item yang aktif punya anak
    bernama `<item>-indicator` (titik di tengah radio), sedangkan item
    yang tidak aktif tidak punya node itu. Itulah satu-satunya penanda
    pilihan yang terbaca dari accessibility tree.
    """
    # Kumpulkan node per item: prefiks-item-cl-NN -> {suffix: node}
    item: dict[str, dict[str, ET.Element]] = {}
    for node in root.iter("node"):
        rid = node.get("resource-id", "")
        if not rid.startswith(f"{prefiks}-item-"):
            continue
        sisa = rid[len(prefiks) + 6:]  # buang "<prefiks>-item-"
        bagian = sisa.split("-")
        kunci = "-".join(bagian[:2])          # mis. "cl-14"
        suffix = "-".join(bagian[2:]) or ""   # mis. "input" / "indicator" / ""
        item.setdefault(kunci, {})[suffix] = node

    terpilih = None
    tombol: dict[str, tuple[int, int, int, int]] = {}
    for kunci, bagian in item.items():
        # Catatan: Element tanpa anak bersifat falsy di ElementTree, jadi
        # pemilihan node WAJIB pakai `is not None`, bukan `or`.
        label_node = bagian.get("label")
        if label_node is None:
            label_node = bagian.get("input")
        if label_node is None:
            continue
        label = (label_node.get("text") or "").strip()
        if not label:
            continue
        # `control` adalah target tap berukuran wajar (~25x26 px); `input`
        # hanya 3x5 px dan enabled=false, jadi jangan pernah jadi target.
        target = bagian.get("control")
        if target is None:
            target = label_node
        tombol[label] = _bounds(target)
        if "indicator" in bagian:
            terpilih = label
    return terpilih, tombol


def ringkas_layar(root: ET.Element) -> list[str]:
    """Daftar teks yang terlihat, untuk pemetaan dan logging."""
    out = []
    for node in root.iter("node"):
        teks = (node.get("text") or "").strip()
        desc = (node.get("content-desc") or "").strip()
        rid = node.get("resource-id", "")
        if rid.startswith("com.android.systemui"):
            continue
        label = teks or (f"[desc] {desc}" if desc else "")
        if not label:
            continue
        tanda = " *" if node.get("clickable") == "true" else ""
        out.append(f"{label}{tanda}")
    return out
