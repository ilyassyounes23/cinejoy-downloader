import os
import re
import sys
import json
import time
import shutil
import urllib.request
import subprocess
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response

# Résolution universelle des dossiers (compatible script Python direct OU exécutable autonome PyInstaller)
if getattr(sys, 'frozen', False):
    EXE_DIR = Path(sys.executable).resolve().parent
    if hasattr(sys, '_MEIPASS'):
        APP_DIR = Path(sys._MEIPASS)
    else:
        APP_DIR = EXE_DIR
    
    if EXE_DIR.name.lower() == 'cinejoy_app':
        BASE_DIR = EXE_DIR.parent
    else:
        BASE_DIR = EXE_DIR
else:
    APP_DIR = Path(__file__).resolve().parent
    BASE_DIR = APP_DIR.parent if APP_DIR.name.lower() == 'cinejoy_app' else APP_DIR

DOWNLOADS_DIR = BASE_DIR / "_VIDEOS_TELECHARGEES"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"

app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder=str(TEMPLATES_DIR))

# Recherche universelle et relative des exécutables nécessaires (priorité absolue au dossier bin/ embarqué)
def find_executable(name, custom_paths=None):
    candidates = [
        BASE_DIR / 'bin' / f"{name}.exe",
        APP_DIR / 'bin' / f"{name}.exe",
        BASE_DIR / f"{name}.exe",
        APP_DIR / f"{name}.exe"
    ]
    if custom_paths:
        candidates.extend(custom_paths)
    candidates.append(Path.home() / '.local' / 'bin' / f"{name}.exe")
    for p in candidates:
        if p and Path(p).is_file():
            return str(Path(p).resolve())
    found = shutil.which(name)
    if found:
        return found
    return name

YT_DLP_BIN = find_executable('yt-dlp')
FFMPEG_BIN = find_executable('ffmpeg')
NODE_BIN = find_executable('node', [
    r'C:\Program Files\nodejs\node.exe'
])

TMDB_API_KEY = "8476a7ab80ad76f0936744df0430e67c"

CACHE_EXTRACT = {}

# État global du téléchargement en cours
current_download = {
    "active": False,
    "status": "idle", # idle, downloading, converting, completed, error
    "step_label": "",
    "percent": 0.0,
    "speed": "0 MiB/s",
    "eta": "--:--",
    "total_size": "0 Mo",
    "filename": "",
    "filepath": "",
    "error_message": "",
    "logs": []
}

download_lock = threading.Lock()

def sanitize_filename(name):
    # Enlève les caractères interdits sous Windows
    return re.sub(r'[\\/*?:"<>|]', "", name).strip().replace("  ", " ")

def get_format_size_str(bytes_count):
    if not bytes_count or bytes_count <= 0:
        return "Taille inconnue"
    gb = bytes_count / (1024 ** 3)
    if gb >= 1.0:
        return f"{gb:.2f} Go"
    mb = bytes_count / (1024 ** 2)
    return f"{mb:.0f} Mo"

def fetch_tmdb_info(tmdb_id, tmdb_type="movie"):
    try:
        url = f"https://api.themoviedb.org/3/{tmdb_type}/{tmdb_id}?api_key={TMDB_API_KEY}&language=fr-FR"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            title = data.get('title') or data.get('name') or data.get('original_title') or f"{tmdb_type}_{tmdb_id}"
            poster = f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else None
            backdrop = f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get('backdrop_path') else None
            year = (data.get('release_date') or data.get('first_air_date') or '')[:4]
            overview = data.get('overview') or "Aucune description disponible."
            return {
                "title": title,
                "year": year,
                "overview": overview,
                "poster": poster,
                "backdrop": backdrop
            }
    except Exception as e:
        print(f"[TMDb Error] {e}")
        return None

def fetch_external_subtitles(tmdb_id, tmdb_type="movie"):
    subs = []
    try:
        url = f"https://subs2.wing.st/subtitles?type={tmdb_type}&tmdb={tmdb_id}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://cinejoy.pk/'})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read().decode('utf-8'))
            for item in data.get('subtitles', []):
                lang = item.get('language', 'fr')
                # On retient en priorité français et anglais pour ne pas surcharger
                if lang in ['fr', 'en', 'es']:
                    subs.append({
                        "lang": lang,
                        "label": f"{'Français' if lang=='fr' else 'Anglais' if lang=='en' else 'Espagnol'} (OpenSubtitles - {item.get('type', 'srt').upper()})",
                        "url": item.get('url'),
                        "type": item.get('type', 'srt'),
                        "source": "wing"
                    })
    except Exception as e:
        print(f"[Wing Subs Error] {e}")
    return subs

@app.route('/')
def index():
    return render_template('index.html', output_dir=str(DOWNLOADS_DIR))

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "yt_dlp": YT_DLP_BIN,
        "ffmpeg": FFMPEG_BIN,
        "node": NODE_BIN,
        "output_dir": str(DOWNLOADS_DIR)
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json or {}
    input_url = data.get('url', '').strip()

    if not input_url:
        return jsonify({"error": "Veuillez fournir une URL."}), 400

    extracted_m3u8 = None
    subtitles = []
    metadata = {}
    is_cinejoy = "cinejoy" in input_url.lower()

    # Si c'est un lien CineJoy, extraction automatique via Chrome CDP
    if is_cinejoy:
        if input_url in CACHE_EXTRACT:
            extract_res = CACHE_EXTRACT[input_url]
            extracted_m3u8 = extract_res.get('m3u8')
            subtitles = list(extract_res.get('subtitles', []))
            tmdb_id = extract_res.get('tmdbId')
            tmdb_type = extract_res.get('tmdbType', 'movie')
            if tmdb_id:
                meta = fetch_tmdb_info(tmdb_id, tmdb_type)
                if meta:
                    metadata.update(meta)
                ext_subs = fetch_external_subtitles(tmdb_id, tmdb_type)
                subtitles.extend(ext_subs)
        else:
            extractor_script = APP_DIR / "extractor.mjs"
            if not extractor_script.is_file():
                for alt in [BASE_DIR / 'cinejoy_app' / 'extractor.mjs', BASE_DIR / 'extractor.mjs']:
                    if alt.is_file():
                        extractor_script = alt
                        break
            try:
                cmd = [NODE_BIN, str(extractor_script), input_url]
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
                if proc.returncode != 0:
                    raw_err = proc.stderr.strip() or proc.stdout.strip()
                    try:
                        err_obj = json.loads(raw_err)
                        err_msg = err_obj.get('error', raw_err)
                    except:
                        err_msg = raw_err
                    return jsonify({"error": f"Erreur lors de l'extraction Cinejoy : {err_msg}"}), 500

                extract_res = json.loads(proc.stdout)
                CACHE_EXTRACT[input_url] = extract_res

                extracted_m3u8 = extract_res.get('m3u8')
                subtitles = extract_res.get('subtitles', [])

                tmdb_id = extract_res.get('tmdbId')
                tmdb_type = extract_res.get('tmdbType', 'movie')
                if tmdb_id:
                    meta = fetch_tmdb_info(tmdb_id, tmdb_type)
                    if meta:
                        metadata.update(meta)
                    ext_subs = fetch_external_subtitles(tmdb_id, tmdb_type)
                    subtitles.extend(ext_subs)

            except Exception as e:
                return jsonify({"error": f"Impossible d'extraire le flux Cinejoy : {str(e)}"}), 500
    else:
        # Lien direct m3u8 ou autre plateforme
        extracted_m3u8 = input_url

    if not extracted_m3u8:
        return jsonify({"error": "Aucun flux vidéo .m3u8 trouvé pour ce lien."}), 404

    # Analyse des formats avec yt-dlp
    try:
        ytdlp_cmd = [YT_DLP_BIN, '-J']
        # Ajout des en-têtes nécessaires si serveur lightspeed / cinejoy
        if 'lightspeed.st' in extracted_m3u8 or is_cinejoy:
            ytdlp_cmd.extend(['--referer', 'https://cinejoy.pk/', '--add-header', 'Origin: https://cinejoy.pk'])
        
        ytdlp_cmd.append(extracted_m3u8)

        proc = subprocess.run(ytdlp_cmd, capture_output=True, text=True, timeout=25)
        if proc.returncode != 0:
            return jsonify({"error": f"yt-dlp n'a pas pu analyser le flux : {proc.stderr}"}), 500

        info = json.loads(proc.stdout)
        duration = info.get('duration') or 0

        # Si pas encore de titre extrait depuis TMDb, on prend celui de yt-dlp
        if not metadata.get('title'):
            yt_title = info.get('title') or "Video_Cinejoy"
            if yt_title.lower() == 'master':
                yt_title = "Video_Telechargee"
            metadata['title'] = yt_title

        formats = info.get('formats', [])
        video_qualities = []
        audio_tracks = []

        seen_res = set()

        for f in formats:
            f_id = str(f.get('format_id'))
            vcodec = f.get('vcodec') or 'none'
            acodec = f.get('acodec') or 'none'
            resolution = f.get('resolution') or ''
            height = f.get('height') or 0
            tbr = f.get('tbr') or 0
            filesize = f.get('filesize') or f.get('filesize_approx')

            # Calcul de la taille estimée si pas fournie
            if not filesize and duration > 0 and tbr > 0:
                filesize = int((tbr * 1000 / 8) * duration)

            # Vidéo seule ou combinée
            if vcodec != 'none' and height > 0:
                if height not in seen_res:
                    seen_res.add(height)
                    
                    label_desc = "Standard"
                    is_best = False
                    if height >= 1080:
                        label_desc = "1080p Full HD (Meilleure image)"
                        is_best = True
                    elif height >= 720:
                        label_desc = "720p HD (Bonne image)"
                    elif height >= 360:
                        label_desc = "360p SD (Rapide et léger)"
                    else:
                        label_desc = f"{height}p SD"

                    video_qualities.append({
                        "id": f_id,
                        "height": height,
                        "resolution": resolution or f"{height}p",
                        "label": label_desc,
                        "size_str": get_format_size_str(filesize),
                        "bytes": filesize or 0,
                        "is_best": is_best
                    })

            # Pistes audio dédiées
            if vcodec == 'none' and (acodec != 'none' or 'audio' in f_id.lower()):
                lang = f.get('language') or 'und'
                note = f.get('format_note') or f.get('format') or f_id
                is_commentary = 'commentary' in note.lower() or 'commentary' in f_id.lower()
                
                lang_label = note
                if 'japanese' in note.lower() or 'jap' in note.lower() or lang == 'ja':
                    lang_label = "Japonais (VO Originale)"
                elif 'korean' in note.lower() or 'kor' in note.lower() or lang == 'ko':
                    lang_label = "Coréen (VO Originale)"
                elif 'english' in note.lower() or 'eng' in note.lower() or lang == 'en':
                    lang_label = "Anglais (Doublage US)"
                elif 'french' in note.lower() or 'fre' in note.lower() or lang == 'fr':
                    lang_label = "Français (VF)"

                if '7.1' in note:
                    lang_label += " 7.1 Surround"
                elif '5.1' in note:
                    lang_label += " 5.1 Surround"
                elif '2.0' in note:
                    lang_label += " 2.0 Stéréo"

                if is_commentary:
                    lang_label = f"🎙️ Commentaires : {note}"

                audio_tracks.append({
                    "id": f_id,
                    "label": lang_label,
                    "lang": lang,
                    "note": note,
                    "is_commentary": is_commentary
                })

        # Mettre les pistes principales en premier et les commentaires à la fin
        audio_tracks.sort(key=lambda a: 1 if a.get('is_commentary') else 0)

        # Tri des qualités vidéo de la plus haute à la plus basse
        video_qualities.sort(key=lambda x: x['height'], reverse=True)

        # Si aucune piste audio séparée (ex: fichier progressif standard), on met une piste par défaut
        if not audio_tracks:
            audio_tracks.append({
                "id": "default",
                "label": "Piste audio par défaut (Intégrée)",
                "lang": "default"
            })

        # Nettoyage et déduplication des sous-titres
        unique_subs = []
        seen_subs = set()
        for s in subtitles:
            key = f"{s.get('lang')}_{s.get('url')}"
            if key not in seen_subs:
                seen_subs.add(key)
                unique_subs.append(s)

        return jsonify({
            "success": True,
            "m3u8_url": extracted_m3u8,
            "metadata": metadata,
            "video_qualities": video_qualities,
            "audio_tracks": audio_tracks,
            "subtitles": unique_subs,
            "duration": duration,
            "is_cinejoy": is_cinejoy
        })

    except Exception as e:
        return jsonify({"error": f"Erreur d'analyse : {str(e)}"}), 500

def run_download_thread(params):
    global current_download
    m3u8_url = params['m3u8_url']
    video_id = params['video_id']
    audio_id = params['audio_id']
    clean_title = sanitize_filename(params['title'])
    sub_url = params.get('sub_url')
    sub_lang = params.get('sub_lang', 'fr')
    embed_sub = params.get('embed_sub', True)
    is_cinejoy = params.get('is_cinejoy', True)

    with download_lock:
        current_download["active"] = True
        current_download["status"] = "downloading"
        current_download["percent"] = 0.0
        current_download["speed"] = "0 MiB/s"
        current_download["eta"] = "--:--"
        current_download["total_size"] = ""
        current_download["filename"] = f"{clean_title}.mp4"
        current_download["filepath"] = str(DOWNLOADS_DIR / f"{clean_title}.mp4")
        current_download["error_message"] = ""
        current_download["logs"] = ["[System] Initialisation du téléchargement..."]

    # Construction de l'argument de format yt-dlp
    if audio_id and audio_id != "default":
        format_spec = f"{video_id}+{audio_id}"
    else:
        format_spec = video_id

    out_template = str(DOWNLOADS_DIR / f"{clean_title}.%(ext)s")

    cmd = [
        YT_DLP_BIN,
        '--newline',
        '-N', '8',
        '-f', format_spec,
        '-o', out_template,
        '--merge-output-format', 'mp4'
    ]

    if is_cinejoy or 'lightspeed.st' in m3u8_url:
        cmd.extend(['--referer', 'https://cinejoy.pk/', '--add-header', 'Origin: https://cinejoy.pk'])

    cmd.append(m3u8_url)

    current_download["logs"].append(f"[System] Commande : {' '.join(cmd)}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        for line in proc.stdout:
            line_str = line.strip()
            if not line_str:
                continue

            with download_lock:
                current_download["logs"].append(line_str)
                # On garde les 200 dernières lignes de logs
                if len(current_download["logs"]) > 200:
                    current_download["logs"] = current_download["logs"][-200:]

                # Analyse de l'étape
                if 'Destination:' in line_str:
                    if 'audio' in line_str.lower() or '.faudio' in line_str.lower():
                        current_download["step_label"] = "Étape 2/2 : Téléchargement Audio"
                    else:
                        current_download["step_label"] = "Étape 1/2 : Téléchargement Vidéo HD"
                elif '[Merger]' in line_str or 'Merging formats' in line_str:
                    current_download["status"] = "merging"
                    current_download["step_label"] = "Fusion Vidéo + Audio en cours..."
                    current_download["speed"] = "Écriture disque"
                    current_download["eta"] = "En cours"
                    current_download["logs"].append("[System] Téléchargements terminés ! Fusion finale des flux vidéo et audio en cours (FFmpeg)...")
                elif 'Deleting original file' in line_str:
                    current_download["step_label"] = "Finalisation du fichier..."
                    current_download["logs"].append("[System] Nettoyage et validation du fichier MP4 final...")

                # Analyse de la progression : [download]  45.2% of  7.54GiB at 9.86MiB/s ETA 00:03:15
                match_pct = re.search(r'\[download\]\s+([\d\.]+)%', line_str)
                if match_pct:
                    try:
                        current_download["percent"] = float(match_pct.group(1))
                    except:
                        pass

                match_spd = re.search(r'at\s+([0-9\.]+\s*(?:K|M|G)iB/s)', line_str)
                if match_spd:
                    current_download["speed"] = match_spd.group(1)

                match_eta = re.search(r'ETA\s+([\d:]+)', line_str)
                if match_eta:
                    current_download["eta"] = match_eta.group(1)

                match_size = re.search(r'of\s+~?\s*([0-9\.]+\s*(?:K|M|G)iB)', line_str)
                if match_size:
                    current_download["total_size"] = match_size.group(1)

        proc.wait()

        if proc.returncode != 0:
            with download_lock:
                current_download["status"] = "error"
                current_download["error_message"] = f"Erreur yt-dlp (Code {proc.returncode})"
            return

        # Gestion des sous-titres si demandés
        if sub_url:
            with download_lock:
                current_download["status"] = "converting"
                current_download["logs"].append(f"[System] Téléchargement des sous-titres ({sub_lang})...")

            sub_ext = "vtt" if ".vtt" in sub_url.lower() else "srt"
            sub_file = DOWNLOADS_DIR / f"{clean_title}.{sub_lang}.{sub_ext}"

            try:
                sub_req = urllib.request.Request(
                    sub_url,
                    headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://cinejoy.pk/', 'Origin': 'https://cinejoy.pk'}
                )
                with urllib.request.urlopen(sub_req, timeout=10) as s_res:
                    sub_file.write_bytes(s_res.read())
                current_download["logs"].append(f"[System] Sous-titres enregistrés : {sub_file.name}")

                # Incrustation / Muxing avec ffmpeg si explicitement activé
                final_video = DOWNLOADS_DIR / f"{clean_title}.mp4"
                if embed_sub and final_video.exists():
                    current_download["logs"].append("[System] Incrustation FFmpeg en cours dans le fichier MP4...")
                    muxed_video = DOWNLOADS_DIR / f"{clean_title}_temp_sub.mp4"
                    
                    ffmpeg_cmd = [
                        FFMPEG_BIN, '-y', '-nostdin',
                        '-i', str(final_video),
                        '-i', str(sub_file),
                        '-map', '0',
                        '-map', '1:0',
                        '-c', 'copy',
                        '-c:s', 'mov_text',
                        '-metadata:s:s:0', f'language={sub_lang}',
                        str(muxed_video)
                    ]
                    
                    try:
                        mux_proc = subprocess.Popen(
                            ffmpeg_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True
                        )
                        last_log_time = 0
                        for line in mux_proc.stdout:
                            line_str = line.strip()
                            if not line_str:
                                continue
                            match_time = re.search(r'time=([\d:.]+)', line_str)
                            match_spd = re.search(r'speed=\s*([\d.]+x)', line_str)
                            now = time.time()
                            if match_time and (now - last_log_time > 1.2):
                                last_log_time = now
                                spd_val = match_spd.group(1) if match_spd else "rapide"
                                with download_lock:
                                    current_download["step_label"] = f"Assemblage sous-titres ({match_time.group(1)} à {spd_val})"
                                    current_download["speed"] = spd_val
                                    current_download["logs"].append(f"[FFmpeg] Assemblage : position {match_time.group(1)} (vitesse {spd_val})")
                                    if len(current_download["logs"]) > 200:
                                        current_download["logs"] = current_download["logs"][-200:]
                        
                        mux_proc.wait()
                        if mux_proc.returncode == 0 and muxed_video.exists():
                            final_video.unlink()
                            muxed_video.rename(final_video)
                            current_download["logs"].append("[System] Sous-titres intégrés dans le MP4 avec succès !")
                        else:
                            current_download["logs"].append(f"[Warning] Muxing ffmpeg code {mux_proc.returncode}, sous-titres conservés en fichier .srt séparé.")
                    except Exception as fe:
                        current_download["logs"].append(f"[Warning] Erreur muxing ffmpeg : {fe}")
                else:
                    current_download["logs"].append("[System] Sous-titres conservés en fichier .srt séparé (Instantané & 100% compatible tous lecteurs) !")
            except Exception as se:
                current_download["logs"].append(f"[Warning] Erreur sous-titres : {se}")

        with download_lock:
            current_download["status"] = "completed"
            current_download["percent"] = 100.0
            current_download["eta"] = "00:00"
            current_download["logs"].append("[System] Téléchargement et assemblage terminés avec succès !")

    except Exception as e:
        with download_lock:
            current_download["status"] = "error"
            current_download["error_message"] = str(e)
            current_download["logs"].append(f"[System Error] {str(e)}")

@app.route('/api/download', methods=['POST'])
def start_download():
    global current_download
    data = request.json or {}

    with download_lock:
        if current_download["active"] and current_download["status"] in ["downloading", "converting"]:
            return jsonify({"error": "Un téléchargement est déjà en cours."}), 409

    thread = threading.Thread(target=run_download_thread, args=(data,), daemon=True)
    thread.start()

    return jsonify({"success": True, "message": "Téléchargement démarré."})

@app.route('/api/progress')
def progress():
    def event_stream():
        last_log_count = 0
        while True:
            with download_lock:
                new_logs = current_download["logs"][last_log_count:]
                last_log_count = len(current_download["logs"])
                
                payload = {
                    "active": current_download["active"],
                    "status": current_download["status"],
                    "step_label": current_download.get("step_label", ""),
                    "percent": current_download["percent"],
                    "speed": current_download["speed"],
                    "eta": current_download["eta"],
                    "total_size": current_download["total_size"],
                    "filename": current_download["filename"],
                    "filepath": current_download["filepath"],
                    "error_message": current_download["error_message"],
                    "new_logs": new_logs
                }
            
            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(0.4)

    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/api/open-folder', methods=['POST'])
def open_folder():
    try:
        os.startfile(str(DOWNLOADS_DIR))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/open-file', methods=['POST'])
def open_file():
    data = request.json or {}
    filepath = data.get('filepath') or current_download.get('filepath')
    if filepath and os.path.exists(filepath):
        try:
            os.startfile(filepath)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Fichier introuvable."}), 404

if __name__ == '__main__':
    port = 5000
    print(f"===========================================================")
    print(f" CineJoy & Video Downloader Web UI")
    print(f" Serveur disponible sur : http://localhost:{port}")
    print(f" Dossier de sortie : {DOWNLOADS_DIR}")
    print(f"===========================================================")
    app.run(host='127.0.0.1', port=port, debug=False, threaded=True)
