# Lie Detector App - Truth AI

Advanced stress analysis system using computer vision and audio analysis.

## ✅ Features

- **Real-time Eye Tracking**: Detects blinks and eye aspect ratio (EAR) for stress measurement
- **Audio Analysis**: Analyzes voice pitch to detect stress indicators  
- **Stress Level Assessment**: Combines visual and audio cues to determine stress level
- **Demo Mode**: Test without a camera - the app simulates realistic data for demonstration
- **Live Dashboard**: Real-time metrics with visual feedback

## 🚀 Quick Start

### Backend Setup
```bash
cd Backend

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

The server will start on `http://127.0.0.1:5000`

### Frontend
Simply open `http://127.0.0.1:5000` in your browser. The frontend is served automatically from the Flask backend.

## 📊 Dashboard Metrics

- **Blink Rate**: Number of eye blinks detected
- **Eye Aspect Ratio (EAR)**: Measurement of eye openness (0.25-0.30 is normal)
- **Voice Pitch**: Fundamental frequency in Hz
- **Stress Level**: Low (green), Medium (orange), or High (red)

## 🎮 How to Use

1. **Click "Start Analysis"** - The app will either:
   - Request camera access (if available), OR
   - Fall back to TEST MODE with simulated frames
   
2. **Watch the metrics update** - Real-time analysis data refreshes every ~200ms

3. **"Hold to Record Voice"** - Press and hold to record audio for voice analysis

4. **"Reset"** - Clears the metrics and starts fresh

## 🔧 Running Modes

### Real Camera Mode
- Requires camera/microphone permissions
- Actual eye tracking via MediaPipe
- Real voice pitch analysis

### Demo/Test Mode (Auto Fallback)
- No camera required - perfect for testing
- Simulates realistic eye tracking data
- Shows data changes and stress level transitions
- Backend still runs real analysis on synthetic frames

## 🐛 Troubleshooting

### No data showing?
- Check browser console (F12) for errors
- Verify socket.io connection (should see "✓ Connected to server")
- If camera access fails, it automatically falls back to TEST MODE

### Camera/microphone not working?
- The app falls back to test mode automatically
- Check browser permissions for camera access
- Works fine with test mode for demonstrations

### Backend errors? 
- MediaPipe is optional - the app runs in demo mode without it
- Check terminal output for [Socket] or [API] log messages
- Ensure port 5000 is available

## 📁 Project Structure

```
lie-detector-app/
├── Backend/
│   ├── app.py              # Flask + Socket.IO server
│   ├── analyzer.py         # Analysis engine
│   └── requirements.txt    # Python dependencies
├── Frontend/
│   ├── index.html          # HTML structure
│   ├── app.js              # Client-side logic
│   └── style.css           # Styling
└── README.md
```

## 🔌 API Endpoints

- `GET /` - Serves the frontend
- `POST /reset` - Resets analyzer state
- `POST /analyze-audio` - Analyzes uploaded audio file
- `socket.io` - WebSocket for real-time video frame analysis

## ⚙️ Technical Details

- **Frontend**: Vanilla JavaScript + Socket.IO (polling mode)
- **Backend**: Flask + Flask-SocketIO + MediaPipe (optional)
- **Analysis**: OpenCV, NumPy, Librosa for audio
- **Architecture**: Real-time frame processing at ~5 FPS

## 📝 Notes

- The app works with or without MediaPipe installed
- Demo mode provides realistic test data for UI testing
- All data processing is client-side friendly with Socket.IO events
