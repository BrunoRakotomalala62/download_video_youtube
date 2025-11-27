const express = require('express');
const ytdl = require('@distube/ytdl-core');
const app = express();
const PORT = 5000;

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

    const info = await ytdl.getInfo(videoUrl);
    const title = info.videoDetails.title.replace(/[^\w\s-]/g, '').trim();
    
    const itag = qualityMap[qualite] || qualityMap['360p'];
    
    let format = info.formats.find(f => f.itag === parseInt(itag));
    
    if (!format) {
      format = ytdl.chooseFormat(info.formats, { 
        quality: qualite === '720p' || qualite === '1080p' ? 'highestvideo' : 'lowest',
        filter: 'videoandaudio'
      });
    }

    const filename = `${title}_${qualite}.mp4`;
    
    res.header('Content-Disposition', `attachment; filename="${encodeURIComponent(filename)}"`);
    res.header('Content-Type', 'video/mp4');

    const stream = ytdl(videoUrl, {
      format: format,
      filter: 'videoandaudio'
    });

    stream.on('error', (error) => {
      console.error('Erreur de téléchargement:', error.message);
      if (!res.headersSent) {
        res.status(500).json({ error: 'Erreur lors du téléchargement de la vidéo' });
      }
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

app.get('/', (req, res) => {
  res.json({
    message: 'API de téléchargement de vidéos YouTube',
    usage: {
      endpoint: 'GET /download',
      parametres: {
        video_url: 'URL de la vidéo YouTube (requis)',
        qualite: 'Qualité de la vidéo: 144p, 240p, 360p, 480p, 720p, 1080p (défaut: 360p)'
      },
      exemple: '/download?video_url=https://www.youtube.com/watch?v=VIDEO_ID&qualite=360p'
    }
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Serveur démarré sur http://0.0.0.0:${PORT}`);
  console.log('Endpoint disponible: GET /download?video_url=URL&qualite=360p');
});
