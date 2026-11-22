import os
import sys
import shutil
import zipfile
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BIN_DIR = ROOT_DIR / "bin"
BIN_DIR.mkdir(parents=True, exist_ok=True)

def reporthook(block_num, block_size, total_size):
    if total_size > 0:
        downloaded = block_num * block_size
        percent = min(100.0, downloaded * 100.0 / total_size)
        mb_down = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        sys.stdout.write(f"\r  Progression : {percent:5.1f}% ({mb_down:5.1f} / {mb_total:5.1f} Mo)")
        sys.stdout.flush()

def download_file(url, target_path, label):
    print(f"\n[+] Téléchargement de {label}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    temp_path = str(target_path) + ".downloading"
    
    with urllib.request.urlopen(req) as resp, open(temp_path, 'wb') as out_file:
        total_length = resp.headers.get('content-length')
        total_size = int(total_length) if total_length else 0
        downloaded = 0
        block_size = 64 * 1024
        
        while True:
            chunk = resp.read(block_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = min(100.0, downloaded * 100.0 / total_size)
                sys.stdout.write(f"\r  Progression : {percent:5.1f}% ({downloaded/(1024*1024):.1f} / {total_size/(1024*1024):.1f} Mo)")
                sys.stdout.flush()
    print("\n  Terminé avec succès.")
    if os.path.exists(target_path):
        os.remove(target_path)
    os.rename(temp_path, target_path)

def ensure_tools():
    print("=" * 60)
    print("      Vérification et installation des composants requis")
    print("=" * 60)

    # 1. yt-dlp
    yt_dlp_exe = BIN_DIR / "yt-dlp.exe"
    if not yt_dlp_exe.is_file() and not shutil.which("yt-dlp"):
        url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        try:
            download_file(url, yt_dlp_exe, "yt-dlp (Moteur de flux)")
        except Exception as e:
            print(f"[!] Erreur téléchargement yt-dlp : {e}")
    else:
        print("[✓] yt-dlp est prêt.")

    # 2. node.exe
    node_exe = BIN_DIR / "node.exe"
    if not node_exe.is_file() and not shutil.which("node"):
        url = "https://nodejs.org/dist/v20.18.0/win-x64/node.exe"
        try:
            download_file(url, node_exe, "Node.js (Moteur d'extraction)")
        except Exception as e:
            print(f"[!] Erreur téléchargement Node.js : {e}")
    else:
        print("[✓] Node.js est prêt.")

    # 3. FFmpeg & FFprobe
    ffmpeg_exe = BIN_DIR / "ffmpeg.exe"
    ffprobe_exe = BIN_DIR / "ffprobe.exe"
    if (not ffmpeg_exe.is_file() or not ffprobe_exe.is_file()) and not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        zip_url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        zip_temp = BIN_DIR / "ffmpeg_temp.zip"
        try:
            download_file(zip_url, zip_temp, "FFmpeg et FFprobe (Traitement audio/vidéo)")
            print("\n[+] Extraction de ffmpeg.exe et ffprobe.exe...")
            with zipfile.ZipFile(zip_temp, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    filename = os.path.basename(member)
                    if filename.lower() in ['ffmpeg.exe', 'ffprobe.exe']:
                        source = zip_ref.open(member)
                        target = open(BIN_DIR / filename, "wb")
                        with source, target:
                            shutil.copyfileobj(source, target)
                        print(f"  Extrait : {filename}")
            if zip_temp.exists():
                zip_temp.unlink()
            print("  Extraction terminée avec succès.")
        except Exception as e:
            print(f"[!] Erreur téléchargement FFmpeg : {e}")
    else:
        print("[✓] FFmpeg & FFprobe sont prêts.")

    print("\n" + "=" * 60)
    print(" Tous les outils sont configurés et opérationnels !")
    print("=" * 60)

if __name__ == "__main__":
    ensure_tools()
