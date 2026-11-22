# 🎬 CineJoy Downloader Pro

> **Application Web complète et autonome pour télécharger des films et séries depuis CineJoy en haute qualité avec sélection des pistes audio et sous-titres (VOSTFR).**

[![GitHub Repository](https://img.shields.io/badge/GitHub-cinejoy--downloader-blue?logo=github)](https://github.com/ilyassyounes23/cinejoy-downloader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Plateforme-Windows-blue)](https://www.microsoft.com/windows)

---

## ✨ Fonctionnalités

- 🚀 **100% Autonome & Portable** : Environnement Python portable embarqué (aucune installation de Python ou de packages n'est obligatoire).
- 🔍 **Extraction intelligente des flux CineJoy** : Détection automatique des flux vidéo `.m3u8` et décryptage via l'analyseur réseau headless.
- 🎞️ **Choix de la qualité vidéo** : 1080p Full HD, 720p HD, etc.
- 🌐 **Pistes audio multilingues** : Sélection facile (VF, VO, Anglais, Espagnol...).
- 💬 **Sous-titres intégrés (VOSTFR)** : Téléchargement et intégration automatique des sous-titres VTT / SRT.
- 🎨 **Interface Web Moderne (Dark Theme)** : Tableau de bord dynamique avec barre de progression en temps réel, vitesse de téléchargement, temps restant (ETA) et console de logs en direct.
- 🎬 **Intégration TMDb** : Affichage automatique de l'affiche, du titre officiel, de l'année et du synopsis.
- 📁 **Dossier de sortie dédié** : Sauvegarde automatique dans le dossier `_VIDEOS_TELECHARGEES`.

---

## 🚀 Démarrage rapide (En 1 Clic)

### 1. Cloner ou télécharger le dépôt
```bash
git clone https://github.com/ilyassyounes23/cinejoy-downloader.git
cd cinejoy-downloader
```
*(ou téléchargez le fichier ZIP depuis GitHub et extrayez-le sur votre PC).*

### 2. Lancer l'application
Double-cliquez simplement sur :
👉 **`LANCER_APPLICATION.bat`**

- Lors du **premier lancement**, l'application télécharge automatiquement les outils nécessaires (`ffmpeg`, `node`) dans le dossier `bin/`.
- Votre navigateur s'ouvre automatiquement sur : **`http://localhost:5000`**.

---

## 📖 Utilisation

1. **Ouvrez CineJoy** dans votre navigateur et copiez l'adresse de votre film ou épisode (exemple : `https://cinejoy.pk/watch/movie/...`).
2. **Collez le lien** dans la barre de recherche de l'application et cliquez sur **« Analyser le flux »**.
3. **Sélectionnez vos options** :
   - La résolution (ex : 1080p).
   - La piste audio souhaitée (ex : Français ou VO).
   - Les sous-titres éventuels (ex : Français VOSTFR).
4. Cliquez sur **« Lancer le téléchargement »** !
5. Retrouvez votre vidéo complète prête à être regardée dans le dossier :
   📂 **`_VIDEOS_TELECHARGEES`**

---

## 🛠️ Structure du Projet

```text
cinejoy-downloader/
├── bin/                       # Outils d'encodage et flux (yt-dlp, ffmpeg, node)
├── cinejoy_app/               # Application principale Flask
│   ├── app.py                 # Serveur Web & contrôleur de téléchargement
│   ├── extractor.mjs          # Script d'extraction headless Chrome / Edge
│   ├── static/                # Interface UI (CSS, JavaScript)
│   └── templates/             # Gabarit HTML
├── python/                    # Python portable préconfiguré
├── _VIDEOS_TELECHARGEES/      # Dossier des vidéos finales
├── INSTALLER_DEPENDANCES.bat  # Script d'installation manuelle des outils si besoin
├── LANCER_APPLICATION.bat     # Lanceur 1-clic principal
├── setup_tools.py             # Script de téléchargement automatique des binaires
├── requirements.txt           # Dépendances Python
└── README.md                  # Documentation du projet
```

---

## 👥 Partager avec vos amis

Pour que vos amis puissent l'installer sur leur ordinateur :
1. Partagez-leur le lien du dépôt : [https://github.com/ilyassyounes23/cinejoy-downloader](https://github.com/ilyassyounes23/cinejoy-downloader)
2. Ils cliquent sur **Code** > **Download ZIP** (ou `git clone`).
3. Ils dézippent et lancent **`LANCER_APPLICATION.bat`**. C'est tout !

---

## ⚖️ Avertissement légal

Ce logiciel est destiné à un usage personnel, éducatif et privé uniquement. Veuillez respecter les conditions d'utilisation des plateformes concernées ainsi que les lois sur le droit d'auteur applicables dans votre juridiction.
