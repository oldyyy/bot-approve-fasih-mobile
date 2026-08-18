# bot-fasih-approve

Otomasi persetujuan assignment pada aplikasi **FASIH** (`id.go.bpsfasih`) yang
berjalan di BlueStacks. Bot membaca layar lewat accessibility tree Android,
bukan lewat pencocokan gambar, sehingga tidak bergantung pada koordinat tetap.

> Bot ini menekan tombol persetujuan pada data sensus sungguhan. Pastikan
> penggunaannya sesuai kebijakan kantor, dan bahwa wilayah yang terbuka di
> BlueStacks memang wilayah yang dituju.

## Prasyarat

- BlueStacks 5 dengan **ADB aktif** (Settings > Advanced > Android Debug Bridge)
- Resolusi instance **900x1600, DPI 240** - jangan diubah, alasannya di bawah
- Python 3.11+

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Uji logika yang tidak butuh perangkat (parsing angka, pencocokan label,
pembacaan kolom, klasifikasi warna, pemilihan baris) - kasusnya diambil dari
data nyata yang pernah muncul di layar, termasuk yang dulu menyebabkan bug:

```bash
.venv\Scripts\python.exe uji.py
```

## Alur yang tersedia

Alur berbasis **putaran** memproses baris pertama pada daftar tersaring Submit,
berulang kali. Alur berbasis **daftar nama** mencari tiap nama dan memutuskan
dari warna barisnya.

| Skrip | Syarat | Tindakan |
|---|---|---|
| `jalankan.py` | keberadaan kode 0/3/4/5 | approve |
| `bangunan-kosong.py` | Search `kosong`, Kode Penggunaan Bangunan = 6 | approve |
| `sakernas-pemutakhiran.py` | tidak ada pengecekan isi | approve |
| `se-approve-nousaha.py` | Jumlah Usaha = 0, lalu Selisih Pendapatan | selisih >= 0 approve, < 0 **reject** |
| `approve-nofound.py` | Nomor Urut Bangunan = `-`, lalu keberadaan kode 0/3/4/5 | approve |
| `unapprove-list.py` | daftar nama, baris harus **hijau** | **unapprove**, diulang sampai biru |
| `reject-list.py` | daftar nama, baris harus **biru** | **reject**, diulang sampai merah |

`pindai.py` memindai isi wilayah tanpa menyentuh apa pun (hanya membentangkan
dan menutup baris), berguna untuk melihat isi daftar sebelum memproses.

## Menjalankan

Buka wilayah yang dituju di BlueStacks sampai tabel assignment tampil, lalu:

```bash
.venv\Scripts\python.exe jalankan.py --perangkat 5665
.venv\Scripts\python.exe approve-nofound.py --loop 5 --perangkat 5665
```

| Opsi | Arti |
|---|---|
| `--loop N` | jumlah baris; tanpa ini dikerjakan sampai daftar habis |
| `--kering` | dry-run: satu putaran, berhenti sebelum menekan Aksi |
| `--perangkat` | port instance; wajib kalau lebih dari satu instance jalan |
| `--abaikan-kunci` | jalan walau wilayahnya terkunci run lain |

Alur berbasis daftar nama memakai `--nama` atau `--berkas`, bukan `--loop`.
Pencariannya substring, jadi nama boleh dipotong:

```bash
.venv\Scripts\python.exe unapprove-list.py --perangkat 5665 --berkas daftar.txt
.venv\Scripts\python.exe reject-list.py --perangkat 5665 --kering --nama "BUDI"
```

Alat bantu:

```bash
.venv\Scripts\python.exe tools\daftar_perangkat.py   # instance aktif + wilayahnya
.venv\Scripts\python.exe tools\pulihkan_agen.py      # hidupkan ulang agen uiautomator2
.venv\Scripts\python.exe tools\baca_warna.py         # warna tiap baris yang tampil
.venv\Scripts\python.exe tools\tap.py --lihat        # isi layar saat ini
```

## Kunci wilayah

**Semua bot mengunci wilayah yang sedang digarapnya**, termasuk `pindai.py`
yang sebenarnya tidak mengubah data - ia tetap mengendalikan UI, jadi dua bot
di wilayah yang sama akan saling merusak navigasi.

Kuncinya berupa `catatan/kunci-<kode wilayah>.json` dan dilepas saat run
selesai. Run yang dihentikan paksa meninggalkan kuncinya; kunci seperti itu
diperiksa apakah prosesnya masih hidup dan diambil alih otomatis kalau sudah
mati. Kunci milik proses yang benar-benar berjalan tetap menahan.

Karena itu beberapa instance boleh jalan bersamaan **asal wilayahnya berbeda**.
Nama berkas log memuat port, jadi run yang berbarengan tidak saling menimpa.

Alur berbasis warna (`unapprove-list.py`, `reject-list.py`) adalah pengecualian:
ia menangkap jendela BlueStacks, jadi jendelanya harus terbuka dan tidak
diminimalkan.

## Pengaman

- Menolak jalan kalau filter di layar bukan `Filter By Submit`
- Baris pertama harus berstatus `SUBMITTED BY ...`
- Wilayah dikunci di awal run; kalau berubah di tengah jalan, bot berhenti
- Tombol `HAPUS`, `ASSIGN`, `RESTORE`, `PINDAH MODE`, `Tandai wilayah telah
  selesai`, dan `REJECT` ada di daftar terlarang, dicek ulang tepat sebelum tap
  - `HAPUS` bertetangga dengan `BUKA`, dan `REJECT` bertetangga dengan
  `APPROVE`. Hanya `se-approve-nousaha.py` dan `reject-list.py` yang membuka
  `REJECT`, lewat izin per-panggilan
- Dialog konfirmasi diverifikasi teksnya sebelum ditekan
- Pencarian yang menghasilkan banyak baris tidak ditebak: dipilih yang nama
  kepala keluarganya persis sama, atau dicatat sebagai `ambigu` dan dilewati
- Nilai kuesioner yang terbaca tapi di luar syarat membuat assignment-nya
  **di-reject**, bukan dibiarkan menggantung - lihat di bawah
- Log dan CSV ditulis per baris (write-ahead), jadi run yang terputus tetap
  meninggalkan catatan lengkap
- Bot **berhenti** saat ragu, tidak menebak

### Nilai tidak sesuai vs gagal teknis

Dua hal ini sengaja dibedakan, karena tindakannya berbeda:

| Jenis | Contoh | Tindakan |
|---|---|---|
| **Nilai tidak sesuai** | kode bangunan `4` padahal syaratnya `6` | **REJECT** + log sebabnya, run lanjut |
| **Gagal teknis** | kuesioner tidak selesai dirender, nilai tidak terbaca | catat `TERLANTAR`, run lanjut tanpa reject |

Kalau bot **gagal membaca** layar, datanya belum tentu salah - me-reject karena
bot tidak bisa melihat berarti mengembalikan pekerjaan pencacah yang mungkin
sudah benar. Jadi reject hanya untuk nilai yang terbaca jelas dan memang di
luar syarat. Sebabnya masuk log dan kolom `catatan` di CSV, lengkap dengan
nilai yang mendasarinya.

### Membedakan selesai dari gagal

| Kondisi | Arti | Kode keluar |
|---|---|---|
| `SELESAI: ... daftar habis` | tidak ada baris tersisa | 0 |
| `SELESAI: ... tidak memenuhi syarat` | baris teratas bukan sasaran lagi | 0 |
| `BERHENTI: ...` | ada yang tidak beres | 1 |
| `TERLANTAR` | assignment terbuka tapi belum diputuskan | 1 |

Syarat kolom diperiksa **sebelum** assignment dibuka, jadi baris yang tidak
lolos tidak pernah berubah status. Alur yang memakainya mengandalkan daftar
yang sudah diurutkan: begitu baris teratas tidak lolos, sisanya juga tidak.

## Struktur

```
bot/perangkat.py   deteksi & koneksi instance BlueStacks
bot/layar.py       pembacaan layar: baris tabel, kolom, radiogroup
bot/warna.py       baca warna baris dari tangkapan jendela BlueStacks
bot/alur.py        langkah-langkah alur di FASIH
bot/runner.py      mesin alur N-baris-pertama
bot/daftar.py      mesin alur berdasarkan daftar nama + warna baris
bot/kunci.py       kunci per wilayah antar-run
bot/cli.py         argumen bersama alat bantu
tools/             alat pemetaan manual
uji.py             uji fungsi murni, tidak butuh perangkat
catatan/           log & CSV hasil run (tidak di-commit)
```

## Catatan teknis

Hal-hal yang tidak terlihat dari kode tapi menentukan cara kerjanya.

**Accessibility tree hanya memuat yang ter-render.** Elemen di luar viewport
tidak ada sama sekali di tree - bukan sekadar tidak terlihat. Ini tiga kali
menjadi sumber bug: opsi radio terpilih di bawah layar terbaca sebagai "tidak
ada yang terpilih", pertanyaan seksi di bawah lipatan terbaca sebagai "seksi
tidak memuat apa pun", dan penanda wilayah hilang saat daftar tergulir. Semua
pencarian elemen karenanya sadar-gulir.

**Geseran nyata bukan jarak gestur.** Inertial scroll WebView menambah sekitar
20% pada gestur cepat. Hasil pengukuran di instance 900x1600:

| jarak | durasi | geseran nyata | rasio | detik/1000px |
|---|---|---|---|---|
| 550 | 0,20 | 619 | 1,13x | 1,773 |
| 800 | 0,20 | 952 | 1,19x | 1,128 |
| **1000** | **0,20** | **1205** | **1,20x** | **0,855** |
| 1200 | 0,20 | > 1440 | ~1,2x | ditolak |
| 800 | 0,40 | 840 | 1,05x | 2,016 |

Dipakai 1000 px. Geseran harus tetap di bawah tinggi viewport (1600) supaya
elemen pendek tidak terlewati; 1200 px pernah benar-benar melewatkan target.
Memperpanjang durasi justru memperburuk efisiensi.

**Resolusi dan DPI jangan diubah.** Tombol `+` untuk membentangkan baris ada
karena DataTables menyembunyikan kolom pada layar sempit. Kalau lebar efektif
(dp) bertambah, semua kolom muat, `+` hilang, dan seluruh alur patah.

**Nama baris tidak unik.** Banyak assignment bernama sama persis (`BANGUNAN
KOSONG`, `KAMAR KOSONG`). Identitas baris memakai nama + kolom pembeda lain,
dengan kolom status sengaja dikecualikan karena nilainya berubah setelah
diproses. Untuk alur berbasis daftar nama, pencarian yang menghasilkan banyak
baris diselesaikan dengan memilih yang nama kepala keluarganya - bagian sebelum
` / ` - persis sama dengan yang dicari.

**Susunan kolom berbeda antar survei.** Indeks kolom tidak boleh dihardcode:
di SE2026 kolom ketiga adalah Nomor Urut Bangunan/IDSBR yang unik, di Sakernas
kolom ketiga adalah PMM yang isinya hanya 0 atau 1. Indeks dicari dari nama
header. Sebagian kolom berisi gabungan (`- / 47854191` = nomor urut + IDSBR),
jadi syarat kolom boleh berupa fungsi, bukan hanya nilai yang sama persis.

**Label opsi dicocokkan sebagai awalan.** FASIH sering menambah keterangan di
belakang label - `0. Tidak Ditemukan (STOP)` pada varian keluarga, `6. Bangunan
Lainnya yang Tidak Tercakup (Tempat Judi, ...)`. Beberapa tombol juga dirender
dengan spasi antar huruf (`A P P R O V E`, `U N A P P R O V E`), sehingga
pencocokan membuang seluruh spasi lebih dulu.

**Jumlah dialog setelah BUKA tidak tetap.** Konfirmasi "Anda akan membuka
assignment ini?" selalu ada, tapi kadang menyusul "Assignment ini mempunyai
versi data lokal dan versi data server yang berbeda" dengan tombol `BUKA
ASSIGNMENT`. Karena itu yang ditunggu adalah FormGear terbuka, dan dialog apa
pun yang menyela ditangani saat terlihat - bukan mengikuti urutan tetap.
Dialog "yakin akan keluar dari halaman ini?" saat meninggalkan kuesioner
dijawab IYA lalu proses lanjut; aman karena bot tidak pernah mengubah isian.

**Satu instance punya dua entri port** di `bluestacks.conf` - `adb_port` dan
`status.adb_port` - dan koneksi bisa memakai salah satunya. Pemetaan port ke
nama jendela mencocokkan keduanya; kalau hanya satu, alur berbasis warna gagal
menemukan jendelanya.

**Angka memakai format Indonesia.** Titik adalah pemisah ribuan, koma pemisah
desimal: `1.255.952` bernilai satu juta dua ratus ribu.

**Agen uiautomator2 bisa mati di tengah run panjang.** Kalau itu terjadi setiap
pembacaan layar menggantung. Batas HTTP dipendekkan ke 60 detik dan pembacaan
layar menghidupkan ulang agen lalu mengulang sekali.

**Port ADB BlueStacks tidak tetap** - berubah saat instance di-restart. Port
dicari otomatis dari `bluestacks.conf` dan daftar port yang sedang LISTENING.

**Screenshot Android tidak tersedia** di konfigurasi ini - `screencap` gagal dan
hasilnya hitam polos. Warna baris karenanya dibaca dengan menangkap **jendela
BlueStacks sebagai jendela Windows** (`bot/warna.py`), lalu koordinat Android
dipetakan ke koordinat jendela. Kalibrasinya otomatis: lebar area Android dicari
dari tepi kiri bilah alat BlueStacks yang gelap, skala dan offset atas dihitung
dari situ.

**Warna baris bukan turunan teks kolom Status.** Keduanya bisa berbeda: baris
ber-status `REVOKED BY Pengawas` bisa tetap hijau, dan baris seperti itu justru
masih perlu di-unapprove. Peta warna yang terukur:

| Warna | RGB | Arti |
|---|---|---|
| kuning | (255, 209, 102) | Draft |
| putih | (255, 255, 255) | Open |
| biru | (12, 178, 255) | Submit |
| hijau | (6, 214, 160) | Approve |
| merah | (239, 71, 111) | Reject |

Urutan pemeriksaan warna menentukan: kuning juga berkomponen merah tinggi,
jadi ia diuji sebelum merah agar baris Draft tidak terbaca sebagai Reject.

**Satu unapprove sering belum cukup.** Siklus pertama biasanya hanya mengubah
teks status menjadi `REVOKED` sementara warnanya tetap hijau - memuat ulang
daftar pun tidak mengubahnya. Siklus kedua yang membuatnya biru. Reject tidak
begitu: satu siklus langsung merah. Karena itu alur berbasis daftar mengulang
sampai warna sasaran tercapai, dengan batas 4 percobaan.

## Keterbatasan

- Verifikasi isi kuesioner hanya bisa dilakukan **setelah** assignment dibuka.
  Baris yang gagal verifikasi jadi terbuka tanpa disetujui - dicatat sebagai
  `TERLANTAR` di log dan CSV, perlu ditangani manual.
- Syarat berbasis kolom daftar (mis. `Jumlah Usaha = 0`) diperiksa **sebelum**
  membuka, jadi kegagalannya tidak meninggalkan baris terlantar.
- Pembacaan warna butuh jendela BlueStacks terlihat, jadi alur berbasis warna
  tidak cocok dijalankan paralel dengan instance lain di depan.
