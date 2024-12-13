import os
from typing import Literal
from pathlib import Path
from google.cloud import texttospeech
from flask import Blueprint, jsonify, request, render_template
from werkzeug.utils import secure_filename

AUDIO_OUTPUT_DIR = Path("static")
# Ensure the audio output directory exists
AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_LANGUAGES = {
    'vi-VN': {
        'male': 'vi-VN-Standard-B',
        'female': 'vi-VN-Standard-C'
    },
    'en-US': {
        'male': 'en-US-Standard-B', 
        'female': 'en-US-Standard-C'
    }
}

# Create Blueprint
tts_bp = Blueprint('tts', __name__, url_prefix='/tts', 
                   template_folder='templates',
                   static_folder='static')

@tts_bp.route('/synthesize', methods=['POST'])
def synthesize():
    """Convert text to speech using Google Cloud TTS API."""
    try:
        text = request.form['text']
        if not text:
            return jsonify({'error': 'Text is required'}), 400
            
        language = request.form.get('language', 'vi-VN')
        if language not in SUPPORTED_LANGUAGES:
            return jsonify({'error': 'Unsupported language'}), 400
            
        gender = request.form.get('gender', 'female')
        if gender not in ['male', 'female']:
            return jsonify({'error': 'Invalid gender'}), 400

        filename = secure_filename(f"output_{hash(text)}.mp3")
        audio_path = AUDIO_OUTPUT_DIR / filename
        
        synthesize_text(text, str(audio_path), language, gender)
        return jsonify({'audio_url': f"/static/{filename}"})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tts_bp.route('/')
def tts():
    """Render TTS web interface."""
    return render_template('tts/tts.html')

def synthesize_text(
    text: str,
    output_file: str,
    language_code: str = 'vi-VN',
    gender: Literal['male', 'female'] = 'female'
) -> None:
    """
    Convert text to speech and save as MP3 file.

    Args:
        text: Input text to convert
        output_file: Path to save audio file
        language_code: Language code (e.g. 'vi-VN', 'en-US')
        gender: Voice gender ('male' or 'female')

    Raises:
        ValueError: If language or gender is invalid
        Exception: If TTS API call fails
    """
    try:
        client = texttospeech.TextToSpeechClient()

        # Get voice name from supported languages
        voice_name = SUPPORTED_LANGUAGES[language_code][gender]

        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        with open(output_file, 'wb') as out:
            out.write(response.audio_content)
    except Exception as e:
        raise Exception(f"Failed to synthesize text: {e}")