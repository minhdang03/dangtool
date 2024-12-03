from flask import Blueprint, render_template, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptAvailable, NoTranscriptFound

gettranscriptsubtitles_bp = Blueprint('gettranscriptsubtitles', __name__)

@gettranscriptsubtitles_bp.route('/get-transcript-subtitles', methods=['GET', 'POST'])
def get_transcript_subtitles():
    transcript = None
    error = None
    video_id = None
    full_text = ""

    if request.method == 'POST':
        video_url = request.form.get('video_url')
        if video_url:
            try:
                # Loại bỏ ký tự '@' nếu có
                video_url = video_url.lstrip('@')
                
                # Xử lý URL đầy đủ
                if 'youtube.com' in video_url:
                    video_id = video_url.split('v=')[1].split('&')[0]
                # Xử lý URL rút gọn
                elif 'youtu.be' in video_url:
                    video_id = video_url.split('/')[-1].split('?')[0]
                else:
                    raise ValueError("URL không hợp lệ")
                
                transcript = YouTubeTranscriptApi.get_transcript(video_id)
                full_text = " ".join([entry['text'] for entry in transcript])
            except (IndexError, ValueError):
                error = "URL video không hợp lệ. Vui lòng nhập một URL YouTube hợp lệ."
            except TranscriptsDisabled:
                error = "Video này không có phụ đề hoặc đã bị vô hiệu hóa phụ đề."
            except NoTranscriptAvailable:
                error = "Không thể lấy phụ đề cho video này. Video không hỗ trợ hoặc chưa có phụ đề."
            except NoTranscriptFound:
                error = "Không tìm thấy phụ đề cho video này. Video có thể chưa được thêm phụ đề hoặc không hỗ trợ ngôn ngữ yêu cầu."
            except Exception as e:
                if "Could not retrieve a transcript for the video" in str(e):
                    error = "Không thể lấy phụ đề cho video này. Video không hỗ trợ hoặc chưa có phụ đề được tạo."
                else:
                    error = f"Đã xảy ra lỗi: {str(e)}"

    return render_template('youtube/gettranscriptsubtitles.html', transcript=transcript, error=error, video_id=video_id, full_text=full_text)

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
