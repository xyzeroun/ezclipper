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

### API Key (pilih salah satu):
- **OpenRouter** — [Daftar di sini](https://openrouter.ai/) (rekomendasi, ~$0.01-0.05/video)
- **KIE AI** — [Daftar di sini](https://kie.ai/) (alternatif)

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

### Step 5: Jalankan App

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

### "No API key configured"
Buka Settings → masukkan OpenRouter atau KIE AI API Key → Save

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
| OpenRouter GPT-4o-mini | ~$0.01-0.05 / video |
| OpenRouter GPT-4o | ~$0.10-0.50 / video |

---

## 📝 Lisensi

Personal use only.
