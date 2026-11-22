document.addEventListener('DOMContentLoaded', () => {
    // Éléments du DOM
    const urlInput = document.getElementById('url-input');
    const btnAnalyze = document.getElementById('btn-analyze');
    const btnPaste = document.getElementById('btn-paste');
    const alertBox = document.getElementById('alert-box');
    const alertMessage = document.getElementById('alert-message');

    const resultSection = document.getElementById('result-section');
    const mediaPoster = document.getElementById('media-poster');
    const mediaBadge = document.getElementById('media-badge');
    const mediaYear = document.getElementById('media-year');
    const mediaTitle = document.getElementById('media-title');
    const mediaOverview = document.getElementById('media-overview');
    const streamUrlText = document.getElementById('stream-url-text');

    const qualitiesList = document.getElementById('qualities-list');
    const audioList = document.getElementById('audio-list');
    const subtitlesSelect = document.getElementById('subtitles-select');
    const embedSubCheckbox = document.getElementById('embed-sub-checkbox');
    const btnDownload = document.getElementById('btn-download');

    const downloadSection = document.getElementById('download-section');
    const dlFilename = document.getElementById('dl-filename');
    const dlStatusBadge = document.getElementById('dl-status-badge');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const statPercent = document.getElementById('stat-percent');
    const statSpeed = document.getElementById('stat-speed');
    const statSize = document.getElementById('stat-size');
    const statEta = document.getElementById('stat-eta');
    const terminalBody = document.getElementById('terminal-body');
    const btnToggleTerminal = document.getElementById('btn-toggle-terminal');
    const dlFinishedActions = document.getElementById('dl-finished-actions');
    const btnOpenFile = document.getElementById('btn-open-file');
    const btnOpenFolder = document.getElementById('btn-open-folder');
    const btnOpenFolderHeader = document.getElementById('btn-open-folder-header');
    const btnNewDownload = document.getElementById('btn-new-download');

    // Données de l'analyse en mémoire
    let currentAnalysis = null;
    let selectedQualityId = null;
    let selectedAudioId = null;
    let eventSource = null;

    // Gestion des alertes
    function showAlert(msg, type = 'error') {
        alertMessage.textContent = msg;
        alertBox.className = `alert alert-${type}`;
        alertBox.classList.remove('hidden');
    }

    function hideAlert() {
        alertBox.classList.add('hidden');
    }

    // Coller depuis le presse-papier
    btnPaste.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text.trim();
                hideAlert();
            }
        } catch (e) {
            console.warn('Impossible de lire le presse-papier', e);
        }
    });

    // Pilules d'exemples rapides
    document.querySelectorAll('.pill-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            urlInput.value = btn.getAttribute('data-url');
            hideAlert();
            analyzeUrl();
        });
    });

    // Analyse du lien
    btnAnalyze.addEventListener('click', analyzeUrl);
    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') analyzeUrl();
    });

    async function analyzeUrl() {
        const url = urlInput.value.trim();
        if (!url) {
            showAlert("Veuillez saisir ou coller un lien valide.");
            return;
        }

        hideAlert();
        resultSection.classList.add('hidden');
        downloadSection.classList.add('hidden');

        // Animation bouton
        btnAnalyze.disabled = true;
        btnAnalyze.querySelector('.btn-text').textContent = "Analyse en cours...";
        btnAnalyze.querySelector('.btn-loader').classList.remove('hidden');

        try {
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await res.json();

            if (!res.ok || data.error) {
                throw new Error(data.error || "Erreur lors de l'analyse.");
            }

            currentAnalysis = data;
            renderAnalysisResult(data);
        } catch (err) {
            showAlert(err.message);
        } finally {
            btnAnalyze.disabled = false;
            btnAnalyze.querySelector('.btn-text').textContent = "Analyser le flux";
            btnAnalyze.querySelector('.btn-loader').classList.add('hidden');
        }
    }

    // Affichage des résultats
    function renderAnalysisResult(data) {
        const meta = data.metadata || {};

        // Métadonnées
        mediaTitle.textContent = meta.title || "Vidéo sans titre";
        mediaYear.textContent = meta.year || "2025";
        mediaOverview.textContent = meta.overview || "Aucune description.";
        mediaPoster.src = meta.poster || "/static/default_poster.png";
        if (!meta.poster) {
            mediaPoster.style.display = 'none';
        } else {
            mediaPoster.style.display = 'block';
        }

        streamUrlText.textContent = data.m3u8_url;
        streamUrlText.title = data.m3u8_url;

        // 1. Qualités vidéo
        qualitiesList.innerHTML = '';
        const qualities = data.video_qualities || [];
        if (qualities.length === 0) {
            qualitiesList.innerHTML = '<div class="option-card">Aucune résolution détectée</div>';
        } else {
            selectedQualityId = qualities[0].id; // Recommandé (1080p)

            qualities.forEach(q => {
                const card = document.createElement('div');
                card.className = `option-card ${q.id === selectedQualityId ? 'selected' : ''}`;
                card.setAttribute('data-id', q.id);

                card.innerHTML = `
                    <div class="option-left">
                        <div class="radio-indicator"></div>
                        <div class="option-details">
                            <span class="option-name">${q.label}</span>
                            <span class="option-subtext">Résolution : ${q.resolution}</span>
                        </div>
                    </div>
                    <span class="option-size">${q.size_str}</span>
                `;

                card.addEventListener('click', () => {
                    document.querySelectorAll('#qualities-list .option-card').forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    selectedQualityId = q.id;
                });

                qualitiesList.appendChild(card);
            });
        }

        // 2. Langues Audio
        audioList.innerHTML = '';
        const audios = data.audio_tracks || [];
        if (audios.length === 0) {
            audioList.innerHTML = '<div class="option-card">Piste audio standard intégrée</div>';
            selectedAudioId = 'default';
        } else {
            // Sélectionne la meilleure piste principale (évite les commentaires audio)
            const mainAudio = audios.find(a => !a.is_commentary && (a.id.toLowerCase().includes('japan') || a.lang === 'ja'))
                || audios.find(a => !a.is_commentary && (a.id.toLowerCase().includes('korean') || a.lang === 'ko'))
                || audios.find(a => !a.is_commentary && (a.id.toLowerCase().includes('french') || a.lang === 'fr'))
                || audios.find(a => !a.is_commentary)
                || audios[0];
            selectedAudioId = mainAudio ? mainAudio.id : audios[0].id;

            audios.forEach(a => {
                const card = document.createElement('div');
                card.className = `option-card ${a.id === selectedAudioId ? 'selected' : ''}`;
                card.setAttribute('data-id', a.id);

                card.innerHTML = `
                    <div class="option-left">
                        <div class="radio-indicator"></div>
                        <div class="option-details">
                            <span class="option-name">${a.label}</span>
                            <span class="option-subtext">Identifiant : ${a.id}</span>
                        </div>
                    </div>
                `;

                card.addEventListener('click', () => {
                    document.querySelectorAll('#audio-list .option-card').forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    selectedAudioId = a.id;
                });

                audioList.appendChild(card);
            });
        }

        // 3. Sous-titres
        subtitlesSelect.innerHTML = '<option value="">Aucun sous-titre</option>';
        const subs = data.subtitles || [];
        let autoSelectSub = null;

        subs.forEach(s => {
            const opt = document.createElement('option');
            opt.value = JSON.stringify({ url: s.url, lang: s.lang });
            opt.textContent = `${s.label} (${s.type.toUpperCase()})`;
            subtitlesSelect.appendChild(opt);

            // Pré-sélection automatique du français VOSTFR si disponible
            if (!autoSelectSub && s.lang === 'fr') {
                autoSelectSub = opt.value;
            }
        });

        if (autoSelectSub) {
            subtitlesSelect.value = autoSelectSub;
        }

        // Afficher le bloc résultat avec animation
        resultSection.classList.remove('hidden');
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Lancement du téléchargement
    btnDownload.addEventListener('click', async () => {
        if (!currentAnalysis) return;

        let subUrl = null;
        let subLang = 'fr';
        if (subtitlesSelect.value) {
            try {
                const parsed = JSON.parse(subtitlesSelect.value);
                subUrl = parsed.url;
                subLang = parsed.lang;
            } catch (e) {}
        }

        const payload = {
            m3u8_url: currentAnalysis.m3u8_url,
            video_id: selectedQualityId,
            audio_id: selectedAudioId,
            title: currentAnalysis.metadata?.title || 'Video_Telechargee',
            sub_url: subUrl,
            sub_lang: subLang,
            embed_sub: embedSubCheckbox.checked,
            is_cinejoy: currentAnalysis.is_cinejoy
        };

        try {
            btnDownload.disabled = true;
            const res = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (!res.ok || data.error) {
                throw new Error(data.error || "Impossible de démarrer le téléchargement.");
            }

            // Bascule vers l'interface de téléchargement en direct
            resultSection.classList.add('hidden');
            downloadSection.classList.remove('hidden');
            dlFinishedActions.classList.add('hidden');
            dlFilename.textContent = `${payload.title}.mp4`;
            terminalBody.innerHTML = '';

            downloadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

            startProgressMonitoring();
        } catch (err) {
            showAlert(err.message);
            btnDownload.disabled = false;
        }
    });

    // Écoute des événements SSE pour la progression en temps réel
    function startProgressMonitoring() {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource('/api/progress');

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                // Progression
                const pct = data.percent || 0;
                progressBarFill.style.width = `${pct}%`;
                statPercent.textContent = `${pct.toFixed(1)} %`;
                if (data.step_label) {
                    dlStatusBadge.textContent = `${data.step_label} (${pct.toFixed(1)}%)`;
                } else {
                    dlStatusBadge.textContent = `Téléchargement ${pct.toFixed(1)}%`;
                }

                // Vitesse, taille, ETA
                if (data.speed) statSpeed.textContent = data.speed;
                if (data.total_size) statSize.textContent = data.total_size;
                if (data.eta) statEta.textContent = data.eta;

                // Ajout des nouvelles lignes de terminal
                if (data.new_logs && data.new_logs.length > 0) {
                    data.new_logs.forEach(line => {
                        const lineDiv = document.createElement('div');
                        lineDiv.className = 'term-line';
                        if (line.startsWith('[System')) lineDiv.classList.add('term-system');
                        lineDiv.textContent = line;
                        terminalBody.appendChild(lineDiv);
                    });
                    terminalBody.scrollTop = terminalBody.scrollHeight;
                }

                // Statut Conversion / Muxing
                if (data.status === 'converting') {
                    dlStatusBadge.textContent = "Assemblage final / Sous-titres...";
                    dlStatusBadge.style.background = 'rgba(245, 158, 11, 0.2)';
                    dlStatusBadge.style.color = '#f59e0b';
                }

                // Fin du téléchargement
                if (data.status === 'completed') {
                    eventSource.close();
                    progressBarFill.style.width = '100%';
                    statPercent.textContent = '100.0 %';
                    statEta.textContent = '00:00';
                    dlStatusBadge.textContent = 'Terminé !';
                    dlStatusBadge.style.background = 'rgba(16, 185, 129, 0.2)';
                    dlStatusBadge.style.color = '#10b981';

                    dlFinishedActions.classList.remove('hidden');
                    btnDownload.disabled = false;
                }

                // Erreur
                if (data.status === 'error') {
                    eventSource.close();
                    dlStatusBadge.textContent = 'Erreur';
                    dlStatusBadge.style.background = 'rgba(239, 68, 68, 0.2)';
                    dlStatusBadge.style.color = '#ef4444';
                    showAlert(data.error_message || "Une erreur est survenue pendant le téléchargement.");
                    btnDownload.disabled = false;
                }
            } catch (e) {
                console.error("Erreur traitement SSE", e);
            }
        };

        eventSource.onerror = () => {
            console.warn("Connexion SSE fermée ou interrompue.");
        };
    }

    // Basculer l'affichage du terminal
    btnToggleTerminal.addEventListener('click', () => {
        if (terminalBody.style.display === 'none') {
            terminalBody.style.display = 'block';
            btnToggleTerminal.textContent = 'Masquer';
        } else {
            terminalBody.style.display = 'none';
            btnToggleTerminal.textContent = 'Afficher';
        }
    });

    // Ouvrir le dossier des téléchargements
    async function openDownloadsFolder() {
        try {
            await fetch('/api/open-folder', { method: 'POST' });
        } catch (e) {
            console.error("Impossible d'ouvrir le dossier", e);
        }
    }

    btnOpenFolder.addEventListener('click', openDownloadsFolder);
    btnOpenFolderHeader.addEventListener('click', openDownloadsFolder);

    // Ouvrir la vidéo
    btnOpenFile.addEventListener('click', async () => {
        try {
            await fetch('/api/open-file', { method: 'POST' });
        } catch (e) {
            console.error("Impossible d'ouvrir la vidéo", e);
        }
    });

    // Nouveau téléchargement
    btnNewDownload.addEventListener('click', () => {
        downloadSection.classList.add('hidden');
        urlInput.value = '';
        urlInput.focus();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
});
