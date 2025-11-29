from flask import Flask, request, send_file, jsonify, Response, render_template, redirect
from pytubefix import YouTube
from googleapiclient.discovery import build
import os
import tempfile
import shutil
import logging
import time
import random
import requests
import re
from functools import wraps
from urllib.parse import quote

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

DOWNLOAD_FOLDER = tempfile.mkdtemp()

CLIENT_TYPES = ['WEB', 'ANDROID', 'IOS', 'WEB_EMBED', 'WEB_MUSIC']

def retry_with_backoff(max_retries=3, base_delay=2, max_delay=30):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception: Exception = Exception("Unknown error")
            for attempt in range(max_retries):
                try:
                    time.sleep(random.uniform(0.5, 1.5))
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()
                    if '429' in error_str or 'too many requests' in error_str:
                        delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                        logger.warning(f"Rate limited (429). Attempt {attempt + 1}/{max_retries}. Waiting {delay:.1f}s...")
                        time.sleep(delay)
                    elif '403' in error_str:
                        delay = random.uniform(2, 5)
                        logger.warning(f"Access denied (403). Attempt {attempt + 1}/{max_retries}. Waiting {delay:.1f}s...")
                        time.sleep(delay)
                    else:
                        raise e
            raise last_exception
        return wrapper
    return decorator

def create_youtube_with_retry(video_url, max_retries=3):
    last_exception: Exception = Exception("Failed to connect to YouTube")
    for client_type in CLIENT_TYPES[:max_retries]:
        try:
            time.sleep(random.uniform(0.3, 1.0))
            logger.debug(f"Trying client type: {client_type}")
            yt = YouTube(video_url, client_type)
            _ = yt.title
            return yt
        except Exception as e:
            last_exception = e
            error_str = str(e).lower()
            if '429' in error_str or 'too many requests' in error_str:
                delay = random.uniform(3, 8)
                logger.warning(f"Rate limited with {client_type}. Waiting {delay:.1f}s before trying next client...")
                time.sleep(delay)
            elif '403' in error_str:
                delay = random.uniform(1, 3)
                logger.warning(f"Access denied with {client_type}. Trying next client...")
                time.sleep(delay)
            else:
                logger.error(f"Error with {client_type}: {e}")
                continue
    
    for attempt in range(2):
        try:
            delay = random.uniform(5, 15)
            logger.info(f"Final retry attempt {attempt + 1}. Waiting {delay:.1f}s...")
            time.sleep(delay)
            yt = YouTube(video_url, 'ANDROID')
            _ = yt.title
            return yt
        except Exception as e:
            last_exception = e
            continue
    
    raise last_exception

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/info', methods=['GET'])
def get_video_info():
    video_url = request.args.get('video_url')
    
    if not video_url:
        return jsonify({"error": "Paramètre 'video_url' requis"}), 400
    
    try:
        logger.debug(f"Getting info for video: {video_url}")
        yt = create_youtube_with_retry(video_url)
        logger.debug(f"YouTube object created, getting title...")
        title = yt.title
        logger.debug(f"Title: {title}")
        streams = yt.streams.filter(progressive=True, file_extension='mp4')
        logger.debug(f"Streams filtered")
        
        available_resolutions = []
        for stream in streams:
            try:
                size_mb = round(stream.filesize / (1024 * 1024), 2) if stream.filesize else "inconnu"
            except Exception:
                size_mb = "inconnu"
            available_resolutions.append({
                "resolution": stream.resolution,
                "fps": stream.fps,
                "size_mb": size_mb
            })
        
        return jsonify({
            "title": title,
            "author": yt.author,
            "length_seconds": yt.length,
            "views": yt.views,
            "thumbnail_url": yt.thumbnail_url,
            "available_streams": available_resolutions
        })
    except Exception as e:
        error_str = str(e).lower()
        if '429' in error_str or 'too many requests' in error_str:
            return jsonify({
                "error": "YouTube limite temporairement les requêtes. Veuillez réessayer dans 30 secondes.",
                "retry_after": 30,
                "code": 429
            }), 429
        return jsonify({"error": str(e)}), 500

@app.route('/recherche', methods=['GET'])
def search_videos():
    query = request.args.get('video')
    max_results = request.args.get('max_results', 200, type=int)
    
    if not query:
        return jsonify({"error": "Paramètre 'video' requis"}), 400
    
    youtube_api_key = os.environ.get("YOUTUBE_API_KEY")
    if not youtube_api_key:
        return jsonify({"error": "Clé API YouTube non configurée. Veuillez définir YOUTUBE_API_KEY dans les variables d'environnement."}), 500
    
    try:
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        
        all_video_ids = []
        next_page_token = None
        
        while len(all_video_ids) < max_results:
            remaining = max_results - len(all_video_ids)
            fetch_count = min(50, remaining)
            
            search_params = {
                'q': query,
                'part': 'id,snippet',
                'type': 'video',
                'maxResults': fetch_count
            }
            if next_page_token:
                search_params['pageToken'] = next_page_token
            
            search_response = youtube.search().list(**search_params).execute()
            
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            all_video_ids.extend(video_ids)
            
            next_page_token = search_response.get('nextPageToken')
            if not next_page_token:
                break
            
            time.sleep(random.uniform(0.1, 0.3))
        
        all_video_ids = all_video_ids[:max_results]
        
        videos = []
        
        for i in range(0, len(all_video_ids), 50):
            batch_ids = all_video_ids[i:i+50]
            
            if batch_ids:
                videos_response = youtube.videos().list(
                    id=','.join(batch_ids),
                    part='snippet,contentDetails,statistics'
                ).execute()
                
                for video in videos_response.get('items', []):
                    video_id = video['id']
                    snippet = video['snippet']
                    content_details = video['contentDetails']
                    
                    duration_iso = content_details.get('duration', 'PT0S')
                    duration_str = duration_iso.replace('PT', '').replace('H', 'h ').replace('M', 'm ').replace('S', 's')
                    
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    definition = content_details.get('definition', 'sd').upper()
                    
                    thumbnails = snippet.get('thumbnails', {})
                    image_url = thumbnails.get('maxres', thumbnails.get('high', thumbnails.get('medium', {}))).get('url', '')
                    
                    videos.append({
                        "titre": snippet.get('title', ''),
                        "duree": duration_str.strip(),
                        "qualite": definition,
                        "lien": video_url,
                        "image_url": image_url,
                        "auteur": snippet.get('channelTitle', ''),
                        "vues": video.get('statistics', {}).get('viewCount', 'N/A')
                    })
                
                time.sleep(random.uniform(0.1, 0.2))
        
        return jsonify({
            "recherche": query,
            "nombre_resultats": len(videos),
            "max_demande": max_results,
            "videos": videos
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def sanitize_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.strip()
    if len(filename) > 100:
        filename = filename[:100]
    return filename if filename else "video"

def generate_stream(stream_url, chunk_size=8192):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
        }
        with requests.get(stream_url, headers=headers, stream=True, timeout=300) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    yield chunk
    except Exception as e:
        logger.error(f"Stream error: {e}")
        raise

@app.route('/download', methods=['GET'])
def download_video():
    video_url = request.args.get('video_url')
    qualite = request.args.get('qualite', '360p')
    file_type = request.args.get('type', 'mp4').lower()
    
    if not video_url:
        return jsonify({"error": "Paramètre 'video_url' requis"}), 400
    
    if file_type not in ['mp3', 'mp4']:
        return jsonify({"error": "Type invalide. Utilisez 'mp3' ou 'mp4'"}), 400
    
    try:
        logger.debug(f"Download request for: {video_url}, type: {file_type}, quality: {qualite}")
        yt = create_youtube_with_retry(video_url)
        title = sanitize_filename(yt.title)
        logger.debug(f"YouTube object created for download, title: {title}")
        
        if file_type == 'mp3':
            stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            if not stream:
                return jsonify({"error": "Aucun flux audio disponible"}), 404
            
            mime_type = 'audio/mpeg'
            extension = 'mp3'
        else:
            logger.debug(f"Looking for stream with resolution: {qualite}")
            stream = yt.streams.filter(progressive=True, file_extension='mp4', resolution=qualite).first()
            
            if not stream:
                logger.debug("Exact resolution not found, getting best available")
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            if not stream:
                return jsonify({"error": "Aucun flux vidéo disponible"}), 404
            
            mime_type = 'video/mp4'
            extension = 'mp4'
        
        logger.debug(f"Stream found: {stream}")
        stream_url = stream.url
        logger.debug(f"Stream URL obtained, starting proxy download")
        
        try:
            file_size = stream.filesize
        except Exception:
            file_size = None
        
        filename = f"{title}.{extension}"
        encoded_filename = quote(filename)
        
        headers = {
            'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}",
            'Content-Type': mime_type,
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
        
        if file_size:
            headers['Content-Length'] = str(file_size)
        
        return Response(
            generate_stream(stream_url),
            headers=headers,
            mimetype=mime_type,
            direct_passthrough=True
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        error_str = str(e).lower()
        if '429' in error_str or 'too many requests' in error_str:
            return jsonify({
                "error": "YouTube limite temporairement les requêtes. Veuillez réessayer dans 30 secondes.",
                "retry_after": 30,
                "code": 429
            }), 429
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
