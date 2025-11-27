const express = require('express');
const ytdl = require('@distube/ytdl-core');
const app = express();
const PORT = 5000;

const agent = ytdl.createAgent(undefined, {
  localAddress: undefined,
  headers: {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
  }
});

const qualityMap = {
  '144p': '160',
  '240p': '133',
  '360p': '18',
  '480p': '135',
  '720p': '22',
  '1080p': '137'
};

app.get('/download', async (req, res) => {
  try {
    const videoUrl = req.query.video_url;
    const qualite = req.query.qualite || '360p';

    if (!videoUrl) {
      return res.status(400).json({
        error: 'Paramètre video_url requis',
        exemple: '/download?video_url=https://www.youtube.com/watch?v=VIDEO_ID&qualite=360p'
      });
    }

    if (!ytdl.validateURL(videoUrl)) {
      return res.status(400).json({
        error: 'URL YouTube invalide',
        url_fournie: videoUrl
      });
    }

    console.log(`Téléchargement demandé: ${videoUrl} en ${qualite}`);

    const info = await ytdl.getInfo(videoUrl, { agent });
    const title = info.videoDetails.title.replace(/[^\w\s-]/g, '').trim();
    
    console.log(`Vidéo trouvée: ${title}`);
    
    let format = null;
    const itag = qualityMap[qualite];
    
    if (itag) {
      format = info.formats.find(f => f.itag === parseInt(itag) && f.hasVideo && f.hasAudio);
    }
    
    if (!format) {
      const formatsWithAudioVideo = info.formats.filter(f => f.hasVideo && f.hasAudio);
      if (formatsWithAudioVideo.length > 0) {
        format = formatsWithAudioVideo[0];
      } else {
        format = ytdl.chooseFormat(info.formats, { 
          quality: 'highest',
          filter: 'audioandvideo'
        });
      }
    }

    if (!format) {
      return res.status(400).json({
        error: 'Aucun format disponible pour cette vidéo',
        qualite_demandee: qualite
      });
    }

    console.log(`Format sélectionné: itag ${format.itag}, qualité: ${format.qualityLabel || 'inconnue'}`);

    const filename = `${title}_${qualite}.mp4`;
    
    res.header('Content-Disposition', `attachment; filename="${encodeURIComponent(filename)}"`);
    res.header('Content-Type', 'video/mp4');
    if (format.contentLength) {
      res.header('Content-Length', format.contentLength);
    }

    const stream = ytdl(videoUrl, {
      format: format,
      agent: agent,
      highWaterMark: 1 << 25
    });

    stream.on('error', (error) => {
      console.error('Erreur de téléchargement:', error.message);
      if (!res.headersSent) {
        res.status(500).json({ 
          error: 'Erreur lors du téléchargement de la vidéo',
          message: error.message 
        });
      }
    });

    stream.on('end', () => {
      console.log('Téléchargement terminé avec succès');
    });

    stream.pipe(res);

  } catch (error) {
    console.error('Erreur:', error.message);
    res.status(500).json({
      error: 'Erreur lors du traitement de la demande',
      message: error.message
    });
  }
});

app.get('/info', async (req, res) => {
  try {
    const videoUrl = req.query.video_url;

    if (!videoUrl) {
      return res.status(400).json({
        error: 'Paramètre video_url requis'
      });
    }

    if (!ytdl.validateURL(videoUrl)) {
      return res.status(400).json({
        error: 'URL YouTube invalide'
      });
    }

    const info = await ytdl.getInfo(videoUrl, { agent });
    
    const formats = info.formats
      .filter(f => f.hasVideo && f.hasAudio)
      .map(f => ({
        itag: f.itag,
        qualite: f.qualityLabel,
        container: f.container,
        taille: f.contentLength ? `${Math.round(f.contentLength / 1024 / 1024)} MB` : 'Inconnue'
      }));

    res.json({
      titre: info.videoDetails.title,
      duree: `${Math.floor(info.videoDetails.lengthSeconds / 60)}:${(info.videoDetails.lengthSeconds % 60).toString().padStart(2, '0')}`,
      auteur: info.videoDetails.author.name,
      formats_disponibles: formats
    });

  } catch (error) {
    res.status(500).json({
      error: 'Erreur lors de la récupération des informations',
      message: error.message
    });
  }
});

app.get('/', (req, res) => {
  res.json({
    message: 'API de téléchargement de vidéos YouTube',
    endpoints: {
      download: {
        url: 'GET /download',
        parametres: {
          video_url: 'URL de la vidéo YouTube (requis)',
          qualite: 'Qualité: 144p, 240p, 360p, 480p, 720p, 1080p (défaut: 360p)'
        },
        exemple: '/download?video_url=https://www.youtube.com/watch?v=VIDEO_ID&qualite=360p'
      },
      info: {
        url: 'GET /info',
        parametres: {
          video_url: 'URL de la vidéo YouTube (requis)'
        },
        exemple: '/info?video_url=https://www.youtube.com/watch?v=VIDEO_ID'
      }
    }
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Serveur démarré sur http://0.0.0.0:${PORT}`);
  console.log('Endpoints disponibles:');
  console.log('  GET /download?video_url=URL&qualite=360p');
  console.log('  GET /info?video_url=URL');
});
