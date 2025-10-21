# Configuration Guide

## Overview

This guide covers all configuration options for Muze, including API keys, server settings, and customization options.

---

## Required Configuration

### 1. Algorithmia API Key

**Location**: `algorithmia.py` line 17

**Current (Insecure)**:
```python
client = Algorithmia.client('api-key')
```

**Recommended (Secure)**:
```python
import os
from dotenv import load_dotenv

load_dotenv()
client = Algorithmia.client(os.getenv('ALGORITHMIA_API_KEY'))
```

**Setup**:
1. Create `.env` file in project root:
```bash
ALGORITHMIA_API_KEY=simYOUR_ACTUAL_KEY_HERE
```

2. Install python-dotenv:
```bash
pip install python-dotenv
```

3. Add `.env` to `.gitignore`:
```bash
echo ".env" >> .gitignore
```

**Get API Key**:
1. Visit [algorithmia.com](https://algorithmia.com/)
2. Sign up or log in
3. Navigate to Profile → Credentials
4. Copy API key (starts with "sim")

---

### 2. Flask Secret Key

**Location**: `app.py` line 12

**Current (Insecure)**:
```python
app.secret_key = "bacon"
```

**Recommended (Secure)**:
```python
import os
from dotenv import load_dotenv

load_dotenv()
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key')
```

**Generate Secure Key**:
```python
import secrets
print(secrets.token_hex(32))
```

**Add to `.env`**:
```bash
FLASK_SECRET_KEY=your_generated_key_here
```

---

## Server Configuration

### Flask Development Server

**Location**: `app.py` line 37-38

**Current**:
```python
if __name__ == '__main__':
    app.run(debug=True)
```

**Configuration Options**:
```python
app.run(
    host='0.0.0.0',      # Listen on all interfaces
    port=5000,           # Port number
    debug=True,          # Debug mode (disable in production)
    threaded=True,       # Handle multiple requests
    ssl_context=None     # SSL configuration
)
```

### Environment-Based Configuration

**Recommended Approach**:
```python
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == '__main__':
    app.run(
        host=os.getenv('FLASK_HOST', '127.0.0.1'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'True') == 'True'
    )
```

**`.env` Configuration**:
```bash
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=True
FLASK_ENV=development
```

---

## Production Configuration

### Using Gunicorn (Linux/macOS)

**Install**:
```bash
pip install gunicorn
```

**Run**:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**Configuration File** (`gunicorn.conf.py`):
```python
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
timeout = 120
keepalive = 5
errorlog = "logs/error.log"
accesslog = "logs/access.log"
loglevel = "info"
```

**Run with Config**:
```bash
gunicorn -c gunicorn.conf.py app:app
```

---

### Using Waitress (Windows)

**Install**:
```bash
pip install waitress
```

**Run**:
```bash
waitress-serve --port=5000 --threads=4 app:app
```

**Python Script** (`run_production.py`):
```python
from waitress import serve
from app import app

serve(app, host='0.0.0.0', port=5000, threads=4)
```

---

## Emotion Detection Configuration

### Cluster Definitions

**Location**: `algorithmia.py` lines 46-54

**Current Configuration**:
```python
songlist = {
    1: [1, 170],
    2: [171, 334],
    3: [335, 549],
    4: [550, 740],
    5: [741, 903]
}
```

**Customization**: Adjust ranges based on your music library

---

### Emotion-to-Cluster Mapping

**Location**: `algorithmia.py` lines 47-54

**Anger/Fear**:
```python
cluster_def = [[5, 2], [3, 7], [2, 12]]  # 21 songs
```

**Sad**:
```python
cluster_def = [[3, 4], [4, 4], [2, 13]]  # 21 songs
```

**Neutral/Disgust/Surprise**:
```python
cluster_def = [[3, 2], [4, 5], [2, 7], [1, 5]]  # 19 songs
```

**Happy**:
```python
cluster_def = [[2, 10], [4, 5], [1, 6]]  # 21 songs
```

**Customization Example**:
```python
# More energetic happy playlist
if current == "Happy":
    cluster_def = [[1, 15], [2, 5], [4, 1]]  # 21 songs, more from cluster 1
```

---

### Emotion Color Mapping

**Location**: `algorithmia.py` line 34

**Current**:
```python
emotion_color_dict = {
    'Neutral': 11,
    'Sad': 31,
    'Disgust': 51,
    'Fear': 61,
    'Surprise': 41,
    'Happy': 21,
    'Angry': 1
}
```

**Color Scheme** (in `get_emotion_grid()`):
```python
cmap = colors.ListedColormap([
    'red',      # 0-10: Angry
    'blue',     # 10-20: Neutral
    'yellow',   # 20-30: Happy
    'green',    # 30-40: Sad
    'cyan',     # 40-50: Surprise
    'magenta',  # 50-60: Disgust
    'black',    # 60-70: Fear
    'white'     # 80+: No data
])
```

**Customization**: Change colors to match your preference

---

## Frontend Configuration

### Snapshot Timing

**Location**: `templates/musi.html`

**Initial Snapshot Delay**:
```javascript
// Line 123
setTimeout(snapshot, 5000);  // 5 seconds
```

**Recapture Interval**:
```javascript
// Line 112
if (i == 20) {  // After 20 songs
    setTimeout(snapshot, 5000);
}
```

**Customization**:
```javascript
// Faster initial capture
setTimeout(snapshot, 2000);  // 2 seconds

// More frequent recapture
if (i == 10) {  // After 10 songs
    setTimeout(snapshot, 3000);
}
```

---

### Video Preview Size

**Location**: `templates/musi.html` line 28

**Current**:
```html
<video width=200 height=200 id="video" controls autoplay></video>
```

**Customization**:
```html
<!-- Larger preview -->
<video width=400 height=400 id="video" controls autoplay></video>

<!-- Hide preview -->
<video hidden width=200 height=200 id="video" autoplay></video>
```

---

### Canvas Resolution

**Location**: `templates/musi.html` line 23

**Current**:
```html
<canvas hidden id="myCanvas" width="400" height="350"></canvas>
```

**Customization**:
```html
<!-- Higher resolution (better quality, larger file) -->
<canvas hidden id="myCanvas" width="640" height="480"></canvas>

<!-- Lower resolution (faster processing, smaller file) -->
<canvas hidden id="myCanvas" width="320" height="240"></canvas>
```

---

## File Paths Configuration

### Snapshot Directory

**Location**: `app.py` line 24

**Current**:
```python
image_PIL.save("snapshots/pic.png", mode='RGB')
```

**Customization**:
```python
import os

SNAPSHOT_DIR = os.getenv('SNAPSHOT_DIR', 'snapshots')
SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, 'pic.png')

# Ensure directory exists
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

image_PIL.save(SNAPSHOT_FILE, mode='RGB')
```

---

### Music Directory

**Location**: `templates/musi.html` line 116

**Current**:
```javascript
$('#aud').attr('src', '/static/music/' + str);
```

**Customization**:
```javascript
var MUSIC_BASE_URL = '/static/music/';
$('#aud').attr('src', MUSIC_BASE_URL + str);
```

---

### Song Database

**Location**: `algorithmia.py` line 44

**Current**:
```python
with open("test.txt", "rb") as fp:
    songnames = pickle.load(fp, encoding='latin1')
```

**Customization**:
```python
import os

SONG_DB_PATH = os.getenv('SONG_DB_PATH', 'test.txt')

with open(SONG_DB_PATH, "rb") as fp:
    songnames = pickle.load(fp, encoding='latin1')
```

---

## Logging Configuration

### Enable Logging

**Add to `app.py`**:
```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
if not app.debug:
    file_handler = RotatingFileHandler(
        'logs/muze.log',
        maxBytes=10240000,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Muze startup')
```

**Create Logs Directory**:
```bash
mkdir logs
```

---

## CORS Configuration

### Enable CORS

**Install**:
```bash
pip install flask-cors
```

**Add to `app.py`**:
```python
from flask_cors import CORS

app = flask.Flask(__name__)
CORS(app)  # Enable CORS for all routes
```

**Restricted CORS**:
```python
CORS(app, resources={
    r"/hook": {"origins": "http://localhost:3000"},
    r"/graph": {"origins": "http://localhost:3000"}
})
```

---

## Security Configuration

### Content Security Policy

**Add to `app.py`**:
```python
@app.after_request
def set_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "media-src 'self' blob:; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline';"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
```

---

### Rate Limiting

**Install**:
```bash
pip install flask-limiter
```

**Add to `app.py`**:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/hook', methods=['POST'])
@limiter.limit("10 per minute")
def get_image():
    # ... existing code
```

---

## Environment Variables Reference

### Complete `.env` Template

```bash
# Algorithmia Configuration
ALGORITHMIA_API_KEY=simYOUR_KEY_HERE

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_HOST=127.0.0.1
FLASK_PORT=5000

# File Paths
SNAPSHOT_DIR=snapshots
SONG_DB_PATH=test.txt
MUSIC_DIR=static/music

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/muze.log

# Security
ENABLE_CORS=False
RATE_LIMIT_ENABLED=True
```

---

## Configuration Validation

### Startup Checks

**Add to `app.py`**:
```python
import os
import sys

def validate_config():
    """Validate required configuration before starting"""
    errors = []
    
    # Check API key
    if not os.getenv('ALGORITHMIA_API_KEY'):
        errors.append("ALGORITHMIA_API_KEY not set")
    
    # Check required directories
    if not os.path.exists('snapshots'):
        os.makedirs('snapshots')
    
    if not os.path.exists('static/music'):
        errors.append("Music directory not found")
    
    # Check song database
    if not os.path.exists('test.txt'):
        errors.append("Song database (test.txt) not found")
    
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

if __name__ == '__main__':
    validate_config()
    app.run(debug=True)
```

---

## Advanced Configuration

### Custom Emotion Detection Model

**Modify `algorithmia.py`**:
```python
# Use different algorithm version
algo = client.algo('deeplearning/EmotionRecognitionCNNMBP/2.0.0')

# Or different algorithm entirely
algo = client.algo('deeplearning/AlternativeEmotionModel/1.0.0')
```

---

### Multiple Music Libraries

**Create library switcher**:
```python
MUSIC_LIBRARIES = {
    'default': 'test.txt',
    'rock': 'rock_songs.txt',
    'classical': 'classical_songs.txt'
}

def get_playlist(library='default'):
    db_path = MUSIC_LIBRARIES.get(library, 'test.txt')
    with open(db_path, "rb") as fp:
        songnames = pickle.load(fp, encoding='latin1')
    # ... rest of function
```

---

## Configuration Best Practices

### 1. Never Hardcode Secrets
❌ Bad:
```python
client = Algorithmia.client('sim123456789')
```

✅ Good:
```python
client = Algorithmia.client(os.getenv('ALGORITHMIA_API_KEY'))
```

### 2. Use Environment-Specific Config
```python
if os.getenv('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
else:
    app.config['DEBUG'] = True
```

### 3. Validate Configuration
```python
assert os.getenv('ALGORITHMIA_API_KEY'), "API key required"
```

### 4. Document All Options
Keep this configuration guide updated with any new options.

### 5. Use Config Classes
```python
class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

app.config.from_object(DevelopmentConfig)
```
