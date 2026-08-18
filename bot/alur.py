"""Langkah-langkah alur bot di layar Daftar Assignment.

Semua fungsi di sini bersifat lokal: membentangkan dan menutup baris
DataTables tidak mengirim apa pun ke server, jadi aman dipakai untuk
memindai isi wilayah sebelum ada aksi sungguhan.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from bot import layar

FILTER_WAJIB = "Filter By Submit"
# Peran pada status berbeda antar survei ("BY Pencacah" / "BY PPL").
AWALAN_STATUS_LAYAK = "submitted"

# Dicocokkan sebagai awalan; lihat README bagian Catatan teknis.
KEBERADAAN_DITERIMA = (
    "0. Tidak Ditemukan",
    "3. Tutup",
    "3. Meninggal",
    "4. Ganda",
    "4. Tidak Eligible",
    "5. Tidak dapat ditemui sampai akhir pendataan",
)
SEKSI_TARGET = "SE2026 - P"

KODE_BANGUNAN_DITERIMA = (
    "6. Bangunan Lainnya yang Tidak Tercakup",
)
KATA_CARI_KOSONG = "kosong"

SEKSI_BLOK4 = "SE2026 - L BLOK IV"
SELISIH_ID = "selisih_pendapatan_pengeluaran_tampil"

PAKET_FASIH = "id.go.bpsfasih"
AKTIVITAS_DAFTAR = "AssignmentListActivity"
AKTIVITAS_FORM = "FormGearActivity"
AKTIVITAS_WILAYAH = "DaftarWilayahActivity"

# Checkbox status pada dialog Filter By Status. Hanya 'submit' yang boleh
# aktif; sisanya harus mati supaya daftar tidak bercampur status.
CHECKBOX_FILTER = {
    "open": "open_cb_bottomSheetFilterAssignment",
    "pernahDibuka": "pernahDibuka_cb_bottomSheetFilterAssignment",
    "submit": "submit_cb_bottomSheetFilterAssignment",
    "approve": "approve_cb_bottomSheetFilterAssignment",
    "reject": "reject_cb_bottomSheetFilterAssignment",
}

# Bertetangga langsung dengan tombol yang dituju bot: HAPUS di sebelah BUKA,
# REJECT di sebelah APPROVE.
TERLARANG = {
    layar.normalisasi(t) for t in (
        "HAPUS", "ASSIGN", "RESTORE", "PINDAH MODE",
        "SINKRONISASI ASSIGNMENT INI", "Tambah Assignment",
        "Tandai wilayah telah selesai", "REJECT",
    )
}

LBL_AKSI = ["Aksi"]
LBL_BUKA = ["BUKA", "Buka"]
LBL_YA = ["YA", "Ya"]
LBL_TIDAK = ["TIDAK", "Tidak"]
LBL_TERAPKAN = ["TERAPKAN", "Terapkan"]
LBL_FILTER_STATUS = ["Filter By Status"]
LBL_SIDEBAR = ["sidebar-toggle"]
LBL_APPROVAL = ["APPROVAL", "Approval"]
LBL_APPROVE = ["APPROVE", "Approve"]
LBL_REJECT = ["REJECT", "Reject"]
LBL_UNAPPROVE = ["UNAPPROVE", "Unapprove"]

DIALOG_BUKA = "Anda akan membuka assignment ini?"
PROMPT_APPROVE = "Apa yang Anda ingin lakukan untuk assignment ini ?"

# Dialog keluar punya beberapa varian teks; hanya pertanyaan intinya yang
# muncul di semua varian.
PETUNJUK_DIALOG_KELUAR = ("yakin akan keluar dari halaman ini",)

# Muncul kadang-kadang saat membuka assignment yang versi datanya berbeda
# antara lokal dan server. Hanya punya satu tombol.
PETUNJUK_DIALOG_VERSI = ("versi data lokal", "versi data server")
LBL_BUKA_ASSIGNMENT = ["BUKA ASSIGNMENT"]
LBL_IYA = ["IYA"]   # dialog ini memakai "IYA", bukan "YA" seperti yang lain

# Jangan tidur selama durasi tetap kalau yang ditunggu bisa dideteksi.
JEDA_POLL = 0.3
JEDA_TAP = 0.25

# Jarak gestur 1000 px -> geseran nyata ~1205 px karena inertial scroll.
# Harus tetap di bawah tinggi viewport (1600) agar elemen pendek tidak
# terlewati; angka pengukurannya ada di README.
GESER_ATAS_Y = 400
GESER_BAWAH_Y = 1400
GESER_DURASI = 0.2
JEDA_GESER = 0.15


def geser_turun(d) -> None:
    """Gulir isi layar ke bawah (jari dari bawah ke atas)."""
    d.swipe(450, GESER_BAWAH_Y, 450, GESER_ATAS_Y, duration=GESER_DURASI)
    time.sleep(JEDA_GESER)


def geser_naik(d) -> None:
    """Gulir isi layar ke atas (jari dari atas ke bawah)."""
    d.swipe(450, GESER_ATAS_Y, 450, GESER_BAWAH_Y, duration=GESER_DURASI)
    time.sleep(JEDA_GESER)


# Durasi panjang = nyaris tanpa inertia; presisi di atas kecepatan.
GESER_HALUS = 300
GESER_HALUS_DURASI = 0.5


def geser_halus(d, turun: bool = True) -> None:
    y1, y2 = (GESER_ATAS_Y + GESER_HALUS, GESER_ATAS_Y)
    if not turun:
        y1, y2 = y2, y1
    d.swipe(450, y1, 450, y2, duration=GESER_HALUS_DURASI)
    time.sleep(JEDA_GESER)


# Label dan nilai menempel tanpa pemisah ("StatusSUBMITTED BY Pencacah").
# Urut dari terpanjang agar label pendek tidak menang duluan.
LABEL = [
    "Skala Usaha / Jenis Prelist",
    "IDSBR UMKM SLS Sama",
    "Jumlah Usaha",
    "Perubahan SLS",
    "User saat ini",
    "Kode Pos",
    "Status",
    "Mode",
]


@dataclass
class HasilBaris:
    nama: str
    nomor: str = ""
    detail: dict[str, str] = field(default_factory=dict)
    catatan: list[str] = field(default_factory=list)

    @property
    def kunci(self) -> str:
        return f"{self.nama}│{self.nomor}"

    @property
    def label(self) -> str:
        return f"{self.nama!r} [{self.nomor or '-'}]"

    @property
    def status(self) -> str:
        return self.detail.get("Status", "")

    @property
    def layak(self) -> bool:
        return self.status.casefold().startswith(AWALAN_STATUS_LAYAK)


class AlurGagal(RuntimeError):
    """Kondisi yang membuat bot harus berhenti, bukan menebak.

    `hasil` diisi kalau kegagalan terjadi setelah assignment terlanjur
    dibuka, supaya baris yang terlantar tetap masuk laporan akhir dan tidak
    hanya tersirat di log.
    """

    def __init__(self, pesan: str, hasil: "HasilBaris | None" = None):
        super().__init__(pesan)
        self.hasil = hasil


class SyaratTakLolos(AlurGagal):
    """Baris tidak memenuhi syarat kolom.

    Diperiksa sebelum apa pun dibuka, jadi baris ini sama sekali belum
    tersentuh - aman untuk dilewati maupun dijadikan alasan berhenti,
    tergantung kebutuhan alurnya.
    """


class NilaiTakSesuai(AlurGagal):
    """Isi kuesioner terbaca, tapi nilainya di luar daftar yang diterima.

    Dibedakan dari kegagalan teknis: di sini datanya jelas, hanya tidak
    memenuhi syarat - jadi assignment-nya di-reject. Kegagalan membaca layar
    tidak boleh diperlakukan sama, karena datanya belum tentu salah.
    """


class DaftarHabis(AlurGagal):
    """Tidak ada lagi baris yang perlu diproses.

    Ini akhir yang normal, bukan kegagalan - dibedakan supaya run tanpa
    batas putaran bisa berhenti sendiri tanpa dilaporkan sebagai error.
    """


def periksa_prasyarat(root: ET.Element) -> dict[str, str]:
    """Pastikan layar benar dan filter sudah diterapkan.

    Tanpa filter 'Filter By Submit', daftar berisi assignment dengan status
    campur - bot tidak boleh bekerja di daftar seperti itu.
    """
    status = layar.baca_status_filter(root)
    if "wilayah1" not in status:
        raise AlurGagal(
            "Bukan layar Daftar Assignment (penanda 'wilayah1' tidak ada)."
        )
    if status.get("filtered") != FILTER_WAJIB:
        raise AlurGagal(
            f"Filter di layar {status.get('filtered')!r}, harus {FILTER_WAJIB!r}. "
            "Terapkan filter dulu lewat FAB > Filter By Status > Submit > Terapkan."
        )
    return status


def baca_detail(root: ET.Element) -> dict[str, str]:
    """Ambil field detail dari baris yang sedang terbentang."""
    hasil: dict[str, str] = {}
    for node in root.iter("node"):
        teks = (node.get("text") or "").strip()
        if not teks:
            continue
        # Header kolom kalau tidak disaring terbaca sebagai nilai Status.
        if "activate to sort" in teks:
            continue
        for label in LABEL:
            if teks.startswith(label) and len(teks) > len(label):
                nilai = teks[len(label):].strip()
                # Node gabungan seluruh detail juga diawali label yang sama;
                # abaikan yang jelas terlalu panjang untuk sebuah nilai.
                if nilai and len(nilai) < 60 and label not in hasil:
                    hasil[label] = nilai
                break
    return hasil


def _cari(d, kunci: str) -> layar.Baris | None:
    """Temukan kembali satu baris berdasarkan kunci majemuknya.

    Pencarian lewat nama saja pernah salah sasaran, karena banyak baris
    bernama identik dan yang ketemu belum tentu yang dimaksud.
    """
    for b in layar.baris_terlihat(layar.pohon(d)):
        if b.kunci == kunci:
            return b
    return None


def _tunggu_baris_diam(d, kunci: str, batas: float = 6.0) -> layar.Baris | None:
    """Tunggu sampai posisi baris berhenti berubah.

    Mengetuk saat daftar masih beranimasi - misalnya bounce setelah digulir
    ke puncak - membuat ketukan mendarat di tempat yang salah walau bounds
    yang dibaca sudah benar pada saat itu. Jadi posisinya dipastikan sama
    pada dua pembacaan berurutan sebelum diketuk.
    """
    sebelum = None
    tenggat = time.monotonic() + batas
    while time.monotonic() < tenggat:
        b = _cari(d, kunci)
        if b is not None and b.bounds == sebelum:
            return b
        sebelum = b.bounds if b is not None else None
        time.sleep(JEDA_POLL)
    return _cari(d, kunci)


def set_bentang(d, kunci: str, mau_terbentang: bool, batas: float = 12.0) -> ET.Element:
    """Buka atau tutup satu baris, lalu kembalikan pohon layar terbaru.

    Prefiks '+'/'-' pada teks sel dipakai untuk memverifikasi hasil tap,
    jadi tap yang gagal terdeteksi alih-alih diam-diam terlewat. Hasilnya
    diselidiki berulang, bukan ditunggu selama durasi tetap: baris biasanya
    membentang dalam ratusan milidetik.
    """
    b = _tunggu_baris_diam(d, kunci)
    if b is None:
        raise AlurGagal(f"Baris {kunci!r} tidak ada di layar.")
    if b.terbentang == mau_terbentang:
        return layar.pohon(d)

    d.click(*b.titik_kontrol)
    time.sleep(JEDA_TAP)

    tenggat = time.monotonic() + batas
    while True:
        sesudah = _cari(d, kunci)
        if sesudah is not None and sesudah.terbentang == mau_terbentang:
            return layar.pohon(d)
        if time.monotonic() >= tenggat:
            kata = "terbentang" if mau_terbentang else "tertutup"
            if sesudah is None:
                raise AlurGagal(f"Baris {kunci!r} hilang setelah tap kontrol.")
            raise AlurGagal(f"Baris {kunci!r} gagal {kata} dalam {batas:.0f} detik.")
        time.sleep(JEDA_POLL)


def geser_ke_atas(d, maks: int = 5) -> None:
    """Gulir ke puncak daftar, berhenti begitu sudah sampai.

    Setelah filter diterapkan daftar biasanya sudah di puncak, jadi usapan
    dengan jumlah tetap hanya membuang waktu tiap putaran. Puncak dikenali
    dari baris teratas yang tidak berubah lagi setelah diusap.
    """
    sebelum = None
    for _ in range(maks):
        baris = layar.baris_terlihat(layar.pohon(d))
        teratas = baris[0].nama if baris else None
        if teratas is not None and teratas == sebelum:
            return
        sebelum = teratas
        geser_naik(d)


def _aktivitas(d) -> str:
    return d.app_current().get("activity", "")


def tunggu_teks(d, kandidat: list[str], batas: float = 30.0,
                jeda: float = JEDA_POLL, clickable: bool = False):
    """Tunggu sampai salah satu label muncul; kembalikan (pohon, node, bounds).

    Dipakai menggantikan sleep tetap, karena WebView FASIH memuat isinya
    secara asinkron dan lamanya tidak bisa diprediksi.
    """
    tenggat = time.monotonic() + batas
    while True:
        root = layar.pohon(d)
        hit = layar.cari_teks_mana_saja(root, kandidat, harus_clickable=clickable)
        if hit is not None:
            return root, hit[0], hit[1]
        if time.monotonic() >= tenggat:
            raise AlurGagal(
                f"Label {kandidat} tidak muncul dalam {batas:.0f} detik."
            )
        time.sleep(jeda)


def tap_label(d, kandidat: list[str], batas: float = 30.0,
              jeda_sesudah: float = JEDA_TAP, clickable: bool = True,
              izinkan: tuple[str, ...] = ()) -> None:
    """Tap label berdasarkan pencocokan teks persis, dengan pengaman.

    Tidak pernah memakai koordinat hasil offset atau urutan indeks: kalau
    labelnya tidak ada, bot berhenti alih-alih menebak. Ini yang menjaga
    'HAPUS' tidak pernah tertekan karena letaknya bertetangga dengan 'BUKA'.

    `izinkan` membuka satu label dari daftar terlarang khusus untuk panggilan
    ini. Dipakai hanya oleh alur yang memang harus menekan REJECT, sehingga
    tombol itu tetap terlarang di semua alur lain.
    """
    boleh = {layar.normalisasi(k) for k in izinkan}
    try:
        _, node, bounds = tunggu_teks(d, kandidat, batas=batas, clickable=clickable)
    except AlurGagal:
        if not clickable:
            raise
        # Sebagian label FASIH tidak ditandai clickable walau bisa ditekan.
        _, node, bounds = tunggu_teks(d, kandidat, batas=5.0, clickable=False)

    teks = (node.get("text") or "").strip()
    if layar.normalisasi(teks) in TERLARANG and layar.normalisasi(teks) not in boleh:
        raise AlurGagal(f"Menolak menekan item terlarang {teks!r}.")
    if layar.normalisasi(teks) not in {layar.normalisasi(k) for k in kandidat}:
        raise AlurGagal(f"Node target bertuliskan {teks!r}, di luar {kandidat}.")

    d.click(*layar.titik_tengah(bounds))
    time.sleep(jeda_sesudah)


def tunggu_id(d, rid: str, batas: float = 30.0, jeda: float = JEDA_POLL):
    """Tunggu sampai elemen ber-resource-id tertentu muncul."""
    tenggat = time.monotonic() + batas
    while True:
        hit = layar.cari_id(layar.pohon(d), rid)
        if hit is not None:
            return hit
        if time.monotonic() >= tenggat:
            raise AlurGagal(
                f"Elemen id={rid!r} tidak muncul dalam {batas:.0f} detik."
            )
        time.sleep(jeda)


def tap_id(d, rid: str, jeda_sesudah: float = JEDA_TAP, batas: float = 30.0) -> None:
    """Tap elemen ber-resource-id, menunggu dulu sampai elemennya ada.

    Menunggu itu wajib: sekembalinya dari FormGear, activity sudah berganti
    ke Daftar Assignment beberapa detik sebelum WebView-nya selesai render,
    jadi pembacaan seketika akan melihat layar kosong.
    """
    hit = tunggu_id(d, rid, batas=batas)
    d.click(*layar.titik_tengah(hit[1]))
    time.sleep(jeda_sesudah)


def tunggu_daftar_siap(d, batas: float = 75.0, jeda: float = 0.5,
                       wilayah: str | None = None) -> str:
    """Tunggu Daftar Assignment siap dipakai; kembalikan kode wilayahnya.

    Siap berarti activity-nya benar, FAB-nya ada, dan header wilayah sudah
    terisi - ketiganya baru lengkap setelah WebView selesai memuat. Kalau
    `wilayah` diberikan, kode di layar harus sama; berpindah wilayah di
    tengah run berarti ada yang tidak beres dan bot tidak boleh lanjut.
    """
    tenggat = time.monotonic() + batas
    # Berdiam di Daftar Wilayah berarti wilayahnya belum dibuka; jeda
    # singkat tetap diberi karena layar ini dilewati saat pemulihan.
    batas_wilayah = time.monotonic() + 10.0
    ke = 0
    while True:
        # Penanda wilayah ada di kepala halaman, jadi hilang saat daftar
        # tergulir - tanpa ini daftar sehat terbaca sebagai kosong.
        if ke and ke % 6 == 0:
            geser_naik(d)
        ke += 1
        kini = d.app_current()
        if kini.get("package") != PAKET_FASIH:
            raise AlurGagal(
                f"FASIH tidak sedang di depan (paket={kini.get('package')!r}). "
                "Buka aplikasinya dan masuk ke Daftar Assignment dulu."
            )
        if AKTIVITAS_WILAYAH in _aktivitas(d) and time.monotonic() >= batas_wilayah:
            raise AlurGagal(
                "Masih di Daftar Wilayah - wilayahnya belum dibuka."
            )
        if AKTIVITAS_DAFTAR in _aktivitas(d):
            root = layar.pohon(d)
            punya_fab = layar.cari_id(root, "expendable_fab") is not None
            kode = layar.baca_status_filter(root).get("wilayah1")
            if punya_fab and kode:
                if wilayah and kode != wilayah:
                    raise AlurGagal(
                        f"Wilayah di layar {kode!r}, padahal run ini terkunci "
                        f"pada {wilayah!r}. Bot berhenti agar tidak memproses "
                        "wilayah yang salah."
                    )
                return kode
        if time.monotonic() >= tenggat:
            # Layar benar tapi kosong = WebView gagal memuat, butuh
            # tindakan berbeda dari sekadar menunggu lebih lama.
            if AKTIVITAS_DAFTAR in _aktivitas(d):
                raise AlurGagal(
                    f"Layar Daftar Assignment terbuka tapi isinya kosong "
                    f"setelah {batas:.0f} detik - WebView gagal memuat."
                )
            raise AlurGagal(
                f"Daftar Assignment tidak siap dalam {batas:.0f} detik "
                f"(activity={_aktivitas(d)})."
            )
        time.sleep(jeda)


def buka_wilayah(d, kode: str, catat=print, batas: float = 60.0) -> None:
    """Dari Daftar Wilayah, buka wilayah dengan kode tertentu.

    Kartu wilayah dicari berdasarkan teks kodenya, digulir kalau perlu.
    """
    tenggat = time.monotonic() + batas
    while AKTIVITAS_WILAYAH not in _aktivitas(d):
        if time.monotonic() >= tenggat:
            raise AlurGagal(
                f"Tidak sampai ke Daftar Wilayah (activity={_aktivitas(d)})."
            )
        time.sleep(1.0)

    for _ in range(12):
        hit = layar.cari_teks(layar.pohon(d), kode)
        if hit is not None:
            catat(f"    buka ulang wilayah {kode}")
            d.click(*layar.titik_tengah(hit[1]))
            time.sleep(1.0)
            return
        geser_turun(d)

    raise AlurGagal(f"Kartu wilayah {kode!r} tidak ditemukan di Daftar Wilayah.")


def pastikan_daftar_siap(d, wilayah: str | None = None, catat=print) -> str:
    """Siapkan Daftar Assignment, pulihkan sendiri kalau isinya kosong.

    WebView daftar kadang gagal memuat dan tinggal kosong permanen -
    menunggu lebih lama tidak menolong. Yang menolong adalah keluar ke
    Daftar Wilayah lalu masuk lagi, dan itu hanya bisa dilakukan otomatis
    kalau kode wilayahnya sudah diketahui dari putaran sebelumnya.
    """
    try:
        return tunggu_daftar_siap(d, wilayah=wilayah)
    except AlurGagal as e:
        catat(f"    daftar belum siap ({e})")

    # Paling sering: masih tertinggal di kuesioner karena transisi lambat.
    if AKTIVITAS_FORM in _aktivitas(d):
        catat("    masih di kuesioner - keluar dulu")
        for _ in range(4):
            # Back memunculkan dialog konfirmasi keluar, dan back berikutnya
            # tidak menembusnya - dialog itu harus dijawab. IYA aman karena
            # bot tidak pernah mengubah isian. Berbeda dari keluar_kuesioner
            # yang sengaja menghentikan run: di sini konteksnya pemulihan
            # antar-nama, jadi setelah dijawab prosesnya dilanjutkan.
            if ada_dialog_keluar(layar.pohon(d)):
                catat("    dialog konfirmasi keluar - tap IYA")
                tap_label(d, LBL_IYA, batas=15.0)
            else:
                d.press("back")
            time.sleep(1.5)
            if AKTIVITAS_FORM not in _aktivitas(d):
                break
        try:
            return tunggu_daftar_siap(d, wilayah=wilayah)
        except AlurGagal as e:
            catat(f"    masih belum siap ({e})")

    if wilayah is None:
        raise AlurGagal(
            "Daftar Assignment tidak siap dan wilayahnya belum diketahui. "
            "Buka ulang wilayahnya di BlueStacks, lalu jalankan lagi."
        )

    # Satu kali back belum tentu sampai Daftar Wilayah.
    catat("    mencoba buka ulang wilayah")
    for _ in range(3):
        if AKTIVITAS_WILAYAH in _aktivitas(d):
            break
        d.press("back")
        time.sleep(1.5)
    buka_wilayah(d, wilayah, catat=catat)
    return tunggu_daftar_siap(d, wilayah=wilayah)


def terapkan_filter_submit(d, catat=print, wilayah: str | None = None) -> dict[str, str]:
    """Pastikan daftar tersaring tepat 'Filter By Submit'.

    Checkbox filter adalah View native, jadi atribut `checked`-nya benar-benar
    terbaca. Hanya checkbox yang keadaannya salah yang ditekan: kalau Submit
    sudah menyala dan lainnya mati, fungsi ini langsung menekan TERAPKAN.
    """
    pastikan_daftar_siap(d, wilayah=wilayah, catat=catat)
    root = layar.pohon(d)

    # Buka dialog filter kalau belum terbuka.
    if layar.cari_teks_mana_saja(root, LBL_TERAPKAN) is None:
        tap_id(d, "expendable_fab")
        tap_label(d, LBL_FILTER_STATUS)

    root = layar.pohon(d)
    perlu = []
    for nama, rid in CHECKBOX_FILTER.items():
        hit = layar.cari_id(root, rid)
        if hit is None:
            raise AlurGagal(f"Checkbox {nama!r} tidak ada di dialog filter.")
        aktif = hit[0].get("checked") == "true"
        harus = nama == "submit"
        if aktif != harus:
            perlu.append((nama, rid, harus))

    if not perlu:
        catat("    filter: Submit sudah benar, langsung TERAPKAN")
    for nama, rid, harus in perlu:
        catat(f"    filter: {'nyalakan' if harus else 'matikan'} {nama}")
        tap_id(d, rid)

    # Verifikasi ulang sebelum menerapkan, supaya tap yang gagal terdeteksi.
    root = layar.pohon(d)
    for nama, rid in CHECKBOX_FILTER.items():
        hit = layar.cari_id(root, rid)
        aktif = hit is not None and hit[0].get("checked") == "true"
        if aktif != (nama == "submit"):
            raise AlurGagal(f"Checkbox {nama!r} tidak berhasil diatur.")

    tap_label(d, LBL_TERAPKAN)

    # Tunggu penanda filter benar-benar berubah di layar, bukan menebak
    # lewat jeda tetap. Daftar kecil selesai jauh lebih cepat dari 3 detik.
    tenggat = time.monotonic() + 30
    while True:
        try:
            info = periksa_prasyarat(layar.pohon(d))
            break
        except AlurGagal:
            if time.monotonic() >= tenggat:
                raise
            time.sleep(JEDA_POLL)

    catat(f"    filter aktif: {info.get('filtered')} | wilayah {info.get('wilayah1')}")
    return info


KELAS_INPUT = "android.widget.EditText"


def pastikan_pencarian(d, kata: str, catat=print, batas: float = 20.0) -> int:
    """Pastikan kotak Search DataTables menyaring dengan `kata`.

    Kalau kotaknya sudah berisi kata itu - misalnya karena diisi manual
    sebelum bot dijalankan - tidak ada yang diketik ulang. Mengembalikan
    jumlah baris terlihat yang namanya memuat kata tersebut.
    """
    root = layar.pohon(d)
    hit = layar.cari_kelas(root, KELAS_INPUT)
    if hit is None:
        raise AlurGagal(
            "Kotak Search tidak ada di layar. Pastikan daftar assignment "
            "sudah termuat sepenuhnya."
        )

    node, bounds = hit
    isi = (node.get("text") or "").strip()
    if kata.casefold() in isi.casefold():
        catat(f"    search sudah berisi {isi!r}")
    else:
        catat(f"    mengisi search dengan {kata!r} (sebelumnya {isi!r})")
        d.click(*layar.titik_tengah(bounds))
        time.sleep(0.4)
        try:
            d(className=KELAS_INPUT).set_text(kata)
        except Exception:  # noqa: BLE001 - jalur cadangan kalau set_text gagal
            d.send_keys(kata, clear=True)

    # Tabel disaring secara asinkron, jadi ditunggu sampai hasilnya benar
    # benar mencerminkan kata kunci - bukan sekadar setelah jeda tetap.
    tenggat = time.monotonic() + batas
    while True:
        baris = layar.baris_terlihat(layar.pohon(d))
        cocok = [b for b in baris if kata.casefold() in b.nama.casefold()]
        if baris and len(cocok) == len(baris):
            catat(f"    hasil search: {len(cocok)} baris terlihat")
            return len(cocok)
        if time.monotonic() >= tenggat:
            if not baris:
                raise AlurGagal(
                    f"Search {kata!r} tidak menghasilkan baris apa pun."
                )
            raise AlurGagal(
                f"Search {kata!r} belum tersaring rapi: {len(cocok)} dari "
                f"{len(baris)} baris memuat kata itu. Contoh baris lain: "
                f"{[b.nama for b in baris if b not in cocok][:3]}"
            )
        time.sleep(JEDA_POLL)


def baris_pertama(d, lewati: set[str] | None = None) -> layar.Baris:
    """Baris teratas yang belum pernah dicoba pada run ini.

    Baris yang selesai di-approve memang keluar dari filter Submit, tapi
    baris yang gagal di tengah jalan ternyata bisa tetap bertahan di sana.
    Tanpa daftar-lewati, baris seperti itu akan terus terambil sebagai
    baris pertama dan run tidak pernah maju.
    """
    lewati = lewati or set()
    geser_ke_atas(d)

    for _ in range(6):
        for b in layar.baris_terlihat(layar.pohon(d)):
            if b.kunci not in lewati:
                return b
        geser_turun(d)

    raise DaftarHabis(
        "Tidak ada baris tersisa yang belum dicoba di daftar ini "
        f"({len(lewati)} baris sudah dicoba pada run ini)."
    )


def buka_kuesioner(d, nama: str, catat=print) -> None:
    """Aksi > BUKA > YA, lalu tunggu FormGear siap."""
    catat("    tap Aksi")
    tap_label(d, LBL_AKSI)
    catat("    tap BUKA")
    tap_label(d, LBL_BUKA)

    # Jumlah dan urutan dialog sesudah BUKA tidak tetap: konfirmasi biasa
    # selalu ada, sedangkan dialog "beda versi data" hanya muncul kadang.
    # Karena itu yang ditunggu adalah FormGear, dan dialog apa pun yang
    # menyela ditangani saat terlihat.
    batas = 90.0
    tenggat = time.monotonic() + batas
    sudah_konfirmasi = False
    while True:
        if AKTIVITAS_FORM in _aktivitas(d):
            catat("    FormGear terbuka")
            return

        root = layar.pohon(d)
        if ada_petunjuk(root, PETUNJUK_DIALOG_VERSI):
            catat("    dialog beda versi data - tap BUKA ASSIGNMENT")
            tap_label(d, LBL_BUKA_ASSIGNMENT, batas=15.0)
            continue
        if layar.cari_teks(root, DIALOG_BUKA) is not None:
            catat("    dialog terverifikasi, tap YA")
            tap_label(d, LBL_YA)
            sudah_konfirmasi = True
            continue

        if time.monotonic() >= tenggat:
            if not sudah_konfirmasi:
                raise AlurGagal(
                    f"Dialog konfirmasi {DIALOG_BUKA!r} tidak muncul dalam "
                    f"{batas:.0f} detik."
                )
            raise AlurGagal(f"FormGear tidak terbuka dalam {batas:.0f} detik.")
        time.sleep(JEDA_POLL)


def tunggu_kuesioner_siap(d, batas: float = 90.0) -> None:
    """Tunggu isi kuesioner selesai dirender, bukan hanya activity-nya.

    Alur yang tidak memeriksa apa pun mengetuk FAB approve segera setelah
    FormGear muncul - jauh lebih awal daripada alur yang sempat menavigasi
    seksi. Tanpa penantian ini, ketukan bisa mendahului form yang belum
    selesai memuat, dan layar approval tidak pernah tampil.
    """
    tenggat = time.monotonic() + batas
    while True:
        root = layar.pohon(d)
        siap = (layar.cari_id(root, "fasih-form-nav-next-button") is not None
                or layar.cari_teks_mana_saja(root, ["Ringkasan"]) is not None)
        if siap:
            return
        if time.monotonic() >= tenggat:
            raise AlurGagal(
                f"Isi kuesioner tidak selesai dirender dalam {batas:.0f} detik."
            )
        time.sleep(JEDA_POLL)


def ke_seksi_target(d, catat=print, seksi: str = SEKSI_TARGET) -> None:
    """sidebar-toggle > pilih seksi yang diminta."""
    root = layar.pohon(d)
    if layar.cari_teks(root, seksi) is not None:
        catat(f"    seksi {seksi} sudah tampil")
        return

    catat("    tap sidebar-toggle")
    tap_label(d, LBL_SIDEBAR, batas=60.0, clickable=False)
    catat(f"    pilih {seksi}")
    tap_label(d, [seksi], batas=30.0, clickable=False)

    # Siap = ada isian FormGear apa pun (radiogroup atau textfield).
    # Sambil menggulir karena isian sering di bawah lipatan layar.
    tenggat = time.monotonic() + 45
    ke = 0
    while True:
        if any(re.match(r"^(radiogroup|textfield|select|checkbox)-cl-\d+",
                        n.get("resource-id", ""))
               for n in layar.pohon(d).iter("node")):
            return
        if time.monotonic() >= tenggat:
            raise AlurGagal(
                f"Seksi {seksi} tidak memunculkan isian apa pun dalam 45 "
                "detik, termasuk setelah digulir."
            )
        # Dua pembacaan pertama tanpa menggulir - beri kesempatan seksinya
        # selesai memuat dulu sebelum posisinya diubah.
        if ke >= 2:
            geser_turun(d)
        ke += 1


def cocok_pilihan(nilai: str, diterima: tuple[str, ...]) -> bool:
    """Apakah `nilai` termasuk yang diterima, dicocokkan sebagai awalan.

    Label opsi FASIH sering memuat keterangan tambahan di belakang - misalnya
    "0. Tidak Ditemukan (STOP)" pada varian keluarga, atau "6. Bangunan
    Lainnya yang Tidak Tercakup (Tempat Judi, ...)". Mencocokkan awalan
    membuat daftar nilai yang diterima cukup memuat kode dan inti labelnya,
    tanpa harus menyalin keterangan dalam tanda kurung yang bisa berubah.
    """
    n = layar.normalisasi(nilai)
    return any(n.startswith(layar.normalisasi(k)) for k in diterima)


def _baca_soal_sekali(root: ET.Element,
                      diterima: tuple[str, ...]) -> tuple[str | None, list[str], str | None]:
    """Sekali baca: (prefiks grup, opsi yang terlihat, opsi terpilih).

    Grup yang dicari adalah yang memuat salah satu opsi pada `diterima`;
    itu yang membedakan satu pertanyaan dari pertanyaan lain di seksi sama.
    """
    prefiks = sorted({
        m.group(1)
        for n in root.iter("node")
        if (m := re.match(r"^(radiogroup-cl-\d+)-item-", n.get("resource-id", "")))
    })
    terlihat: list[str] = []
    for p in prefiks:
        terpilih, tombol = layar.baca_radiogroup(root, p)
        terlihat.extend(tombol)
        if any(cocok_pilihan(opsi, diterima) for opsi in tombol):
            return p, list(tombol), terpilih
    return None, terlihat, None


def verifikasi_pilihan(d, diterima: tuple[str, ...],
                       nama_soal: str = "pilihan") -> tuple[bool, str]:
    """Baca satu pertanyaan pilihan dan bandingkan dengan nilai yang diterima.

    Dipakai bersama oleh beberapa alur: tiap alur menentukan sendiri opsi
    mana yang dianggap sah, mekanisme pembacaannya sama.
    """
    prefiks = terpilih = None
    terlihat: list[str] = []
    for ke in range(9):
        prefiks, terlihat, terpilih = _baca_soal_sekali(layar.pohon(d), diterima)
        if terpilih is not None:
            return cocok_pilihan(terpilih, diterima), terpilih
        if ke < 2:
            time.sleep(0.6)
        else:
            geser_turun(d)

    if prefiks is None:
        raise AlurGagal(
            f"Tidak ada radiogroup {nama_soal} beropsi {list(diterima)}. "
            f"Opsi yang ada di layar: {terlihat}"
        )
    raise AlurGagal(
        f"{prefiks} ({nama_soal}): tidak ada opsi terpilih setelah 9 kali "
        f"pembacaan sambil menggulir. Opsi terbaca: {terlihat}. Periksa "
        "manual - kemungkinan pertanyaannya memang belum diisi."
    )


def verifikasi_keberadaan(d) -> tuple[bool, str]:
    """Baca radiogroup keberadaan bangunan/usaha.

    Nilai yang terbaca dikembalikan apa adanya. Kalau penanda pilihan tidak
    ditemukan sama sekali, itu dianggap kegagalan - bukan 'belum terpilih' -
    karena deteksinya bergantung pada struktur DOM FormGear yang bisa berubah.
    """
    return verifikasi_pilihan(d, KEBERADAAN_DITERIMA, "keberadaan")


def urai_angka(teks: str) -> float:
    """Ubah angka bergaya Indonesia menjadi float.

    Titik adalah pemisah ribuan dan koma pemisah desimal, jadi "1.255.952"
    bernilai 1255952 - bukan 1,255952. Negatif bisa ditulis dengan minus di
    depan maupun dibungkus tanda kurung.
    """
    bersih = teks.strip().replace(" ", " ")
    bersih = re.sub(r"(?i)\brp\b", "", bersih).strip()

    negatif = bersih.startswith("-") or (bersih.startswith("(") and bersih.endswith(")"))
    bersih = bersih.strip("()").lstrip("+-").strip()
    bersih = bersih.replace(".", "").replace(",", ".")

    if not re.fullmatch(r"\d+(\.\d+)?", bersih):
        raise AlurGagal(f"Nilai {teks!r} tidak bisa dibaca sebagai angka.")
    nilai = float(bersih)
    return -nilai if negatif else nilai


def baca_selisih(d, catat=print, batas: float = 45.0) -> tuple[float, str]:
    """Baca "Selisih Pendapatan dan Pengeluaran" di seksi BLOK IV.

    Nilainya dicari lewat id wadahnya, bukan posisi relatif terhadap label,
    supaya tidak bergeser kalau tata letak berubah. Wadah itu jauh di bawah
    seksi, jadi pencariannya sambil menggulir.
    """
    _, tinggi = d.window_size()
    tenggat = time.monotonic() + batas
    rapikan = 0
    while True:
        root = layar.pohon(d)
        wadah = layar.cari_id(root, SELISIH_ID)
        if wadah is not None:
            wx1, wy1, wx2, wy2 = wadah[1]
            for n in root.iter("node"):
                if not n.get("resource-id", "").endswith("-input"):
                    continue
                x1, y1, x2, y2 = layar._bounds(n)
                di_dalam = x1 >= wx1 and x2 <= wx2 and y1 >= wy1 and y2 <= wy2
                if di_dalam and (teks := (n.get("text") or "").strip()):
                    catat(f"    selisih terbaca: {teks!r}")
                    return urai_angka(teks), teks

            # Wadah mendarat di tepi layar sehingga isinya terpotong dan
            # tidak masuk tree. Dirapikan dulu, bukan langsung gagal.
            if rapikan < 6:
                rapikan += 1
                ke_bawah = wy2 > tinggi - 120
                catat(f"    wadah di tepi layar - rapikan posisi "
                      f"({'turun' if ke_bawah else 'naik'}, {rapikan}/6)")
                geser_halus(d, turun=ke_bawah)
                continue

            raise AlurGagal(
                f"Wadah {SELISIH_ID!r} terlihat tapi kotak nilainya tetap "
                f"kosong setelah {rapikan} kali dirapikan. Kemungkinan "
                "nilainya memang belum terisi - periksa manual."
            )
        if time.monotonic() >= tenggat:
            raise AlurGagal(
                f"Tidak menemukan {SELISIH_ID!r} dalam {batas:.0f} detik, "
                "termasuk setelah digulir. Pastikan seksinya benar."
            )
        geser_turun(d)


def reject(d, catat=print) -> None:
    """FAB bukan-pencacah > APPROVAL > REJECT > konfirmasi.

    REJECT ada di daftar terlarang global karena letaknya persis di sebelah
    APPROVE. Di sini ia dibuka lewat `izinkan`, dan tetap melalui verifikasi
    teks yang sama - jadi salah tekan tetap tidak mungkin.
    """
    if layar.cari_teks_mana_saja(layar.pohon(d), [PROMPT_APPROVE]) is None:
        catat("    tap FAB bukan-pencacah")
        tap_id(d, "expendable_fab_bukan_pencacah")
        catat("    tap APPROVAL")
        tap_label(d, LBL_APPROVAL)
        catat("    menunggu layar approval siap")
        tunggu_teks(d, [PROMPT_APPROVE], batas=90.0)
    else:
        catat("    layar approval sudah tampil")

    catat("    prompt terverifikasi, tap REJECT")
    tap_label(d, LBL_REJECT, batas=30.0, izinkan=("REJECT",))

    # Sebagian varian tidak menampilkan konfirmasi; ketiadaannya bukan
    # kegagalan.
    try:
        tunggu_teks(d, LBL_YA + LBL_IYA, batas=12.0)
    except AlurGagal:
        catat("    tidak ada tombol konfirmasi - memeriksa hasilnya")
        return
    catat("    tap konfirmasi reject")
    tap_label(d, LBL_YA + LBL_IYA, batas=15.0)


def unapprove(d, catat=print) -> None:
    """FAB bukan-pencacah > Approval > UNAPPROVE > konfirmasi.

    Layar pilihan untuk assignment yang sudah ter-approve hanya memuat satu
    tombol, jadi tidak ada tombol berbahaya bertetangga di sini.
    """
    if layar.cari_teks_mana_saja(layar.pohon(d), [PROMPT_APPROVE]) is None:
        catat("    tap FAB bukan-pencacah")
        tap_id(d, "expendable_fab_bukan_pencacah")
        catat("    tap Approval")
        tap_label(d, LBL_APPROVAL)
        catat("    menunggu layar approval siap")
        tunggu_teks(d, [PROMPT_APPROVE], batas=90.0)
    else:
        catat("    layar approval sudah tampil")

    catat("    tap UNAPPROVE")
    tap_label(d, LBL_UNAPPROVE, batas=30.0)

    try:
        tunggu_teks(d, LBL_YA + LBL_IYA, batas=12.0)
    except AlurGagal:
        catat("    tidak ada tombol konfirmasi")
        return
    catat("    tap konfirmasi")
    tap_label(d, LBL_YA + LBL_IYA, batas=15.0)


def approve(d, catat=print) -> None:
    """FAB bukan-pencacah > APPROVAL > (tunggu) > APPROVE > YA.

    Layar pilihan akhir menaruh REJECT tepat di sebelah APPROVE, jadi teks
    promptnya diverifikasi dulu dan REJECT ada di daftar terlarang.
    """
    # Kalau layar pilihan sudah tampil, jangan buka menu lagi.
    if layar.cari_teks_mana_saja(layar.pohon(d), [PROMPT_APPROVE]) is None:
        catat("    tap FAB bukan-pencacah")
        tap_id(d, "expendable_fab_bukan_pencacah")
        catat("    tap APPROVAL")
        tap_label(d, LBL_APPROVAL)

        # 'tunggu beberapa saat' pada alur manual: layar approval memuat data
        # dulu. Ditunggu sampai promptnya benar-benar ada, bukan sleep tetap.
        catat("    menunggu layar approval siap")
        tunggu_teks(d, [PROMPT_APPROVE], batas=90.0)
    else:
        catat("    layar approval sudah tampil")

    catat("    prompt terverifikasi, tap APPROVE")
    tap_label(d, LBL_APPROVE, batas=30.0)
    catat("    tap YA (konfirmasi approve)")
    tap_label(d, LBL_YA, batas=30.0)


def ada_petunjuk(root: ET.Element, petunjuk: tuple[str, ...]) -> bool:
    """Apakah ada node yang teksnya memuat seluruh potongan kata petunjuk."""
    for node in root.iter("node"):
        teks = (node.get("text") or "").casefold()
        if all(k in teks for k in petunjuk):
            return True
    return False


def ada_dialog_keluar(root: ET.Element) -> bool:
    """Apakah dialog konfirmasi keluar kuesioner sedang tampil."""
    return ada_petunjuk(root, PETUNJUK_DIALOG_KELUAR)


def keluar_kuesioner(d, catat=print, batas: float = 45.0,
                     wilayah: str | None = None) -> None:
    """Kembali dari FormGear ke Daftar Assignment.

    Wajib dipanggil setelah baris terlantar. Tanpa ini putaran berikutnya
    masih berada di dalam kuesioner dan pasti gagal - persis yang membuat
    mode 'catat lalu lanjut' tidak pernah benar-benar melanjutkan.

    Dialog konfirmasi keluar dijawab IYA - aman karena bot tidak pernah
    mengubah isian kuesioner. Baris yang bermasalah sudah dicatat pemanggil,
    jadi di sini tugasnya hanya mengembalikan layar supaya baris berikutnya
    bisa diproses.
    """
    if AKTIVITAS_DAFTAR in _aktivitas(d):
        return

    catat("    keluar dari kuesioner")
    tenggat = time.monotonic() + batas
    ditekan = 0
    while time.monotonic() < tenggat and ditekan < 3:
        kini = _aktivitas(d)
        if AKTIVITAS_DAFTAR in kini:
            pastikan_daftar_siap(d, wilayah=wilayah, catat=catat)
            catat("    kembali di Daftar Assignment")
            return
        if AKTIVITAS_FORM not in kini:
            raise AlurGagal(f"Terdampar di layar tak dikenal: {kini}")

        if ada_dialog_keluar(layar.pohon(d)):
            catat("    dialog konfirmasi keluar - tap IYA")
            tap_label(d, LBL_IYA, batas=15.0)
            time.sleep(1.0)
            continue

        d.press("back")
        ditekan += 1
        # Beri jeda cukup untuk transisi activity sebelum diperiksa lagi;
        # back yang beruntun terlalu cepat bisa keluar dari aplikasi.
        time.sleep(1.5)

    if AKTIVITAS_DAFTAR in _aktivitas(d):
        pastikan_daftar_siap(d, wilayah=wilayah, catat=catat)
        return

    isi = layar.ringkas_layar(layar.pohon(d))
    raise AlurGagal(
        f"Tidak bisa keluar dari kuesioner setelah {ditekan} kali back. "
        f"Yang terlihat di layar: {isi}"
    )


def proses_satu(d, urutan: int, kering: bool, catat=print,
                lewati: set[str] | None = None,
                wilayah: str | None = None,
                diterima: tuple[str, ...] | None = KEBERADAAN_DITERIMA,
                nama_soal: str = "keberadaan",
                kata_cari: str | None = None,
                putuskan=None,
                syarat_kolom: dict[str, str] | None = None) -> HasilBaris:
    """Satu putaran penuh: filter, ambil baris pertama, proses.

    Pencatatan bersifat write-ahead: niat ditulis sebelum aksi dijalankan,
    supaya baris yang tergantung tetap terlacak kalau bot mati di tengah.
    """
    catat(f"\n[{urutan}] mulai putaran")
    terapkan_filter_submit(d, catat=catat, wilayah=wilayah)

    if kata_cari:
        pastikan_pencarian(d, kata_cari, catat=catat)
    else:
        # Kotak Search bertahan antar-alur dan bisa diam-diam mempersempit
        # daftar, jadi keadaannya selalu dicatat.
        hit = layar.cari_kelas(layar.pohon(d), KELAS_INPUT)
        isi = (hit[0].get("text") or "").strip() if hit else ""
        if isi:
            catat(f"    PERHATIAN: kotak Search berisi {isi!r} - daftar "
                  "tersaring oleh kata itu. Kosongkan kalau tidak dimaksud.")
        else:
            catat("    search: kosong (seluruh daftar)")

    b = baris_pertama(d, lewati)
    r = HasilBaris(nama=b.nama, nomor=b.nomor)
    catat(f"    baris pertama: {b.label}")

    # Syarat kolom diperiksa sebelum apa pun dibuka. Kalau tidak lolos, bot
    # berhenti tanpa menyentuh assignment - jadi tidak ada baris terlantar.
    # Nilai syarat boleh berupa teks (harus sama persis) atau fungsi, karena
    # sebagian kolom berisi gabungan beberapa nilai seperti "- / 43974516".
    for nama_kolom, harus in (syarat_kolom or {}).items():
        ada = layar.nilai_kolom(layar.pohon(d), b, nama_kolom)
        if ada is None:
            raise AlurGagal(
                f"Kolom {nama_kolom!r} tidak ada di tabel ini. Kolom yang "
                f"tersedia: {layar.kolom_tabel(layar.pohon(d))}"
            )
        catat(f"    {nama_kolom}: {ada!r}")
        if callable(harus):
            cocok, diminta = harus(ada), getattr(harus, "penjelasan", "syarat")
        else:
            cocok, diminta = ada.strip() == harus, repr(harus)
        if not cocok:
            raise SyaratTakLolos(
                f"{nama_kolom} = {ada!r}, tidak memenuhi {diminta}", hasil=r
            )

    pohon = set_bentang(d, b.kunci, True)
    r.detail = baca_detail(pohon)
    # Kalau tabelnya punya kolom Status - seperti Sakernas - nilai dari sel
    # baris lebih dipercaya daripada hasil pemotongan label pada detail.
    if b.status:
        r.detail["Status"] = b.status
    catat(f"    status: {r.status or '(tidak terbaca)'}")

    if not r.layak:
        set_bentang(d, b.kunci, False)
        raise AlurGagal(
            f"Baris pertama {b.label} berstatus {r.status!r}, yang bukan "
            "status submitted. Bot berhenti supaya tidak melewati baris ini "
            "diam-diam."
        )

    if kering:
        set_bentang(d, b.kunci, False)
        r.catatan.append("dry-run: berhenti sebelum Aksi/BUKA")
        catat("    DRY-RUN: berhenti di sini, tidak menekan Aksi")
        return r

    # Titik tidak-bisa-kembali: kegagalan setelah ini meninggalkan
    # assignment dalam keadaan terbuka.
    # Kata "proses" dipakai, bukan "approve": pada alur berkeputusan, arah
    # tindakannya belum diketahui sampai isi kuesioner dibaca.
    catat(f"    NIAT: buka lalu proses {b.label}")
    try:
        buka_kuesioner(d, b.kunci, catat=catat)

        if putuskan is not None:
            # Fungsi penentu membaca sendiri lalu memilih approve/reject.
            keputusan, nilai = putuskan(d, catat)
            r.detail["NilaiSoal"] = nilai
            r.detail["Keputusan"] = keputusan
            if keputusan == "approve":
                catat(f"    keputusan: APPROVE ({nilai})")
                approve(d, catat=catat)
            elif keputusan == "reject":
                catat(f"    keputusan: REJECT ({nilai})")
                reject(d, catat=catat)
            else:
                raise AlurGagal(
                    f"Keputusan {keputusan!r} tidak dikenal untuk {b.label} "
                    f"(nilai {nilai})."
                )
        elif diterima:
            ke_seksi_target(d, catat=catat)
            cocok, nilai = verifikasi_pilihan(d, diterima, nama_soal)
            r.detail["NilaiSoal"] = nilai
            catat(f"    {nama_soal}: {nilai!r}")
            if not cocok:
                raise NilaiTakSesuai(
                    f"{nama_soal} = {nilai!r}, bukan salah satu dari "
                    f"{list(diterima)}"
                )
            approve(d, catat=catat)
        else:
            # Tanpa pengecekan isi: penyaringnya hanya filter Submit dan
            # Status baris. Dicatat eksplisit agar jelas saat log dibaca.
            r.detail["NilaiSoal"] = "(tanpa pengecekan)"
            catat("    tanpa pengecekan isi kuesioner - tunggu form siap")
            tunggu_kuesioner_siap(d)
            catat("    form siap - langsung approve")
            approve(d, catat=catat)
    except NilaiTakSesuai as e:
        raise NilaiTakSesuai(str(e), hasil=r) from e
    except AlurGagal as e:
        r.catatan.append(f"TERLANTAR: {e}")
        raise AlurGagal(
            f"{e} Assignment ini terbuka tapi belum diputuskan.", hasil=r
        ) from e

    # Aksi sudah terkirim; catatan ditulis lebih dulu agar baris yang
    # berhasil tidak hilang dari laporan kalau langkah berikutnya gagal.
    ditolak = r.detail.get("Keputusan") == "reject"
    r.catatan.append("rejected" if ditolak else "approved")
    try:
        pastikan_daftar_siap(d, wilayah=wilayah, catat=catat)
    except AlurGagal as e:
        r.catatan.append(f"PERINGATAN: tidak kembali ke daftar - {e}")
        raise AlurGagal(f"Setelah approve, {e}", hasil=r) from e
    catat(f"    SELESAI: {b.label} {'ter-REJECT' if ditolak else 'ter-approve'}")
    return r


def jalankan(d, loop: int | None, kering: bool, catat=print, simpan=None,
             diterima: tuple[str, ...] | None = KEBERADAAN_DITERIMA,
             nama_soal: str = "keberadaan",
             kata_cari: str | None = None,
             putuskan=None,
             syarat_kolom: dict[str, str] | None = None) -> list[HasilBaris]:
    """Jalankan N putaran; baris bermasalah dicatat lalu dilewati.

    Melanjutkan hanya aman untuk kegagalan yang terjadi setelah assignment
    terbuka, karena baris yang sudah terbuka keluar dari filter Submit dan
    putaran berikutnya pasti dapat baris lain. Kegagalan sebelum itu -
    misalnya filter tidak bisa diterapkan - akan mengulang baris yang sama
    terus-menerus, jadi bot berhenti.
    """
    hasil: list[HasilBaris] = []
    lewati: set[str] = set()

    # Wilayah tidak ditentukan dari luar: bot memakai yang sedang dibuka,
    # menguncinya, dan memakai kodenya untuk pemulihan.
    try:
        wilayah = tunggu_daftar_siap(d)
    except AlurGagal as e:
        catat(f"\nBERHENTI sebelum mulai: {e}")
        catat("Buka wilayahnya di BlueStacks sampai tabel assignment tampil, "
              "lalu jalankan lagi.")
        return hasil
    catat(f"Wilayah terkunci: {wilayah}")

    def rekam(r: HasilBaris) -> None:
        hasil.append(r)
        lewati.add(r.kunci)  # jangan pernah diambil lagi pada run ini
        if simpan is not None:
            simpan(r)        # ditulis per baris supaya selamat kalau run terputus

    # loop=None berarti kerjakan sampai daftarnya habis. Jumlah baris yang
    # sudah dicoba selalu bertambah, jadi baris_pertama pasti kehabisan
    # kandidat pada suatu titik - run tidak bisa berputar tanpa akhir.
    i = 0
    while loop is None or i < loop:
        i += 1
        try:
            r = proses_satu(d, i, kering, catat=catat, lewati=lewati,
                            wilayah=wilayah, diterima=diterima,
                            nama_soal=nama_soal, kata_cari=kata_cari,
                            putuskan=putuskan, syarat_kolom=syarat_kolom)
        except DaftarHabis as e:
            catat(f"\nSELESAI: {e}")
            break
        except NilaiTakSesuai as e:
            # Nilainya terbaca jelas dan memang tidak memenuhi syarat, jadi
            # assignment-nya di-reject lalu run lanjut. Sebabnya tetap
            # dicatat supaya keputusan ini bisa ditelusuri belakangan.
            r = e.hasil
            catat(f"    TIDAK SESUAI: {r.label}")
            catat(f"      sebab: {e}")
            try:
                reject(d, catat=catat)
                r.catatan.append(f"rejected: {e}")
                r.detail["Keputusan"] = "reject"
                catat("    di-REJECT karena nilainya tidak sesuai")
                pastikan_daftar_siap(d, wilayah=wilayah, catat=catat)
            except AlurGagal as gagal:
                r.catatan.append(f"TERLANTAR: gagal reject - {gagal}")
                catat(f"    gagal me-reject: {gagal}")
                try:
                    keluar_kuesioner(d, catat=catat, wilayah=wilayah)
                except AlurGagal as keluar:
                    rekam(r)
                    catat(f"\nBERHENTI di putaran {i}: {keluar}")
                    break
            rekam(r)
            continue
        except SyaratTakLolos as e:
            # Daftar diurutkan sehingga baris yang memenuhi syarat berkumpul
            # di atas: begitu baris teratas tidak lolos, sisanya juga tidak.
            catat(f"\nSELESAI: {e.hasil.label} {e} - tidak ada lagi baris "
                  "yang memenuhi syarat.")
            break
        except AlurGagal as e:
            if e.hasil is None:
                catat(f"\nBERHENTI di putaran {i}: {e}")
                break
            r = e.hasil
            rekam(r)
            # Baris yang approve-nya sudah terkirim bukan baris terlantar,
            # walau bot gagal kembali ke daftar sesudahnya.
            label = "APPROVED tapi bermasalah" if "approved" in r.catatan else "TERLANTAR"
            catat(f"    {label}: {r.label}")
            catat(f"      sebab: {e}")
            try:
                keluar_kuesioner(d, catat=catat, wilayah=wilayah)
            except AlurGagal as keluar:
                catat(f"\nBERHENTI di putaran {i}: {keluar}")
                catat(f"  Baris        : {r.label}")
                catat(f"  {nama_soal} terbaca: "
                      f"{r.detail.get('NilaiSoal', '(tidak terbaca)')!r}")
                catat(f"  Status baris : {r.status or '(tidak terbaca)'}")
                break
            continue

        rekam(r)
        if kering:
            catat("\nDry-run hanya menjalankan satu putaran.")
            break
    return hasil


def pindai(d, maks: int | None = None, catat=print) -> list[HasilBaris]:
    """Bentangkan tiap baris satu per satu, catat detailnya, lalu tutup.

    Tidak ada aksi yang terkirim ke server. Baris diproses berdasarkan nama,
    bukan koordinat, karena membentangkan satu baris menggeser semua baris
    di bawahnya.
    """
    root = layar.pohon(d)
    info = periksa_prasyarat(root)
    catat(f"Wilayah : {info.get('wilayah1')}")
    catat(f"Filter  : {info.get('filtered')}")
    catat(f"Sortir  : {info.get('sorted')}")

    geser_ke_atas(d)

    hasil: list[HasilBaris] = []
    sudah: set[str] = set()
    mandek = 0

    while mandek < 3:
        terlihat = layar.baris_terlihat(layar.pohon(d))
        baru = [b for b in terlihat if b.kunci not in sudah]

        if not baru:
            mandek += 1
            geser_turun(d)
            continue
        mandek = 0

        for b in baru:
            if maks is not None and len(hasil) >= maks:
                catat(f"\nBerhenti: batas {maks} baris tercapai.")
                return hasil

            sudah.add(b.kunci)
            r = HasilBaris(nama=b.nama, nomor=b.nomor)
            try:
                pohon = set_bentang(d, b.kunci, True)
                r.detail = baca_detail(pohon)
                # Sebagian tabel memuat Status sebagai kolom; nilainya lebih
                # dipercaya daripada hasil pemotongan label pada detail.
                if b.status:
                    r.detail["Status"] = b.status
                set_bentang(d, b.kunci, False)
            except AlurGagal as e:
                r.catatan.append(str(e))

            tanda = "LAYAK " if r.layak else "lewati"
            catat(f"  [{len(hasil) + 1:>3}] {tanda} {r.nama[:44]:<44} "
                  f"{r.status or '(status tidak terbaca)'}")
            for c in r.catatan:
                catat(f"        ! {c}")
            hasil.append(r)

    return hasil
