# Custom Contribution-Snake Generator

**Tanggal:** 2026-07-14
**Repo:** `ssFari/ssFari` (GitHub profile repo)
**Pemilik:** Muhammad Safari Luthfi Siregar (`@ssFari`)

## Tujuan

Mengganti animasi ular `Platane/snk` dengan **generator custom** yang melahap
grafik kontribusi asli, di mana **badan ular tumbuh saat makan** dan **warna
badan mengikuti warna makanan** yang ditelan — sesuatu yang tidak didukung
`Platane/snk`. Output: SVG animasi self-contained, dua tema (dark navy / light
gray), tampil di profil lewat `README` (branch `output`).

## Ruang Lingkup

### Termasuk
1. `snake.py`: fetch `contributionCalendar` asli via GraphQL → SVG animasi.
2. Mekanik **tumbuh + ekor memudar** (maks ~16 segmen).
3. Jalur **sapuan kronologis** (kolom minggu kiri→kanan, zig-zag naik-turun).
4. **Warna badan = warna makanan** (efek "menelan" yang mengalir turun).
5. Dua tema: dark (navy) & light (gray).
6. Ganti `snake.yml` agar menjalankan `snake.py` (bukan `Platane/snk`).
7. Unit test (pytest, TDD) untuk logika path/grid/timeline/render.

### Dikecualikan
- Pertumbuhan tanpa batas (ditolak: grid jadi penuh/berantakan).
- Jalur "pemburu" / boustrophedon horizontal (ditolak; dipilih kronologis).
- Perubahan pada kartu neofetch (`today.py`) — di luar lingkup.

## Keputusan Desain (terkunci)
- **Tumbuh:** +1 segmen tiap makan, cap ~16, ekor memudar agar panjang stabil.
- **Jalur:** sapuan kronologis vertikal, kolom kiri→kanan.
- **Tech:** Python (konsisten `today.py`), SVG beranimasi CSS `@keyframes`.
- **Ringan-file:** semua segmen berbagi *satu* set keyframes jalur/warna, beda
  hanya `animation-delay` per segmen (segmen ke-k tertinggal k langkah).

## Arsitektur

### File
```
snake.py                     # generator baru
tests/test_snake.py          # unit test
.github/workflows/snake.yml  # ganti: Platane/snk → snake.py
```

### Komponen (`snake.py`)
| Fungsi | Tugas | Depends |
|---|---|---|
| `fetch_calendar(login, token)` | GraphQL `contributionCalendar` → list hari `{date, count, level}` | GitHub API |
| `build_grid(days)` | Matriks kolom×baris `(col,row)→level`; toleran jumlah minggu ≠ 53 | — |
| `build_path(grid)` | Urutan sel sapuan kronologis, zig-zag, kunjungi semua sel tepat sekali | `build_grid` |
| `build_timeline(path)` | Per langkah: posisi head, event makan, warna makanan; mekanik tumbuh+cap+fade | `build_path` |
| `render_svg(grid, timeline, theme)` | Rakit SVG: `<rect>` per sel + `<style>` `@keyframes` (shared + delay) | `build_timeline` |
| `main()` | Baca env token; generate dark & light → `dist/*.svg` | semua |

## Data Flow
```
snake.yml (cron harian / dispatch / push)
  → snake.py
      fetch_calendar (ACCESS_TOKEN) → 371 hari + level(0-4)
      build_grid → build_path → build_timeline
      render_svg × 2 (dark navy, light gray)
  → dist/github-snake-dark.svg + github-snake.svg
  → publish branch `output` (crazy-max/ghaction-github-pages)
README <picture> (raw output branch) → profil menampilkan ular
```

## Model Animasi

- **Sel:** `<rect>` 11×11px, gap 2px. Warna = level (0–4) → gradien tema.
  - Dark: `#0d1b2a → #1e3a5f → #2e5480 → #4a7ab5 → #6ea3e0`
  - Light: `#e5e7eb → #c3ccd6 → #9aa7b5 → #6b7a8c → #3d4b5a`
- **Ular:** 16 segmen `<rect>`; semua pakai `@keyframes move` (371 posisi jalur),
  segmen ke-k `animation-delay: -(k×step)`.
- **Tumbuh (1→16):** `@keyframes` opacity — segmen k `opacity:0` hingga `k×step`,
  lalu `1`.
- **Ekor memudar & stabil:** setelah 16, segmen ekor opacity lebih rendah +
  transisi; di ujung jalur segmen menghilang (opacity→0) saat kepala selesai.
- **Warna menelan:** `@keyframes swallow` untuk `fill`, shared + delay per segmen;
  warna makanan mengalir turun badan. Sel termakan pudar jadi kosong
  (`@keyframes eaten`).
- **Timing:** step ≈ 60ms → ~22s per putaran, `infinite loop`. Step = konstanta.
- **Kepala:** aksen tegas (dark `#8ab4f0`, light `#3d4b5a`) agar arah jelas.

## Error Handling
- Query gagal/rate-limited → exit non-zero, pesan jelas; SVG lama di `output`
  dipertahankan (tidak menimpa dengan file korup).
- Kontribusi kosong → ular tetap menyapu tanpa event makan; tidak crash.
- Token tak ada → error eksplisit.
- Hari ≠ 371 (kabisat / akun baru) → `build_grid` pakai jumlah minggu dari API.

## Testing (pytest, TDD)
- `build_grid`: matriks benar (termasuk <371 hari).
- `build_path`: sapuan kronologis benar; kunjungi semua sel tepat sekali.
- `build_timeline`: tumbuh 1→16, cap 16, event makan di sel berisi + warna benar,
  delay per-segmen konsisten.
- `render_svg`: smoke — SVG valid, jumlah `<rect>` sesuai, `@keyframes` ada, nol
  placeholder, ukuran wajar.
- `fetch_calendar`: payload GraphQL tiruan (pola sama seperti test `extract_stats`).
- `main()` tipis; diverifikasi lewat run workflow nyata.

## Kriteria Sukses
- Profil `github.com/ssFari` menampilkan ular yang: menyapu kontribusi asli urut
  waktu, **badan memanjang saat makan**, **warna badan = warna makanan**, ekor
  memudar stabil, dua tema (navy/gray), loop mulus — dan regenerate otomatis
  via workflow.
