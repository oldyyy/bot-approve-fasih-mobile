# bot-fasih-approve

Otomasi persetujuan assignment pada aplikasi **FASIH** (`id.go.bpsfasih`) yang
berjalan di BlueStacks. Bot membaca layar lewat accessibility tree Android,
bukan lewat pencocokan gambar, sehingga tidak bergantung pada koordinat tetap.

> Bot ini menekan tombol persetujuan pada data sensus sungguhan. Pastikan
> penggunaannya sesuai kebijakan kantor, dan bahwa wilayah yang terbuka di
> BlueStacks memang wilayah yang dituju.

## Prasyarat

- BlueStacks 5 dengan **ADB aktif** (Settings → Advanced → Android Debug Bridge)
- Resolusi instance **900x1600, DPI 240** — jangan diubah, alasannya di bawah
- Python 3.11+

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Uji logika yang tidak butuh perangkat (parsing angka, pencocokan label,
pembacaan kolom) — kasusnya diambil dari data nyata yang pernah muncul di
layar, termasuk yang dulu menyebabkan bug:

```bash
.venv\Scripts\python.exe uji.py
```

## Alur yang tersedia

Setiap alur memakai mesin yang sama; yang membedakan hanya syarat dan keputusan.

| Skrip | Syarat | Tindakan |
|---|---|---|
| `jalankan.py` | Keberadaan bernilai kode 0/3/4/5 | approve |
| `bangunan-kosong.py` | Search `kosong`, Kode Penggunaan Bangunan = 6 | approve |
| `sakernas-pemutakhiran.py` | tidak ada pengecekan isi | approve |
| `se-approve-nousaha.py` | Jumlah Usaha = 0, lalu baca Selisih Pendapatan | selisih ≥ 0 approve, < 0 **reject** |

`pindai.py` memindai isi wilayah tanpa menyentuh apa pun (hanya membentangkan
dan menutup baris), berguna untuk melihat isi daftar sebelum memproses.

## Menjalankan

Buka wilayah yang dituju di BlueStacks sampai tabel assignment tampil, lalu:

```bash
.venv\Scripts\python.exe jalankan.py --loop 10 --perangkat 5666
```

| Opsi | Arti |
|---|---|
| `--loop N` | jumlah baris yang diproses (wajib) |
| `--kering` | dry-run: satu putaran, berhenti sebelum menekan Aksi |
| `--perangkat` | port instance; wajib kalau lebih dari satu instance jalan |
| `--abaikan-kunci` | jalan walau wilayahnya terkunci run lain |

Alat bantu:

```bash
.venv\Scripts\python.exe tools\daftar_perangkat.py   # instance aktif + wilayahnya
.venv\Scripts\python.exe tools\pulihkan_agen.py      # hidupkan ulang agen uiautomator2
.venv\Scripts\python.exe tools\tap.py --lihat        # isi layar saat ini
```

### Beberapa instance sekaligus

Bisa berapa pun. Syaratnya tiap instance dibuka di **wilayah berbeda** — kalau
tidak, kunci wilayah (`catatan/kunci-<kode>.json`) akan menolak run kedua.
Nama berkas log memuat port, jadi run yang berbarengan tidak saling menimpa.

## Pengaman

- Menolak jalan kalau filter di layar bukan `Filter By Submit`
- Baris pertama harus berstatus `SUBMITTED BY ...`
- Wilayah dikunci di awal run; kalau berubah di tengah jalan, bot berhenti
- Tombol `HAPUS`, `ASSIGN`, `RESTORE`, `PINDAH MODE`, `Tandai wilayah telah
  selesai`, dan `REJECT` ada di daftar terlarang, dicek ulang tepat sebelum tap
  — `HAPUS` bertetangga dengan `BUKA`, dan `REJECT` bertetangga dengan
  `APPROVE`. Hanya `se-approve-nousaha.py` yang membuka `REJECT`, lewat izin
  per-panggilan
- Dialog konfirmasi diverifikasi teksnya sebelum ditekan
- Log ditulis per baris (write-ahead) dan CSV ditulis per baris, jadi run yang
  terputus tetap meninggalkan catatan lengkap
- Bot **berhenti** saat ragu, tidak menebak

## Struktur

```
bot/perangkat.py   deteksi & koneksi instance BlueStacks
bot/layar.py       pembacaan layar: baris tabel, kolom, radiogroup
bot/alur.py        langkah-langkah alur di FASIH
bot/runner.py      mesin bersama: argumen, kunci, log, CSV, kode keluar
bot/kunci.py       kunci per wilayah antar-run
tools/             alat pemetaan manual
uji.py             uji fungsi murni, tidak butuh perangkat
catatan/           log & CSV hasil run (tidak di-commit)
```

## Catatan teknis

Hal-hal yang tidak terlihat dari kode tapi menentukan cara kerjanya.

**Accessibility tree hanya memuat yang ter-render.** Elemen di luar viewport
tidak ada sama sekali di tree — bukan sekadar tidak terlihat. Ini tiga kali
menjadi sumber bug: opsi radio terpilih di bawah layar terbaca sebagai "tidak
ada yang terpilih", pertanyaan seksi di bawah lipatan terbaca sebagai "seksi
tidak memuat apa pun", dan penanda wilayah hilang saat daftar tergulir. Semua
pencarian elemen karenanya sadar-gulir.

**Geseran nyata ≠ jarak gestur.** Inertial scroll WebView menambah sekitar 20%
pada gestur cepat. Hasil pengukuran di instance 900x1600:

| jarak | durasi | geseran nyata | rasio | detik/1000px |
|---|---|---|---|---|
| 550 | 0,20 | 619 | 1,13× | 1,773 |
| 800 | 0,20 | 952 | 1,19× | 1,128 |
| **1000** | **0,20** | **1205** | **1,20×** | **0,855** |
| 1200 | 0,20 | > 1440 | ~1,2× | ditolak |
| 800 | 0,40 | 840 | 1,05× | 2,016 |

Dipakai 1000 px. Geseran harus tetap di bawah tinggi viewport (1600) supaya
elemen pendek tidak terlewati; 1200 px pernah benar-benar melewatkan target.
Memperpanjang durasi justru memperburuk efisiensi.

**Resolusi dan DPI jangan diubah.** Tombol `+` untuk membentangkan baris ada
karena DataTables menyembunyikan kolom pada layar sempit. Kalau lebar efektif
(dp) bertambah, semua kolom muat, `+` hilang, dan seluruh alur patah.

**Nama baris tidak unik.** Banyak assignment bernama sama persis (`BANGUNAN
KOSONG`, `KAMAR KOSONG`). Identitas baris memakai nama + kolom pembeda lain,
dengan kolom status sengaja dikecualikan karena nilainya berubah setelah
diproses.

**Susunan kolom berbeda antar survei.** Indeks kolom tidak boleh dihardcode:
di SE2026 kolom ketiga adalah Nomor Urut Bangunan/IDSBR yang unik, di Sakernas
kolom ketiga adalah PMM yang isinya hanya 0 atau 1. Indeks dicari dari nama
header.

**Label opsi dicocokkan sebagai awalan.** FASIH sering menambah keterangan di
belakang label — `0. Tidak Ditemukan (STOP)` pada varian keluarga, `6. Bangunan
Lainnya yang Tidak Tercakup (Tempat Judi, ...)`. Beberapa tombol juga dirender
dengan spasi antar huruf (`A P P R O V E`), sehingga pencocokan membuang seluruh
spasi lebih dulu.

**Angka memakai format Indonesia.** Titik adalah pemisah ribuan, koma pemisah
desimal: `1.255.952` bernilai satu juta dua ratus ribu.

**Agen uiautomator2 bisa mati di tengah run panjang.** Kalau itu terjadi setiap
pembacaan layar menggantung. Batas HTTP dipendekkan ke 60 detik dan pembacaan
layar menghidupkan ulang agen lalu mengulang sekali.

**Port ADB BlueStacks tidak tetap** — berubah saat instance di-restart. Port
dicari otomatis dari `bluestacks.conf` dan daftar port yang sedang LISTENING.

**Screenshot tidak tersedia** di konfigurasi ini (menghasilkan gambar hitam),
jadi tidak ada bukti visual. Sebagai gantinya seluruh langkah tercatat di log.

## Keterbatasan

- Verifikasi isi kuesioner hanya bisa dilakukan **setelah** assignment dibuka.
  Baris yang gagal verifikasi jadi terbuka tanpa disetujui — dicatat sebagai
  `TERLANTAR` di log dan CSV, perlu ditangani manual.
- Syarat berbasis kolom daftar (mis. `Jumlah Usaha = 0`) diperiksa **sebelum**
  membuka, jadi kegagalannya tidak meninggalkan baris terlantar.
