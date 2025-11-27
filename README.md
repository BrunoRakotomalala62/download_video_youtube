# YouTube Video Download API

API Node.js pour télécharger des vidéos YouTube avec sélection de qualité.

## Utilisation

### Endpoint

```
GET /download?video_url=<URL_YOUTUBE>&qualite=<QUALITE>
```

### Paramètres

| Paramètre | Description | Requis | Défaut |
|-----------|-------------|--------|--------|
| video_url | URL de la vidéo YouTube | Oui | - |
| qualite | Qualité de la vidéo | Non | 360p |

### Qualités disponibles

- 144p
- 240p
- 360p (défaut)
- 480p
- 720p
- 1080p

### Exemple

```
GET /download?video_url=https://www.youtube.com/watch?v=WE9G0HGMvnw&qualite=360p
```

## Installation

```bash
npm install
npm start
```

Le serveur démarre sur le port 5000.
