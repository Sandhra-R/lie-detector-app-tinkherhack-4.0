from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import base64
import cv2
import numpy as np
import os
from analyzer import StressAnalyzer

CWD = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.normpath(os.path.join(CWD, '..', 'Frontend'))

# Serve the frontend static files from the sibling Frontend folder
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)
# Prefer an explicit async mode when using eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

analyzer = StressAnalyzer()

@app.route('/')
def index():
    # Serve the frontend index.html when available
    try:
        return app.send_static_file('index.html')
    except Exception:
        return jsonify({"message": "Lie Detector API Running"})

@app.route('/reset', methods=['POST'])
def reset():
    print('[API] Reset request received')
    analyzer.reset()
    print('[API] Analyzer reset')
    return jsonify({"status": "reset"})

@app.route('/analyze-audio', methods=['POST'])
def analyze_audio():
    print('[API] Audio analysis request received')
    if 'audio' not in request.files:
        print('[API] ERROR: No audio file in request')
        return jsonify({"error": "No audio file"})
    
    audio_file = request.files['audio']
    audio_path = "temp_audio.wav"
    audio_file.save(audio_path)
    print(f'[API] Audio file saved: {audio_path}')
    try:
        result = analyzer.analyze_audio(audio_path)
        print(f'[API] Audio analysis result: {result}')
    finally:
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f'[API] Temp audio file deleted')
        except Exception:
            pass

    return jsonify(result)

@socketio.on('video_frame')
def handle_video_frame(data):
    print(f'[Socket] Received video frame from client')
    # Validate incoming data
    if not data or 'image' not in data:
        print('[Socket] ERROR: No image data in frame')
        emit('analysis_result', {"error": "no_image"})
        return

    # Decode base64 image
    try:
        image_data = data['image'].split(',')[1]
    except Exception as e:
        print(f'[Socket] ERROR: Bad image data format: {e}')
        emit('analysis_result', {"error": "bad_image_data"})
        return
    
    try:
        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            print('[Socket] ERROR: Could not decode image with cv2')
            emit('analysis_result', {"error": "decode_failed"})
            return
        
        # Analyze
        result = analyzer.analyze_frame(img)
        print(f'[Socket] Analysis result: {result}')
        emit('analysis_result', result)
    except Exception as e:
        print(f'[Socket] ERROR during analysis: {e}')
        emit('analysis_result', {"error": str(e)})

if __name__ == '__main__':
    print('='*60)
    print(' Lie Detector Backend Starting')
    print(f' Serving frontend from: {FRONTEND_DIR}')
    print(f' API running on: http://127.0.0.1:5000')
    print('='*60)
    socketio.run(app, debug=True, port=5000, host='127.0.0.1')