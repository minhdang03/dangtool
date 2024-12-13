import os
from flask import Blueprint
from dotenv import load_dotenv
import asyncio
import telegram
from telegram.error import TelegramError
import httpx
import json
import time

load_dotenv()  # Thêm dòng này ở đầu file

uploadpornhubtotelegram_bp = Blueprint('uploadpornhubtotelegram', __name__)

# Cấu hình

API_SERVER = "https://api.telegram.org"  # Thay đổi này

# Biến global để lưu trữ tiến trình
UPLOAD_PROGRESS = {'percent': 0, 'speed': '0 KB/s'}

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

async def get_bot():
    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.initialize()
    return bot

async def send_large_video(video_path):
    bot = await get_bot()
    try:
        file_size = os.path.getsize(video_path)
        start_time = time.time()
        
        with open(video_path, 'rb') as video_file:
            await bot.send_chat_action(chat_id=CHAT_ID, action="upload_document")
            
            # Tăng thời gian chờ
            message = await bot.send_document(
                chat_id=CHAT_ID,
                document=video_file,
                filename=os.path.basename(video_path),
                read_timeout=1200,  # Tăng lên 20 phút
                write_timeout=1200,
                connect_timeout=60,
                pool_timeout=1200,
            )
            
            # Cập nhật tiến trình
            UPLOAD_PROGRESS['percent'] = 100
            UPLOAD_PROGRESS['speed'] = f"{file_size / (time.time() - start_time) / 1024:.2f} KB/s"
            current_app.config['UPLOAD_PROGRESS'] = json.dumps(UPLOAD_PROGRESS)
        
        return f"Video {os.path.basename(video_path)} đã được gửi thành công."
    except telegram.error.BadRequest as e:
        if "Request Entity Too Large" in str(e):
            return "Video quá lớn để tải lên. Vui lòng sử dụng file nhỏ hơn hoặc chia nhỏ file."
        else:
            return f"Lỗi khi gửi video: {str(e)}"
    except TelegramError as e:
        return f"Lỗi khi gửi video: {str(e)}"
    finally:
        await bot.shutdown()

async def upload_video(video_path):
    if not os.path.exists(video_path):
        return f"Không tìm thấy file: {video_path}"
    
    file_size = os.path.getsize(video_path)
    print(f"Bắt đầu tải lên file {os.path.basename(video_path)} (Kích thước: {file_size / (1024*1024):.2f} MB)")
    
    return await send_large_video(video_path)

@uploadpornhubtotelegram_bp.route('/upload_to_telegram/', methods=['POST'])
def handle_upload():
    video_path = request.json.get('video_path')
    if not video_path:
        return jsonify({"error": "Không có đường dẫn video được cung cấp"}), 400
    
    result = asyncio.run(upload_video(video_path))
    return jsonify({"message": result})

@uploadpornhubtotelegram_bp.route('/upload_progress/')
def get_upload_progress():
    return current_app.config.get('UPLOAD_PROGRESS', json.dumps({'percent': 0, 'speed': '0 KB/s'}))
