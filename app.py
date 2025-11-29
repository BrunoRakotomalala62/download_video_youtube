from flask import Flask, request, send_file, jsonify, Response
from pytubefix import YouTube
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
            "info": "GET /info?video_url=URL_YOUTUBE"
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
