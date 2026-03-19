# 🎬 TikTok Clipper

AI-powered tool yang mengubah video YouTube menjadi clip pendek viral untuk TikTok, lengkap dengan caption word-by-word ala TikTok.

## ✨ Fitur

- 📥 Download video & livestream YouTube
- 🧠 AI mendeteksi 3-5 momen paling menarik/viral
- 📐 Auto-reframe landscape → portrait (9:16)
- 💬 Caption TikTok-style (highlight kata per kata)
- 📅 Scheduling / penjadwalan otomatis
- 🎙️ Transcription gratis (Whisper lokal)

---

## 📋 Requirements

| Software | Versi | Keterangan |
|----------|-------|------------|
| Python | 3.10+ | [Download](https://www.python.org/downloads/) |
| FFmpeg | Any | [Download](https://www.gyan.dev/ffmpeg/builds/) |
| Git | Any | Opsional |

### API Key (wajib):
- **Reka AI** — [Daftar di sini](https://chat.reka.ai/api-keys) (Rekomendasi, sangat murah/gratis)

### 🍪 Wajib: Ekstensi YouTube Cookies
Untuk menghindari blokir "bot detection" dari YouTube (Error DPAPI), kamu **WAJIB** punya ekstensi export cookies:
- **Chrome/Edge**: [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/ccpbcikobfhhdjfhmckahfheobnhifhi)

---

## 🚀 Instalasi di RDP / VPS / PC Lokal

### Step 1: Install Python

```powershell
# Download Python 3.10+ dari https://www.python.org/downloads/
# Saat install, CENTANG "Add Python to PATH"
# Verifikasi:
python --version
```

### Step 2: Install FFmpeg

```powershell
# Cara 1: Download manual
# Download dari https://www.gyan.dev/ffmpeg/builds/
# Extract ke C:\ffmpeg
# Tambahkan C:\ffmpeg\bin ke System PATH

# Cara 2: Via winget (Windows 10/11)
winget install ffmpeg

# Cara 3: Via choco (jika sudah install Chocolatey)
choco install ffmpeg

# Verifikasi:
ffmpeg -version
```

### Step 3: Clone / Copy Project

```powershell
# Jika pakai Git:
git clone <repo-url> C:\clipper
cd C:\clipper

# Atau copy folder clipper ke RDP via RDP file transfer
```

### Step 4: Install Dependencies

```powershell
cd C:\clipper
pip install -r requirements.txt
```

> ⏳ Ini akan menginstall: FastAPI, yt-dlp, faster-whisper, dll.
> Pertama kali jalankan app, Whisper model (~150 MB) akan di-download otomatis.

### Step 5: Setup YouTube Cookies (Sangat Penting! 🍪)

YouTube sekarang memblokir download jika tidak ada cookies dari akun yang valid.
1. Install ekstensi **Get cookies.txt LOCALLY** di Chrome/Edge kamu.
2. Buka `youtube.com` dan pastikan kamu **sudah login**.
3. Klik ekstensinya, lalu klik **Export**.
4. Rename file yang ter-download menjadi **`cookies.txt`** (tanpa spasi).
5. Pindahkan `cookies.txt` ke dalam folder bot: `C:\clipper\cookies.txt`

### Step 6: Jalankan App

```powershell
cd C:\clipper
python app.py
```

Browser akan terbuka otomatis ke `http://localhost:8000`

---

## ⚙️ Setup Pertama Kali

1. Buka app di browser → `http://localhost:8000`
2. Klik tab **Settings**
3. Masukkan **OpenRouter API Key** (atau KIE AI Key)
4. Pilih model AI:
   - `GPT-4o Mini` — Paling murah (~$0.01/video)
   - `GPT-4o` — Lebih pintar (~$0.10/video)
   - `Claude 3.5 Sonnet` — Alternatif bagus
5. Atur settings lain sesuai kebutuhan
6. Klik **Save Settings**

---

## 🎯 Cara Pakai

### Generate Clips
1. Klik tab **Home**
2. Paste URL YouTube (video biasa atau livestream)
3. Pilih jumlah clip (3-5)
4. Klik **✨ Generate Clips**
5. Tunggu progress (~2-5 menit)
6. Preview & download clip hasil

### Schedule Job
1. Klik tab **Schedule**
2. Paste URL YouTube
3. Pilih waktu jadwal
4. Klik **📅 Schedule**

### Lihat Semua Clips
- Klik tab **Clips** → lihat semua clip yang sudah di-generate
- Clips tersimpan di folder `output/`

---

## 📂 Struktur Folder

```
clipper/
├── app.py              # Server utama
├── config.py           # Pengaturan & API keys
├── requirements.txt    # Dependencies
├── settings.json       # Settings tersimpan (auto-generated)
├── core/
│   ├── downloader.py   # Download YouTube (yt-dlp)
│   ├── transcriber.py  # Transcripsi audio (Whisper)
│   ├── detector.py     # AI deteksi highlight
│   ├── clipper.py      # Potong video + caption (FFmpeg)
│   └── scheduler.py    # Penjadwalan
├── templates/
│   └── index.html      # Halaman web
├── static/             # CSS & JavaScript
├── output/             # Hasil clip tersimpan di sini
└── temp/               # File sementara (auto-cleanup)
```

---

## 🔧 Troubleshooting

### "yt-dlp not found"
```powershell
# Install ulang via pip:
pip install yt-dlp --upgrade
```

### "FFmpeg not found"
Pastikan FFmpeg sudah di-install dan ada di PATH:
```powershell
ffmpeg -version
# Jika error, tambahkan ke PATH atau install ulang
```

### "Failed to decrypt with DPAPI" atau "Sign in to confirm you're not a bot"
Ini terjadi karena Chrome/Edge (v127+) mengunci file cookies sistem.
**Solusi 100% Berhasil:** Ekspor manual cookies-mu pakai ekstensi "Get cookies.txt LOCALLY" dari Chrome. Rename jadi `cookies.txt` dan taruh di folder bot yang sama dengan file `app.py`. Bot akan otomatis membaca file ini.

### "n challenge solving failed"
Sama seperti error di atas, YouTube mendeteksi bot karena kurangnya cookies yang valid. Cukup gunakan trik file `cookies.txt` di atas.

### "No API key configured"
Buka Settings → masukkan Reka AI API Key → Save

### Port 8000 sudah terpakai
Edit `settings.json`, ubah `server_port` ke port lain (misal 8080)

### Akses dari browser lain / PC lain
App sudah bind ke `0.0.0.0`, jadi bisa diakses dari PC lain:
```
http://<IP_RDP>:8000
```
Pastikan port 8000 dibuka di Windows Firewall:
```powershell
netsh advfirewall firewall add rule name="TikTok Clipper" dir=in action=allow protocol=tcp localport=8000
```

---

## 💰 Estimasi Biaya

| Komponen | Biaya |
|----------|-------|
| Whisper (lokal) | **GRATIS** |
| FFmpeg | **GRATIS** |
| Reka AI Core / Flash | ~$0.01 / video |

---

## 🔄 Cara Update App

Jika ada perbaikan error atau fitur baru di GitHub, kamu bisa update tanpa install ulang:

1. Buka terminal/CMD di folder bot (`C:\clipper`)
2. Tarik update terbaru:
   ```powershell
   git pull
   ```
3. Update library (opsional, jika ada peringatan module missing):
   ```powershell
   pip install -r requirements.txt --upgrade
   ```

---

## 📝 Lisensi

Personal use only.

