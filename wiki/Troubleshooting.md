# Troubleshooting Guide

## Common Issues and Solutions

This guide covers common problems you might encounter while using Muze and how to solve them.

---

## Installation Issues

### Python Module Not Found

**Error**:
```
ModuleNotFoundError: No module named 'flask'
```

**Solution**:
```bash
pip install flask
# Or install all dependencies
pip install Flask Algorithmia Pillow numpy matplotlib Jinja2
```

**Verify Installation**:
```bash
python -c "import flask; print(flask.__version__)"
```

---

### Pickle Loading Error

**Error**:
```
UnicodeDecodeError: 'ascii' codec can't decode byte 0x80 in position 0
```

**Solution**: Ensure encoding parameter is used
```python
with open("test.txt", "rb") as fp:
    songnames = pickle.load(fp, encoding='latin1')
```

---

### Port Already in Use

**Error**:
```
OSError: [Errno 48] Address already in use
```

**Solution 1**: Kill existing process
```bash
# Find process
lsof -i :5000

# Kill process
kill -9 <PID>
```

**Solution 2**: Use different port
```python
# In app.py
app.run(debug=True, port=5001)
```

---

## Webcam Issues

### Webcam Not Detected

**Error**: "getUserMedia not supported" or no video preview

**Solutions**:

1. **Check Browser Support**
   - Use Chrome, Firefox, Safari, or Edge
   - Update browser to latest version
   - IE not supported

2. **Check Permissions**
   - Click lock icon in address bar
   - Ensure camera permission is "Allow"
   - Reload page after changing permissions

3. **Check Hardware**
   - Verify webcam works in other apps
   - Try different USB port
   - Check if another app is using camera

4. **HTTPS Requirement**
   - Some browsers require HTTPS for webcam
   - Use `localhost` (exempt from HTTPS requirement)
   - Or set up SSL certificate

---

### Video Preview Black Screen

**Problem**: Video element shows but is black

**Solutions**:

1. **Check Lighting**
   - Ensure room has adequate light
   - Camera lens not covered

2. **Driver Issues**
   - Update webcam drivers
   - Restart computer

3. **Browser Cache**
   - Clear browser cache
   - Try incognito/private mode

---

### Permission Denied

**Error**: "Permission denied" or "NotAllowedError"

**Solutions**:

1. **Grant Permission**
   - Click "Allow" when prompted
   - Check browser settings → Privacy → Camera

2. **System Settings**
   - **macOS**: System Preferences → Security & Privacy → Camera
   - **Windows**: Settings → Privacy → Camera
   - Ensure browser has camera access

3. **Browser Reset**
   - Reset site permissions
   - Clear site data
   - Restart browser

---

## API Issues

### Invalid API Key

**Error**: `AlgorithmException: authorization required`

**Solutions**:

1. **Verify API Key**
   ```python
   # Check algorithmia.py line 17
   client = Algorithmia.client('simYOUR_KEY_HERE')
   ```

2. **Get New Key**
   - Visit [algorithmia.com](https://algorithmia.com/)
   - Profile → Credentials
   - Copy API key

3. **Check Format**
   - Key should start with "sim"
   - No extra spaces or quotes
   - No newlines

---

### API Timeout

**Error**: Connection timeout or no response

**Solutions**:

1. **Check Internet**
   ```bash
   ping algorithmia.com
   ```

2. **Increase Timeout**
   ```python
   algo = client.algo('deeplearning/EmotionRecognitionCNNMBP/1.0.1')
   algo.set_options(timeout=300)  # 5 minutes
   ```

3. **Retry Logic**
   ```python
   import time
   
   max_retries = 3
   for attempt in range(max_retries):
       try:
           result = algo.pipe(input).result
           break
       except Exception as e:
           if attempt < max_retries - 1:
               time.sleep(2 ** attempt)  # Exponential backoff
           else:
               raise
   ```

---

### API Credits Exhausted

**Error**: "Insufficient credits" or 402 Payment Required

**Solutions**:

1. **Check Account**
   - Log in to Algorithmia
   - Check credit balance
   - Free tier: 5,000 credits/month

2. **Upgrade Plan**
   - Purchase additional credits
   - Upgrade to paid plan

3. **Optimize Usage**
   - Reduce snapshot frequency
   - Cache emotion results
   - Use lower resolution images

---

## Playlist Issues

### No Playlist Generated

**Problem**: Page reloads but no songs play

**Debug Steps**:

1. **Check Console**
   ```javascript
   // Press F12 → Console tab
   // Look for errors
   ```

2. **Verify Snapshot**
   ```bash
   # Check if snapshot was created
   ls -la snapshots/pic.png
   ```

3. **Test API Manually**
   ```python
   import Algorithmia
   
   client = Algorithmia.client('YOUR_KEY')
   algo = client.algo('deeplearning/EmotionRecognitionCNNMBP/1.0.1')
   
   input = bytearray(open("snapshots/pic.png", "rb").read())
   result = algo.pipe(input).result
   print(result)
   ```

4. **Check Server Logs**
   ```bash
   # Look at terminal output
   # Should show "Getting emotion..."
   ```

---

### Songs Not Playing

**Problem**: Playlist loads but audio doesn't start

**Solutions**:

1. **Check Audio Files**
   ```bash
   # Verify MP3 files exist
   ls static/music/*.mp3 | wc -l
   # Should show 903
   ```

2. **Check File Permissions**
   ```bash
   chmod 644 static/music/*.mp3
   ```

3. **Browser Audio**
   - Check browser isn't muted
   - Check system volume
   - Try different browser

4. **File Format**
   - Ensure files are valid MP3
   - Test file in media player
   - Re-encode if corrupted

---

### Wrong Song Names

**Problem**: Song names don't match audio

**Solution**: Verify `test.txt` and MP3 files are synchronized

```python
# Test script
import pickle

with open("test.txt", "rb") as fp:
    songnames = pickle.load(fp, encoding='latin1')

# Check specific song
print(f"Song 234: {songnames[234]}")
# Verify 234.mp3 matches this song
```

---

## Performance Issues

### Slow Page Load

**Problem**: Page takes long to load

**Solutions**:

1. **Check Network**
   - F12 → Network tab
   - Look for slow requests
   - Check file sizes

2. **Optimize Images**
   ```javascript
   // Reduce canvas resolution
   <canvas width="320" height="240"></canvas>
   ```

3. **Enable Caching**
   ```python
   @app.after_request
   def add_cache_headers(response):
       response.cache_control.max_age = 300
       return response
   ```

---

### High Memory Usage

**Problem**: Server uses too much memory

**Solutions**:

1. **Restart Server**
   ```bash
   # Stop server (Ctrl+C)
   # Start again
   python app.py
   ```

2. **Clear Snapshots**
   ```bash
   rm snapshots/*.png
   ```

3. **Limit Workers**
   ```bash
   # If using Gunicorn
   gunicorn -w 2 app:app  # Reduce workers
   ```

---

### Slow Emotion Detection

**Problem**: Takes >10 seconds to get playlist

**Solutions**:

1. **Check Internet Speed**
   ```bash
   speedtest-cli
   ```

2. **Reduce Image Size**
   ```javascript
   // Use JPEG with compression
   var dataURL = canvas.toDataURL("image/jpeg", 0.7);
   ```

3. **Use Async Processing**
   ```python
   from threading import Thread
   
   def async_emotion_detection():
       # Process in background
       pass
   
   Thread(target=async_emotion_detection).start()
   ```

---

## Display Issues

### Emotion Grid Not Showing

**Problem**: Click "Stop WebCam" but no graph appears

**Solutions**:

1. **Check File Creation**
   ```bash
   ls -la static/graph.jpg
   ```

2. **Check Matplotlib**
   ```python
   import matplotlib
   print(matplotlib.__version__)
   ```

3. **Backend Issues**
   ```python
   # Add to algorithmia.py
   import matplotlib
   matplotlib.use('Agg')  # Non-interactive backend
   import matplotlib.pyplot as plt
   ```

---

### UI Elements Misaligned

**Problem**: Buttons or video in wrong position

**Solutions**:

1. **Clear Browser Cache**
   - Ctrl+Shift+Delete
   - Clear cached images and files

2. **Check CSS**
   - Verify `styling.css` loaded
   - F12 → Elements → Styles

3. **Browser Compatibility**
   - Test in different browser
   - Update browser to latest version

---

## Error Messages

### "No face detected"

**Meaning**: API couldn't find a face in the image

**Solutions**:

1. **Improve Conditions**
   - Better lighting
   - Face camera directly
   - Remove obstructions
   - Get closer to camera

2. **Check Image Quality**
   ```python
   # View captured image
   from PIL import Image
   img = Image.open("snapshots/pic.png")
   img.show()
   ```

3. **Adjust Timing**
   ```javascript
   // Give more time before snapshot
   setTimeout(snapshot, 10000);  // 10 seconds
   ```

---

### "CORS policy" Error

**Error**: "blocked by CORS policy"

**Solution**:
```bash
pip install flask-cors
```

```python
# Add to app.py
from flask_cors import CORS
CORS(app)
```

---

### "Cannot read property 'split' of undefined"

**Error**: JavaScript error in console

**Cause**: Empty playlist or malformed song entry

**Solution**:
```javascript
// Add null check
if (songlist && songlist[i]) {
    var parts = songlist[i].split("_");
    // ... rest of code
}
```

---

## Database Issues

### test.txt Not Found

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'test.txt'`

**Solutions**:

1. **Check File Exists**
   ```bash
   ls -la test.txt
   ```

2. **Check Working Directory**
   ```python
   import os
   print(os.getcwd())
   ```

3. **Use Absolute Path**
   ```python
   import os
   db_path = os.path.join(os.path.dirname(__file__), 'test.txt')
   with open(db_path, "rb") as fp:
       songnames = pickle.load(fp, encoding='latin1')
   ```

---

### Corrupted Database

**Error**: `UnpicklingError` or `EOFError`

**Solution**: Re-create database

```python
import pickle

# Create new song list
songs = [
    "Song 1 - Artist 1",
    "Song 2 - Artist 2",
    # ... add all 903 songs
]

# Save as pickle
with open("test.txt", "wb") as fp:
    pickle.dump(songs, fp)
```

---

## Deployment Issues

### Production Server Won't Start

**Problem**: Works locally but not on server

**Solutions**:

1. **Check Permissions**
   ```bash
   chmod +x app.py
   ```

2. **Check Python Version**
   ```bash
   python --version
   # Should be 2.7 or 3.6+
   ```

3. **Check Dependencies**
   ```bash
   pip list
   # Verify all packages installed
   ```

4. **Check Firewall**
   ```bash
   # Allow port 5000
   sudo ufw allow 5000
   ```

---

### HTTPS Issues

**Problem**: Webcam not working on deployed site

**Solution**: Use HTTPS

```bash
# Generate self-signed certificate (development)
openssl req -x509 -newkey rsa:4096 -nodes \
  -out cert.pem -keyout key.pem -days 365

# Run with SSL
python app.py --cert=cert.pem --key=key.pem
```

Or use production server with SSL:
```bash
gunicorn --certfile=cert.pem --keyfile=key.pem app:app
```

---

## Debug Mode

### Enable Detailed Logging

```python
# Add to app.py
import logging

logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

@app.route('/hook', methods=['POST'])
def get_image():
    app.logger.debug(f"Received image data: {len(request.values['imageBase64'])} bytes")
    # ... rest of code
```

---

### Browser Developer Tools

**Open**: Press F12

**Useful Tabs**:
- **Console**: JavaScript errors
- **Network**: API calls, file loading
- **Application**: Local storage, cookies
- **Sources**: Debug JavaScript

---

## Getting Help

### Information to Provide

When asking for help, include:

1. **Error Message**: Full error text
2. **Browser**: Name and version
3. **OS**: Windows/Mac/Linux version
4. **Python Version**: `python --version`
5. **Steps to Reproduce**: What you did before error
6. **Console Output**: Terminal and browser console
7. **Network Tab**: Any failed requests

### Example Bug Report

```
**Problem**: Playlist not generating

**Error**: "AlgorithmException: authorization required"

**Environment**:
- OS: Windows 10
- Python: 3.9.5
- Browser: Chrome 91
- Algorithmia SDK: 1.8.0

**Steps**:
1. Started server with `python app.py`
2. Opened http://localhost:5000
3. Allowed webcam access
4. Waited 5 seconds
5. Page reloaded but no songs

**Console Output**:
```
Getting emotion...
Traceback (most recent call last):
  ...
AlgorithmException: authorization required
```

**What I Tried**:
- Verified API key is correct
- Checked internet connection
- Restarted server
```

---

## Quick Diagnostic Script

```python
#!/usr/bin/env python
"""Diagnostic script for Muze"""

import os
import sys

def check_environment():
    print("=== Muze Diagnostic ===\n")
    
    # Python version
    print(f"Python: {sys.version}")
    
    # Check modules
    modules = ['flask', 'Algorithmia', 'PIL', 'numpy', 'matplotlib']
    for mod in modules:
        try:
            __import__(mod)
            print(f"✓ {mod} installed")
        except ImportError:
            print(f"✗ {mod} NOT installed")
    
    # Check files
    files = ['app.py', 'algorithmia.py', 'test.txt']
    for f in files:
        if os.path.exists(f):
            print(f"✓ {f} exists")
        else:
            print(f"✗ {f} NOT found")
    
    # Check directories
    dirs = ['templates', 'static/music', 'snapshots']
    for d in dirs:
        if os.path.exists(d):
            print(f"✓ {d}/ exists")
        else:
            print(f"✗ {d}/ NOT found")
    
    # Check music files
    music_count = len([f for f in os.listdir('static/music') if f.endswith('.mp3')])
    print(f"\nMusic files: {music_count}/903")
    
    # Check API key
    with open('algorithmia.py', 'r') as f:
        content = f.read()
        if 'api-key' in content:
            print("⚠ API key not configured")
        else:
            print("✓ API key appears configured")

if __name__ == '__main__':
    check_environment()
```

Run with:
```bash
python diagnostic.py
```
