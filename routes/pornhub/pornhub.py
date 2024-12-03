#!/usr/bin/env python
import httpx
import telegram
import youtube_dl
import requests
import sys
import urllib.parse as urlparse
import os
from bs4 import BeautifulSoup
import ssl
from flask import app, current_app
import json
import time
import socket
import warnings
import urllib.request
from urllib3.exceptions import InsecureRequestWarning
from flask import Blueprint, render_template, request, jsonify, current_app
import asyncio
import aiohttp
from telegram import Bot
from telegram.error import TelegramError
from concurrent.futures import ThreadPoolExecutor
import subprocess


pornhub_bp = Blueprint('pornhub', __name__)
# Tắt cảnh báo cho requests
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# Tắt xác minh SSL cho urllib và requests
ssl._create_default_https_context = ssl._create_unverified_context
requests.packages.urllib3.disable_warnings()

DOWNLOAD_LOCATION = os.path.join('static', 'pornhub_video')
ssl._create_default_https_context = ssl._create_unverified_context

def ph_url_check(url):
    parsed = urlparse.urlparse(url)
    regions = ["www", "cn", "cz", "de", "es", "fr", "it", "nl", "jp", "pt", "pl", "rt"]
    for region in regions:
        if parsed.netloc == region + ".pornhub.com":
            print("PornHub url validated.")
            return
    print("This is not a PornHub url.")
    sys.exit()

def ph_alive_check(url):
    try:
        requested = requests.get(url, verify=False)
        if requested.status_code == 200:
            return "URL tồn tại và có thể truy cập."
        else:
            return "URL không tồn tại hoặc không thể truy cập."
    except requests.exceptions.RequestException as e:
        return f"Lỗi khi kiểm tra URL: {str(e)}"

def get_downloaded_videos():
    app_root = current_app.root_path
    download_location = os.path.join(app_root, 'static', 'pornhub_video')
    videos = []
    for root, dirs, files in os.walk(download_location):
        for file in files:
            if file.endswith(('.mp4', '.webm', '.mkv')):
                videos.append(os.path.join(root, file))
    return videos

def list_downloaded_videos():
    videos = get_downloaded_videos()
    video_list = []
    for i, video in enumerate(videos, 1):
        relative_path = os.path.relpath(video, current_app.root_path)
        video_list.append({
            'id': i,
            'name': os.path.basename(video),
            'path': relative_path,
            'size': os.path.getsize(video)
        })
    return video_list

class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)

def my_hook(d):
    if d['status'] == 'downloading':
        progress = {
            'status': 'Đang tải xuống...',
            'filename': d.get('filename', 'Unknown'),
            'percent': d.get('_percent_str', 'Unknown'),
            'speed': d.get('_speed_str', 'Unknown'),
            'eta': d.get('_eta_str', 'Unknown')
        }
    elif d['status'] == 'finished':
        progress = {
            'status': 'Đã tải xuống xong',
            'filename': d.get('filename', 'Unknown'),
            'percent': '100%'
        }
    else:
        progress = {
            'status': d['status'],
            'filename': d.get('filename', 'Unknown')
        }
    
    current_app.config['DOWNLOAD_PROGRESS'] = json.dumps(progress)

class CustomHTTPHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(self.getConnection, req)

    def getConnection(self, host, timeout=300):
        return ssl.create_default_context(ssl._create_unverified_context()).wrap_socket(
            socket.create_connection((host, 443), timeout=timeout),
            server_hostname=host,
        )

def custom_dl_download(url, download_location):
    ph_url_check(url)
    alive_status = ph_alive_check(url)
    if "URL tồn tại và có thể truy cập" not in alive_status:
        raise Exception(alive_status)
    
    app_root = current_app.root_path
    full_download_path = os.path.join(app_root, DOWNLOAD_LOCATION, 'handpicked')
    os.makedirs(full_download_path, exist_ok=True)
    outtmpl = os.path.join(full_download_path, '%(title)s.%(ext)s')
    ydl_opts = {
        'format': 'best',
        'outtmpl': outtmpl,
        'nooverwrites': True,
        'no_warnings': False,
        'ignoreerrors': True,
        'nocheckcertificate': True,
        'progress_hooks': [my_hook],
        'logger': MyLogger()
    }

    opener = urllib.request.build_opener(CustomHTTPHandler())
    urllib.request.install_opener(opener)

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as e:
            raise Exception(f"Lỗi khi tải xuống: {str(e)}")

def upload_with_progress(bot, chat_id, video_path):
    file_size = os.path.getsize(video_path)
    with open(video_path, 'rb') as video_file:
        current_app.config['UPLOAD_PROGRESS'] = json.dumps({'percent': '0%'})
        sent = 0
        start_time = time.time()
        for chunk in iter(lambda: video_file.read(4096), b''):
            bot.send_chat_action(chat_id=chat_id, action="upload_video")
            sent += len(chunk)
            elapsed_time = time.time() - start_time
            speed = sent / elapsed_time if elapsed_time > 0 else 0
            progress = {
                'percent': f"{(sent / file_size * 100):.1f}%",
                'speed': f"{speed / 1024 / 1024:.2f} MB/s"
            }
            current_app.config['UPLOAD_PROGRESS'] = json.dumps(progress)
        
        video_file.seek(0)
        bot.send_video(chat_id=chat_id, video=video_file)


# Khởi tạo bot Telegram
BOT_TOKEN = '7930718317:AAHjn9fCqLb1sXIpd7eBGr6Pp3r1W6RQmXA'
bot = telegram.Bot(token=BOT_TOKEN)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes

DOWNLOAD_LOCATION = os.path.join('static', 'pornhub_video')

executor = ThreadPoolExecutor(max_workers=1)

async def get_bot():
    timeout = httpx.Timeout(5.0, connect=60, read=3600, write=3600, pool=None)
    async with httpx.AsyncClient(timeout=timeout) as client:
        bot = telegram.Bot(token='7930718317:AAHjn9fCqLb1sXIpd7eBGr6Pp3r1W6RQmXA')
        await bot.initialize()
        yield bot
        await bot.shutdown()

async def split_and_send_video(video_path):
    file_size = os.path.getsize(video_path)
    if file_size <= MAX_FILE_SIZE:
        app.config['UPLOAD_PROGRESS'] = json.dumps({'status': 'Đang gửi file nguyên vẹn', 'progress': '0%'})
        await send_single_file(video_path)
    else:
        app.config['UPLOAD_PROGRESS'] = json.dumps({'status': 'Chuẩn bị chia nhỏ file', 'progress': '0%'})
        await split_and_send(video_path)


async def send_single_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            await bot.send_document(
                chat_id='-1002455680989',
                document=file,
                filename=os.path.basename(file_path)
            )
        app.config['UPLOAD_PROGRESS'] = json.dumps({'status': 'Đã gửi xong file', 'progress': '100%'})
    except TelegramError as e:
        app.config['UPLOAD_PROGRESS'] = json.dumps({'status': f'Lỗi khi gửi file: {str(e)}', 'progress': '0%'})
        print(f"Lỗi khi gửi file: {str(e)}")
        raise
    
async def split_and_send(video_path):
    file_size = os.path.getsize(video_path)
    chunk_size = MAX_FILE_SIZE
    total_chunks = (file_size + chunk_size - 1) // chunk_size

    with open(video_path, 'rb') as video_file:
        for i in range(total_chunks):
            chunk = video_file.read(chunk_size)
            chunk_filename = f"{os.path.basename(video_path)}.part{i+1}"
            
            try:
                await bot.send_document(
                    chat_id='-1002455680989',
                    document=chunk,
                    filename=chunk_filename,
                    caption=f"Phần {i+1}/{total_chunks} của {os.path.basename(video_path)}"
                )
                progress = (i + 1) / total_chunks * 100
                app.config['UPLOAD_PROGRESS'] = json.dumps({
                    'status': f'Đã gửi phần {i+1}/{total_chunks}',
                    'progress': f'{progress:.2f}%'
                })
            except TelegramError as e:
                error_message = f'Lỗi khi gửi phần {i+1}: {str(e)}'
                app.config['UPLOAD_PROGRESS'] = json.dumps({
                    'status': 'error',
                    'message': error_message,
                    'progress': f'{(i / total_chunks * 100):.2f}%'
                })
                print(error_message)
                return  # Thay vì raise, chúng ta return để tiếp tục xử lý

    app.config['UPLOAD_PROGRESS'] = json.dumps({'status': 'Đã gửi xong tất cả các phần', 'progress': '100%'})

def run_async(coroutine):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coroutine)


async def send_large_video(video_path):
    async for bot in get_bot():
        try:
            with open(video_path, 'rb') as video_file:
                await bot.send_chat_action(chat_id='-1002455680989', action="upload_video")
                
                # Sử dụng phương thức send_document thay vì send_video để có thể upload file lớn
                await bot.send_document(
                    chat_id='-1002455680989',
                    document=video_file,
                    filename=os.path.basename(video_path),
                    write_timeout=3600,
                    connect_timeout=60,
                    pool_timeout=3600,
                    read_timeout=3600
                )
        except Exception as e:
            print(f"Lỗi khi gửi video: {str(e)}")
            raise

async def send_video(video_path):
    timeout = aiohttp.ClientTimeout(total=3600)  # 1 giờ
    async with aiohttp.ClientSession(timeout=timeout) as session:
        bot = telegram.Bot(token='7930718317:AAHjn9fCqLb1sXIpd7eBGr6Pp3r1W6RQmXA', session=session)
        retries = 3
        for attempt in range(retries):
            try:
                with open(video_path, 'rb') as video_file:
                    await bot.send_video(chat_id='-1002455680989', video=video_file)
                break
            except Exception as e:
                if attempt == retries - 1:
                    raise
                print(f"Lỗi khi upload, thử lại lần {attempt + 2}: {str(e)}")
                await asyncio.sleep(5)

@pornhub_bp.route('/download')
def download():
    return render_template('pornhub/pornhub.html')

@pornhub_bp.route('/execute/', methods=['POST'])
def execute():
    data = request.json
    if not data:
        return jsonify({"message": "Không có dữ liệu được gửi", "status": False}), 400
    
    url = data.get('url')
    if not url:
        return jsonify({"message": "Không có URL được cung cấp", "status": False}), 400

    try:
        url_status = ph_alive_check(url)
        if "không tồn tại" in url_status:
            return jsonify({"message": url_status, "status": False}), 400
        
        current_app.config['DOWNLOAD_PROGRESS'] = json.dumps({
            'status': 'Đang bắt đầu tải xuống...',
            'progress': '0%'
        })
        download_in_thread(url, DOWNLOAD_LOCATION, current_app._get_current_object())
        return jsonify({"message": "Đang bắt đầu tải xuống...", "status": True})
    except Exception as e:
        return jsonify({"message": str(e), "status": False}), 500

from threading import Thread
def download_in_thread(url, download_location, app):
    def run_with_context():
        with app.app_context():
            custom_dl_download(url, download_location)
    
    thread = Thread(target=run_with_context)
    thread.start()
    return thread


@pornhub_bp.route('/delete_video/', methods=['POST'])
def delete_video():
    video_path = request.json.get('video_path')
    if not video_path:
        return jsonify({"error": "Không có đường dẫn video được cung cấp"}), 400
    
    try:
        os.remove(video_path)
        return jsonify({"message": f"Đã xóa video {os.path.basename(video_path)}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@pornhub_bp.route('/list_videos/', methods=['GET'])
def list_videos():
    try:
        videos = list_downloaded_videos()
        return jsonify({"videos": videos})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@pornhub_bp.route('/listvideo')
def listvideo():
    return render_template('pornhub/listvideo.html')

@pornhub_bp.route('/reveal_in_finder/', methods=['POST'])
def reveal_in_finder():
    video_path = request.json.get('video_path')
    if not video_path:
        return jsonify({"error": "Không có đường dẫn video được cung cấp"}), 400
    
    try:
        full_path = os.path.join(current_app.root_path, video_path)
        if os.path.exists(full_path):
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', '-R', full_path])
            elif sys.platform == 'win32':  # Windows
                subprocess.run(['explorer', '/select,', full_path])
            else:  # Linux và các hệ điều hành khác
                subprocess.run(['xdg-open', os.path.dirname(full_path)])
            return jsonify({"message": f"Đã mở thư mục chứa {os.path.basename(video_path)}"}), 200
        else:
            return jsonify({"error": "File không tồn tại"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@pornhub_bp.route('/progress')
def progress():
    return jsonify(progress=current_app.config.get('DOWNLOAD_PROGRESS', '{}'))

@pornhub_bp.route('/upload_to_telegram/', methods=['POST'])
def upload_to_telegram():
    video_path = request.json.get('video_path')
    if not video_path:
        return jsonify({"error": "Không có đường dẫn video được cung cấp"}), 400
    
    try:
        executor.submit(run_async, split_and_send_video(video_path))
        return jsonify({"message": f"Đang upload video {os.path.basename(video_path)} lên Telegram"}), 202
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@pornhub_bp.route('/upload_progress/')
def get_upload_progress():
    return current_app.config.get('UPLOAD_PROGRESS', json.dumps({'percent': '0%', 'speed': '0 MB/s'}))