from flask import Flask, render_template
from routes.youtube.gettranscriptsubtitles import gettranscriptsubtitles_bp
from routes.pornhub.pornhub import pornhub_bp
from routes.tts.google_tts import tts_bp
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Cần thiết cho session

# Đảm bảo rằng secret_key được bảo vệ và không được hard-code trong mã nguồn
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret_key')

# Đảm bảo rằng đường dẫn đến Google Cloud Key được bảo vệ
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'key/your-google-cloud-key.json')

# Đăng ký blueprint
app.register_blueprint(pornhub_bp)
app.register_blueprint(gettranscriptsubtitles_bp)
app.register_blueprint(tts_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/instagram/gioithieu')
def gioithieu():
    return render_template('instagram/gioithieu.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)