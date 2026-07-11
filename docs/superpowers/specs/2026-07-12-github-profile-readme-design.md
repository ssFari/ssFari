# GitHub Profile README — Self-Updating (ala Andrew6rant)

**Tanggal:** 2026-07-12
**Repo:** `ssFari/ssFari` (GitHub profile repo)
**Pemilik:** Muhammad Safari Luthfi Siregar (`@ssFari`)

## Tujuan

Mengganti README profil GitHub yang sekarang (basic) dengan profil dinamis
bergaya Andrew6rant: sebuah **kartu "neofetch" self-updating** bertema terminal
hijau yang menarik data live dari GitHub API, plus komponen pelengkap (typing
header, snake animation, tech badges, social links).

## Ruang Lingkup

### Termasuk
1. Kartu neofetch text-only, dual light/dark, auto-update via GitHub Actions.
2. Metrik live: uptime (umur akun), repos, stars, followers, commits, contributions.
3. Typing SVG header.
4. Snake contribution animation.
5. Tech stack badges (statik).
6. Social links (statik).

### Dikecualikan (keputusan eksplisit pemilik)
- **Lines of Code (LOC)** — tidak dihitung (menghindari kompleksitas caching + histori commit).
- **ASCII art potret** — kartu text-only, tanpa gambar/portrait.

## Arsitektur

### Struktur file
```
├── README.md                 # markdown utama, menyusun semua komponen
├── today.py                  # script: GitHub API → isi placeholder SVG
├── requirements.txt          # dependency python (requests, python-dateutil)
├── dark_mode.svg             # template kartu neofetch (gelap) — di-update script
├── light_mode.svg            # template kartu neofetch (terang) — di-update script
└── .github/workflows/
    ├── update-card.yml       # cron + on-push → jalankan today.py, commit SVG
    └── snake.yml             # generate snake animation → branch `output`
```

### Komponen & tanggung jawab

**1. `today.py` (mesin data)**
- Input: env `ACCESS_TOKEN` (PAT), `GITHUB_ACTOR` / username `ssFari`.
- Query GitHub GraphQL API v4 untuk:
  - `createdAt` → hitung `uptime` (format "X years, Y months, Z days").
  - `repositories.totalCount` → `repos`.
  - total `stargazerCount` seluruh repo milik user → `stars`.
  - `followers.totalCount` → `followers`.
  - `contributionsCollection.totalCommitContributions` → `commits`.
  - `repositoriesContributedTo.totalCount` → `contributions`.
- Buka `dark_mode.svg` & `light_mode.svg`, ganti placeholder token
  (`{{ uptime }}`, `{{ repos }}`, `{{ stars }}`, `{{ followers }}`,
  `{{ commits }}`, `{{ contributions }}`) dengan nilai terhitung, tulis balik.
- Idempoten: menjalankan ulang dengan data sama menghasilkan file sama.

**2. Template SVG (`dark_mode.svg`, `light_mode.svg`)**
- Layout kotak bergaya terminal: header `safari@github`, baris prompt `>`,
  font monospace, ukuran ~460×xxx.
- Dark: latar gelap (`#0d1117`-ish), teks hijau (`#00ff9c`/`#39d353`).
- Light: latar terang, teks hijau gelap agar kontras.
- Berisi token placeholder yang diisi `today.py`.

**3. `update-card.yml`**
- Trigger: `schedule` (cron tiap 12 jam), `push` ke `main`, `workflow_dispatch`.
- Steps: checkout → setup Python → `pip install -r requirements.txt` →
  jalankan `today.py` (env `ACCESS_TOKEN` dari secret) → commit & push SVG
  yang berubah (skip jika tidak ada perubahan).
- Butuh permission `contents: write`.

**4. `snake.yml`**
- Trigger: `schedule` (cron harian) + `workflow_dispatch`.
- Pakai `Platane/snk` → generate `github-snake.svg` (dark) &
  `github-snake-dark.svg`/light → push ke branch `output`.

**5. `README.md`**
- Typing header via `readme-typing-svg` (query: baris "Muhammad Safari
  Luthfi Siregar" + "Always Learning").
- Embed kartu dual-mode:
  ```html
  <img src="./dark_mode.svg#gh-dark-mode-only">
  <img src="./light_mode.svg#gh-light-mode-only">
  ```
- Tech badges (shields.io): TypeScript, JavaScript, Next.js, React,
  Tailwind CSS, Node.js, Bun, PostgreSQL, Git.
- Snake embed dari branch `output` (dual-mode).
- Social: IG `hi_ssfari`, X `ssFari1`, Web `ssfari.dev`, GitHub `ssFari`.

## Data Flow

```
GitHub Actions (cron 12h / push)
  → today.py  ── query GraphQL (ACCESS_TOKEN) ──▶ metrik
              ── isi placeholder ──▶ dark_mode.svg + light_mode.svg
  → commit SVG kembali ke repo
README.md  ── embed SVG (#gh-dark/light-mode-only) ──▶ viewer lihat versi terbaru
```

Snake berjalan pada workflow terpisah dengan siklusnya sendiri.

## Error Handling
- `today.py`: jika query API gagal / rate-limited → exit non-zero dengan pesan
  jelas, workflow gagal (tidak commit data korup). Pertahankan SVG lama.
- Nilai kosong/None dari API → fallback `0` agar SVG tetap valid.
- Workflow commit: gunakan guard "no changes → skip commit" agar tidak bikin
  commit kosong tiap jalan.

## Prasyarat Setup (dilakukan pemilik, dipandu)
1. Buat **Personal Access Token** (classic) scope `repo` + `read:user`.
2. Simpan sebagai repo secret `ACCESS_TOKEN`.
3. Settings → Actions → Workflow permissions → **Read and write**.

## Testing / Verifikasi
- `today.py` dapat dijalankan lokal dengan `ACCESS_TOKEN` di env → cek SVG
  terisi angka nyata (bukan placeholder).
- Validasi SVG hasil terbuka benar di browser (light & dark).
- Setelah push: cek Actions berjalan hijau, cek render README di halaman profil
  GitHub (mode terang & gelap).

## Kriteria Sukses
- Halaman profil `github.com/ssFari` menampilkan: typing header, kartu neofetch
  ber-angka live yang benar, snake animation, badges, social — dan kartu
  ter-update otomatis tanpa intervensi manual.
