import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Chỉ sử dụng trong môi trường phát triển!

import logging
logging.basicConfig(level=logging.DEBUG)

from dotenv import load_dotenv
from flask import Blueprint, jsonify, render_template, redirect, url_for, session, request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import base64
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

netflix_bp = Blueprint('netflix', __name__)

# Tải biến môi trường từ file .env
load_dotenv()

# Cấu hình OAuth 2.0
CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:5001/netflix/oauth2callback"]
    }
}
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

flow = Flow.from_client_config(CLIENT_CONFIG, SCOPES)
flow.redirect_uri = "http://localhost:5001/netflix/oauth2callback"

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_gmail_service():
    if 'credentials' not in session:
        return None
    credentials = Credentials(**session['credentials'])
    return build('gmail', 'v1', credentials=credentials)

def get_netflix_emails(service, limit=10):
    query = 'from:info@account.netflix.com subject:"Mã truy cập tạm thời của bạn"'
    results = service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
    messages = results.get('messages', [])

    email_list = []
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        email_data = {
            "id": msg['id'],
            "subject": next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'), 'No Subject'),
            "date": next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Date'), 'Unknown'),
            "code": "Không tìm thấy mã"
        }
        
        body = ""
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/html':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
            body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
        
        soup = BeautifulSoup(body, 'html.parser')
        
        # Tìm nút "Nhận mã"
        get_code_button = soup.find('a', string='Nhận mã')
        if get_code_button and 'href' in get_code_button.attrs:
            verify_link = get_code_button['href']
            try:
                response = requests.get(verify_link)
                if response.status_code == 200:
                    code_soup = BeautifulSoup(response.text, 'html.parser')
                    code_element = code_soup.find('div', {'data-uia': 'travel-verification-pin'})
                    if code_element:
                        email_data["code"] = code_element.text.strip()
            except Exception as e:
                logging.error(f"Lỗi khi truy cập liên kết xác minh: {str(e)}")
        
        # Nếu không tìm thấy mã từ liên kết, tìm trong nội dung email
        if email_data["code"] == "Không tìm thấy mã":
            code_match = re.search(r'\b\d{6}\b', body)
            if code_match:
                email_data["code"] = code_match.group()
        
        email_list.append(email_data)

    return email_list

@netflix_bp.route('/authorize')
def authorize():
    authorization_url, _ = flow.authorization_url(prompt='consent')
    return redirect(authorization_url)

@netflix_bp.route('/oauth2callback')
def oauth2callback():
    # Ensure that state and code are present in the request
    state = request.args.get('state')
    code = request.args.get('code')
    
    if not state or not code:
        return jsonify({"error": "State and code are required"}), 400

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        session['credentials'] = credentials_to_dict(credentials)
        return redirect(url_for('netflix.get_email_list'))
    except Exception as e:
        logging.error(f"Error in oauth2callback: {str(e)}")
        return jsonify({"error": str(e)}), 500

@netflix_bp.route('/get_email_list')
def get_email_list():
    service = get_gmail_service()
    if not service:
        return redirect(url_for('netflix.authorize'))
    
    try:
        email_list = get_netflix_emails(service)
        return jsonify({
            "success": True,
            "emails": email_list
        })
    except Exception as e:
        logging.error(f"Lỗi: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@netflix_bp.route('/get_latest_code')
def get_latest_code():
    service = get_gmail_service()
    if not service:
        return redirect(url_for('netflix.authorize'))
    
    try:
        email_list = get_netflix_emails(service, limit=1)
        if email_list:
            latest_email = email_list[0]
            return jsonify({
                "success": True,
                "time": latest_email["date"],
                "code": latest_email["code"]
            })
        else:
            return jsonify({
                "success": False,
                "error": "Không tìm thấy email Netflix mới"
            }), 404
    except Exception as e:
        logging.error(f"Lỗi: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@netflix_bp.route('/code')
def netflix_code():
    return render_template('netflix/codenetflix.html')
