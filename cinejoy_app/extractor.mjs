import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

// Recherche de Google Chrome ou Microsoft Edge sur Windows (standard et par utilisateur)
function getBrowserPath() {
  const localAppData = process.env.LOCALAPPDATA || '';
  const candidates = [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    localAppData ? path.join(localAppData, "Google\\Chrome\\Application\\chrome.exe") : null,
    localAppData ? path.join(localAppData, "Microsoft\\Edge\\Application\\msedge.exe") : null
  ];
  for (const p of candidates) {
    if (p && fs.existsSync(p)) return p;
  }
  return null;
}

function killProcessTree(pid) {
  if (!pid) return;
  try {
    spawn('taskkill', ['/pid', String(pid), '/T', '/F'], { stdio: 'ignore' });
  } catch (e) {}
}

export async function extractCinejoy(targetUrl, timeoutMs = 25000) {
  const browserPath = getBrowserPath();
  if (!browserPath) {
    throw new Error("Navigateur Google Chrome ou Microsoft Edge introuvable.");
  }

  const port = Math.floor(Math.random() * 800) + 9100;
  const tempProfileDir = path.join(process.env.TEMP || 'C:\\Windows\\Temp', `cj_prof_${port}_${Date.now()}`);

  let chromeProc = null;
  let ws = null;

  try {
    chromeProc = spawn(browserPath, [
      `--remote-debugging-port=${port}`,
      '--headless=new',
      '--disable-gpu',
      '--no-sandbox',
      '--disable-web-security',
      '--blink-settings=imagesEnabled=false', // Désactive le chargement d'images pour aller 3x plus vite
      '--mute-audio',
      '--disable-dev-shm-usage',
      `--user-data-dir=${tempProfileDir}`,
      'about:blank'
    ], { stdio: 'ignore' });

    let wsUrl = null;
    for (let i = 0; i < 35; i++) {
      await new Promise(r => setTimeout(r, 150));
      try {
        const res = await fetch(`http://127.0.0.1:${port}/json/list`);
        const tabs = await res.json();
        if (tabs && tabs[0]?.webSocketDebuggerUrl) {
          wsUrl = tabs[0].webSocketDebuggerUrl;
          break;
        }
      } catch (e) {}
    }

    if (!wsUrl) {
      throw new Error("Impossible de se connecter au navigateur en arrière-plan.");
    }

    const result = {
      targetUrl,
      m3u8: null,
      subtitles: [],
      tmdbId: null,
      tmdbApiKey: null,
      tmdbType: targetUrl.includes('/tv/') ? 'tv' : 'movie'
    };

    const tmdbMatch = targetUrl.match(/watch\/(movie|tv)\/(\d+)/);
    if (tmdbMatch) {
      result.tmdbType = tmdbMatch[1];
      result.tmdbId = tmdbMatch[2];
    }

    ws = new WebSocket(wsUrl);
    let msgId = 1;

    const streamFoundPromise = new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        if (result.m3u8) resolve(result);
        else reject(new Error("Délai d'attente dépassé sans trouver de flux vidéo m3u8."));
      }, timeoutMs);

      ws.onopen = () => {
        ws.send(JSON.stringify({ id: msgId++, method: 'Network.enable' }));
        ws.send(JSON.stringify({ id: msgId++, method: 'Page.enable' }));
        ws.send(JSON.stringify({ id: msgId++, method: 'Page.navigate', params: { url: targetUrl } }));
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.method === 'Network.requestWillBeSent') {
            const reqUrl = msg.params.request.url;

            // Détection du master m3u8
            if (reqUrl.includes('.m3u8') && !result.m3u8) {
              if (reqUrl.includes('master.m3u8') || reqUrl.includes('/hls/')) {
                result.m3u8 = reqUrl;
                // Attend 1.2s pour récupérer les sous-titres associés
                setTimeout(() => resolve(result), 1200);
              }
            }

            // Détection des sous-titres VTT lightspeed
            if (reqUrl.includes('/subtitles/sub-') && reqUrl.endsWith('.vtt')) {
              const langMatch = reqUrl.match(/sub-([a-z]{2})\.vtt/);
              const lang = langMatch ? langMatch[1] : 'vtt';
              if (!result.subtitles.some(s => s.url === reqUrl)) {
                result.subtitles.push({
                  lang,
                  label: getLangLabel(lang),
                  url: reqUrl,
                  type: 'vtt',
                  source: 'lightspeed'
                });
              }
            }

            // Récupération éventuelle de la clé TMDb
            if (reqUrl.includes('api.themoviedb.org') && reqUrl.includes('api_key=')) {
              const keyMatch = reqUrl.match(/api_key=([a-zA-Z0-9]+)/);
              if (keyMatch) {
                result.tmdbApiKey = keyMatch[1];
              }
            }
          }
        } catch (err) {}
      };

      ws.onerror = (err) => reject(err);
    });

    const data = await streamFoundPromise;
    return data;
  } finally {
    if (ws) {
      try { ws.close(); } catch (e) {}
    }
    if (chromeProc && chromeProc.pid) {
      killProcessTree(chromeProc.pid);
    }
    setTimeout(() => {
      try { fs.rmSync(tempProfileDir, { recursive: true, force: true }); } catch (e) {}
    }, 1500);
  }
}

function getLangLabel(code) {
  const map = {
    fr: 'Français (VOSTFR)',
    en: 'Anglais (English)',
    ja: 'Japonais (Japanese)',
    ko: 'Coréen (Korean)',
    es: 'Espagnol (Spanish)',
    de: 'Allemand (German)',
    it: 'Italien (Italian)',
    pt: 'Portugais (Portuguese)',
    ru: 'Russe (Russian)',
    ar: 'Arabe (Arabic)',
    zh: 'Chinois (Chinese)',
    id: 'Indonésien (Indonesian)',
    ms: 'Malais (Malay)',
    th: 'Thaï (Thai)',
    vi: 'Vietnamien (Vietnamese)',
    pl: 'Polonais (Polish)'
  };
  return map[code] || `Sous-titre (${code.toUpperCase()})`;
}

// Support appel CLI direct
if (process.argv[1] && process.argv[1].endsWith('extractor.mjs')) {
  const target = process.argv[2] || 'https://cinejoy.pk/watch/movie/1311031';
  extractCinejoy(target)
    .then(data => {
      console.log(JSON.stringify(data));
      process.exit(0);
    })
    .catch(err => {
      console.error(JSON.stringify({ error: err.message }));
      process.exit(1);
    });
}
