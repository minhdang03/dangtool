from flask import Flask, render_template
from routes.youtube.gettranscriptsubtitles import gettranscriptsubtitles_bp
from routes.pornhub.pornhub import pornhub_bp
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Cần thiết cho session


# Đăng ký blueprint
app.register_blueprint(pornhub_bp)
app.register_blueprint(gettranscriptsubtitles_bp)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/instagram/gioithieu')
def gioithieu():
    return render_template('instagram/gioithieu.html')

if __name__ == '__main__':
    app.run(debug=True,port=5001)
