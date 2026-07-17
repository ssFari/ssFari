# Snake Multi-Pass Eating + Loop Reset

**Tanggal:** 2026-07-16
**Repo:** `ssFari/ssFari` (GitHub profile repo)
**Pemilik:** Muhammad Safari Luthfi Siregar (`@ssFari`)
**Basis:** Iterasi atas `snake.py` yang sudah ada (lihat `2026-07-14-custom-snake-generator-design.md`).

## Tujuan

Memperbaiki dua hal pada generator ular custom:

1. **Loop tidak reset** (cacat sekarang): sel kontribusi yang termakan pakai
   `animation: eat{lv} ... forwards` (sekali jalan lalu diam kosong), sementara
   segmen ular loop `infinite`. Akibatnya setelah sapuan pertama (~22 dtk) grid
   jadi kosong permanen dan ular menyapu grid kosong selamanya. Harusnya sel
   **tumbuh kembali** saat loop sehingga animasi berulang mulus sampai hari
   terakhir (kolom paling kanan).
2. **Cara makan lebih ekspresif**: ular makan **kontribusi terkecil dulu, baru
   yang terbesar** — multi-pass progresif per level.

## Ruang Lingkup

### Termasuk
1. `build_timeline` ditulis ulang → model **multi-pass** (satu sapuan per level
   yang ada di data).
2. Mekanik makan: sapuan ke-*n* hanya memakan sel level-*n*; level lebih tinggi
   **dilewati** (ular meluncur di atasnya, sel tetap terlihat).
3. **Tumbuh carry-over**: panjang dibawa terus lintas sapuan sampai cap 16. Warna
   badan = warna makanan yang menempel di jejak (efek "menelan mengalir"): tiap
   segmen menampilkan warna makanan yang tertelan `k` langkah lalu, jadi badan
   berupa gradien "rekaman makanan terakhir". Diimplementasi lewat **satu**
   timeline `swallow` bersama + `animation-delay` per segmen — file-light dan
   otomatis menangani total makanan **> 16** (jendela geser), tak bisa dicapai
   oleh warna-tetap-per-segmen.
4. **Fase reset** di akhir sapuan terakhir: sel termakan tumbuh kembali, ular
   menyusut ke 1 segmen, lalu loop.
5. Pacing: turunkan `STEP_MS` agar total loop wajar (~20–30 dtk) meski multi-pass.
6. Update unit test untuk model baru.

### Dikecualikan
- Perubahan jalur dasar (`build_path` tetap zig-zag kronologis).
- Perubahan `today.py` / kartu neofetch.
- Perubahan tema warna (dark navy / light gray tetap).
- Perubahan `snake.yml` (workflow tidak berubah).

## Keputusan Desain (terkunci)
- **Mekanik makan:** multi-pass per level. Jalur zig-zag tetap; sapuan-*n* makan
  level-*n* saja, lewati (pass-over) level lebih tinggi.
- **Arah sapuan boustrophedon:** sapuan berselang dibalik arahnya (pass genap
  maju, pass ganjil mundur) supaya kepala mengalir kontinu di batas antar-pass
  tanpa teleport/streak. "Terkecil dulu" tetap utuh (urutan level tak berubah);
  hanya urutan kunjungan sel dalam pass ganjil yang mundur.
- **Jumlah pass:** hanya level yang **benar-benar ada** di grid. Akun level 1–2 →
  2 pass; tidak selalu 4.
- **Panjang:** carry-over lintas pass sampai cap 16; ekor memudar FIFO setelah 16.
- **Warna segmen:** timeline `swallow` bersama + delay per segmen; badan jadi
  gradien "rekaman makanan terakhir" yang menempel di jejak. Menangani total
  makanan > 16 lewat sliding window.
- **Reset:** fase regrow singkat di akhir → loop `infinite`.

## Arsitektur

File yang berubah:
```
snake.py               # build_timeline + render_svg ditulis ulang untuk multi-pass
tests/test_snake.py    # test disesuaikan model baru
```
`fetch_calendar`, `build_grid`, `build_path`, `_xy`, `_write`, `main`, `THEMES`
tidak berubah bentuk antarmukanya (kecuali `main` tetap memanggil pipeline yang sama).

### Model Timeline (baru)

```
present_levels = sorted({ lv for kolom in grid for lv in kolom if lv > 0 })
path = build_path(grid)                      # 371 sel, zig-zag

frames = []                                  # daftar frame animasi berurut
for L in present_levels:                     # satu pass per level
    for cell in path:
        frames.append({ "cell": cell,
                        "is_eat": grid[cell] == L,
                        "food_level": L if grid[cell] == L else None })
reset_start = len(frames)
# fase reset: RESET_FRAMES frame "diam di sel terakhir" untuk regrow + shrink
frames += [ { "cell": path[-1], "is_eat": False, "food_level": None } ] * RESET_FRAMES

eat_events = [ (i, f["food_level"]) for i, f in enumerate(frames) if f["is_eat"] ]
```

Timeline dict (kunci baru):
| kunci | isi |
|---|---|
| `frames` | list frame `{cell, is_eat, food_level}` lintas semua pass + reset |
| `total` | `len(frames)` |
| `eat_events` | list `(frame_index, food_level)` global, terurut |
| `present_levels` | level yang ada (untuk info/test) |
| `reset_start` | indeks frame awal fase reset |
| `max_len` | 16 |

`snake_length(eaten)` tetap `min(eaten+1, MAX_LEN)`; `eaten` = kumulatif lintas pass.
Segmen ke-*k* **muncul** (opacity) pada `eat_events[k-1]`; **warnanya** datang dari
timeline `swallow` bersama yang di-delay `k×STEP_MS` (bukan warna fix di rect).

## Model Animasi (CSS)

- **`move`**: `@keyframes` posisi melintasi **seluruh `frames`** (multi-pass +
  reset), bukan satu jalur 371. Segmen ke-*k* `animation-delay: k×STEP_MS`.
- **`swallow` (bersama, stepwise)**: `@keyframes fill` yang berubah **hanya di
  frame makan** dan **menahan** warna di antaranya (piecewise-constant), jadi
  warna makanan menempel di jejak alih-alih menyapu. Segmen ke-*k* memakainya
  dengan `animation-delay: k×STEP_MS`. Segmen ke-0 (kepala) tidak pakai swallow
  (tetap warna aksen `head`).
- **`grow{k}` (per segmen, opacity saja)**: muncul di `eat_events[k-1]`, tetap
  tampil, lalu **opacity→0 di fase reset** (ular menyusut ke 1 saat loop).
- **Sel kontribusi (grafik permanen)**: keyframe **loop penuh** (bukan
  `forwards`). Warna level tampil **permanen**; hanya **meredup sesaat** (dip
  transien selebar `FLASH_FRAMES`) tepat saat kepala melahapnya, lalu **langsung
  pulih** — tidak ditahan kosong sampai reset. Jadi grafik kontribusi selalu
  terbaca sepanjang loop; ular yang lewat hanya "mengedipkan" sel. Semua sinkron
  `infinite`.
- **Palet kontras**: level 1–4 dibuat jelas berbeda dari `empty` (terutama
  level-1) agar kontribusi "pop"; dark = ramp biru navy, light = ramp abu.
- **Durasi:** semua animasi = `total × STEP_MS`, `infinite`, sinkron. `STEP_MS`
  diturunkan ke **20ms** agar worst-case 4 level (`4 × 371 + reset`) ≈ 30 dtk
  (profil dengan lebih sedikit level → lebih pendek). Jumlah sapuan bergantung
  pada **berapa level distinct** yang hadir, bukan kepadatan grid.
- **Kepala:** segmen ke-0 tetap warna aksen `head` agar arah jelas.

## Data Flow
```
snake.yml (tak berubah) → snake.py
  fetch_calendar → build_grid → build_path
  build_timeline (MULTI-PASS: present_levels × path + reset)
  render_svg × 2 (dark, light)  ← keyframe multi-pass, sel loop penuh
→ dist/*.svg → branch output → README menampilkan ular
```

## Error Handling
- **Kontribusi kosong** (`present_levels == []`): tidak ada pass makan. Ular tetap
  satu segmen menyapu satu sapuan kosong lalu loop; tidak crash, tidak ada
  `eat_events`.
- Query gagal / token tak ada: perilaku lama dipertahankan (exit non-zero via
  `run_query` / `KeyError` env) — di luar perubahan ini.
- Ukuran SVG membesar (keyframe `move` ~N× lebih panjang). Diverifikasi wajar
  (< beberapa ratus KB) lewat test smoke + render sintetis.

## Testing (pytest, TDD)
- `build_timeline` multi-pass:
  - `present_levels` benar (hanya level yang ada, terurut).
  - jumlah `frames` = `len(present_levels) × len(path) + RESET_FRAMES`.
  - sapuan-*n* menandai `is_eat` hanya pada sel level-*n*; level lain di pass itu
    `is_eat=False`.
  - `eat_events` terurut naik per level (semua level-1 sebelum level-2, dst).
  - `food_level` tiap eat event = level sel yang dimakan.
- `snake_length`: carry-over kumulatif, cap 16.
- Kosong: `present_levels == []` → tidak ada `eat_events`, tidak crash,
  `frames` = satu sapuan + reset.
- `render_svg`:
  - SVG well-formed, jumlah `<rect>` sel = `len(path)`.
  - jumlah segmen (`rx="3"`) = `min(16, len(eat_events)+1)`.
  - sel kontribusi **tidak** pakai `forwards` (regresi loop-reset) — keyframe
    loop penuh ada.
  - `@keyframes swallow` ada; segmen non-kepala memakainya dengan delay per segmen.
  - dua tema (dark & light) menghasilkan warna berbeda.
  - nol placeholder, ukuran wajar.

## Kriteria Sukses
- Ular menyapu kontribusi asli, **makan terkecil dulu lalu terbesar** (multi-pass),
  badan **tumbuh carry-over** dengan **warna per makanan**, di akhir siklus grid
  **tumbuh kembali** dan animasi **loop mulus** (tidak lagi berhenti di grid
  kosong). Dua tema navy/gray. Regenerate otomatis via workflow yang sudah ada.
