from flask import Blueprint, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptAvailable, NoTranscriptFound
import re

gettranscriptsubtitles_bp = Blueprint('gettranscriptsubtitles', __name__)

@gettranscriptsubtitles_bp.route('/get-transcript-subtitles', methods=['GET', 'POST'])
def get_transcript_subtitles():
    if request.method == 'POST':
        results = {
            'transcripts': {},
            'failed_videos': [],
            'failed_urls': []
        }
        
        video_urls_text = request.form.get('video_urls', '').strip()
        if video_urls_text:
            urls = [url.strip() for url in video_urls_text.split('\n') if url.strip()]
            
            for index, url in enumerate(urls, 1):
                if not is_valid_youtube_url(url):
                    results['failed_urls'].append({
                        'url': url,
                        'error': 'Ông troll sao?, gởi link không hợp lệ như này à?'
                    })
                    continue
                
                try:
                    video_id = extract_video_id(url)
                    transcript = YouTubeTranscriptApi.get_transcript(video_id)
                    results['transcripts'][video_id] = {
                        'index': index,
                        'data': transcript
                    }
                except (TranscriptsDisabled, NoTranscriptAvailable, NoTranscriptFound):
                    results['failed_videos'].append({
                        'url': url,
                        'error': 'Video không hỗ trợ hoặc chưa có phụ đề'
                    })
                except Exception as e:
                    results['failed_videos'].append({
                        'url': url,
                        'error': str(e)
                    })
        
        return render_template('youtube/gettranscriptsubtitles.html', results=results)
    
    return render_template('youtube/gettranscriptsubtitles.html')

def extract_video_id(url):
    if 'youtube.com' in url:
        return url.split('v=')[1].split('&')[0]
    elif 'youtu.be' in url:
        return url.split('/')[-1].split('?')[0]
    else:
        raise ValueError("URL không hợp lệ")

@gettranscriptsubtitles_bp.route('/get-full-text', methods=['POST'])
def get_full_text():
    video_id = request.form.get('video_id')
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join([entry['text'] for entry in transcript])
        return jsonify({'full_text': full_text})
    except Exception as e:
        if "Could not retrieve a transcript for the video" in str(e):
            return jsonify({'error': "Không thể lấy phụ đề cho video này. Video không hỗ trợ hoặc chưa có phụ đề được tạo."}), 400
        return jsonify({'error': str(e)}), 400

def is_valid_youtube_url(url):
    youtube_regex = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    )
    return youtube_regex.match(url) is not None

def process_video_urls(video_urls):
    results = {
        'transcripts': {},
        'failed_videos': [],
        'failed_urls': []
    }   
    
    for url in video_urls:
        if not is_valid_youtube_url(url):
            results['failed_urls'].append({'url': url, 'error': 'Ông troll sao?, gởi link không hợp lệ như này à?'})
        else:
            # Thực hiện xử lý lấy phụ đề
            # Nếu thành công, thêm vào results['transcripts']
            # Nếu thất bại, thêm vào results['failed_videos']
            pass
    
    return results
