from flask import Flask, request, send_file, jsonify, Response
from pytubefix import YouTube
from googleapiclient.discovery import build
import os
import tempfile
import shutil

app = Flask(__name__)

DOWNLOAD_FOLDER = tempfile.mkdtemp()

@app.route('/')
def home():
    return jsonify({
        "message": "API de téléchargement YouTube",
        "endpoints": {
            "download": "GET /download?video_url=URL_YOUTUBE",
            "info": "GET /info?video_url=URL_YOUTUBE",
            "recherche": "GET /recherche?video=NOM_VIDEO"
        },
        "example": "/download?video_url=https://www.youtube.com/watch?v=VIDEO_ID"
    })

@app.route('/info', methods=['GET'])
def get_video_info():
    video_url = request.args.get('video_url')
    
    if not video_url:
        return jsonify({"error": "Paramètre 'video_url' requis"}), 400
    
    try:
        yt = YouTube(video_url)
        streams = yt.streams.filter(progressive=True, file_extension='mp4')
        
        available_resolutions = []
        for stream in streams:
            available_resolutions.append({
                "resolution": stream.resolution,
                "fps": stream.fps,
                "size_mb": round(stream.filesize / (1024 * 1024), 2) if stream.filesize else "inconnu"
            })
        
        return jsonify({
            "title": yt.title,
            "author": yt.author,
            "length_seconds": yt.length,
            "views": yt.views,
            "thumbnail_url": yt.thumbnail_url,
            "available_streams": available_resolutions
        })
    except Exception as e:
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
        
        return jsonify({
            "recherche": query,
            "nombre_resultats": len(videos),
            "max_demande": max_results,
            "videos": videos
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['GET'])
def download_video():
    video_url = request.args.get('video_url')
    resolution = request.args.get('resolution', '720p')
    
    if not video_url:
        return jsonify({"error": "Paramètre 'video_url' requis"}), 400
    
    try:
        yt = YouTube(video_url)
        
        stream = yt.streams.filter(progressive=True, file_extension='mp4', resolution=resolution).first()
        
        if not stream:
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        
        if not stream:
            return jsonify({"error": "Aucun flux vidéo disponible"}), 404
        
        for f in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, f)
            try:
                os.unlink(file_path)
            except:
                pass
        
        downloaded_file = stream.download(output_path=DOWNLOAD_FOLDER)
        
        safe_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_title}.mp4"
        
        return send_file(
            downloaded_file,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
