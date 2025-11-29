# API de Téléchargement YouTube

## Vue d'ensemble
API REST simple permettant de télécharger des vidéos YouTube en utilisant la bibliothèque pytubeFix.

## Endpoints

### GET /
Page d'accueil avec la liste des endpoints disponibles.

### GET /download
Télécharge une vidéo YouTube.

**Paramètres:**
- `video_url` (requis): L'URL complète de la vidéo YouTube
- `resolution` (optionnel): Résolution souhaitée (par défaut: 720p)

**Exemple:**
```
/download?video_url=https://www.youtube.com/watch?v=VIDEO_ID
/download?video_url=https://www.youtube.com/watch?v=VIDEO_ID&resolution=360p
```

### GET /info
Récupère les informations d'une vidéo YouTube.

**Paramètres:**
- `video_url` (requis): L'URL complète de la vidéo YouTube

**Exemple:**
```
/info?video_url=https://www.youtube.com/watch?v=VIDEO_ID
```

## Technologies
- Python 3.11
- Flask (serveur web)
- pytubeFix (téléchargement YouTube)

## Structure du projet
```
.
├── app.py          # Serveur Flask principal
├── replit.md       # Documentation du projet
└── requirements.txt # Dépendances Python
```
