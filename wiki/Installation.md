# Installation Guide

## Prerequisites

### System Requirements

- **Operating System**: Windows, macOS, or Linux
- **Python**: Version 2.7 or 3.6+ (code uses Python 2 pickle format)
- **Webcam**: Required for emotion detection
- **Internet**: Required for Algorithmia API calls
- **Browser**: Modern browser with WebRTC support (Chrome, Firefox, Safari, Edge)

### Required Accounts

- **Algorithmia Account**: Free tier available at [algorithmia.com](https://algorithmia.com/)

---

## Step-by-Step Installation

### 1. Clone or Download Repository

```bash
# If using git
git clone <repository-url>
cd muze

# Or download and extract ZIP file
```

### 2. Install Python Dependencies

#### Using pip

```bash
pip install Flask==0.12.2
pip install hsaudiotag==1.1.1
pip install Jinja2==2.10
pip install matplotlib==2.1.2
pip install numpy==1.14.0
pip install Pillow==5.0.0
pip install simplejson==3.13.2
pip install six==1.11.0
pip install urllib3==1.22
pip install Werkzeug==0.14.1
pip install Algorithmia
```

#### Using requirements.txt (if available)

```bash
pip install -r requirements.txt
```

#### Create requirements.txt

If not present, create `requirements.txt`:

```txt
Flask==0.12.2
hsaudiotag==1.1.1
Jinja2==2.10
matplotlib==2.1.2
numpy==1.14.0
Pillow==5.0.0
simplejson==3.13.2
six==1.11.0
urllib3==1.22
Werkzeug==0.14.1
Algorithmia>=1.0.0
```

### 3. Get Algorithmia API Key

1. Visit [algorithmia.com](https://algorithmia.com/)
2. Sign up for a free account
3. Navigate to your profile
4. Click on "Credentials" section
5. Copy your API key (starts with "sim...")

### 4. Configure API Key

Open `algorithmia.py` and replace the API key on line 17:

```python
# Before
client = Algorithmia.client('api-key')

# After
client = Algorithmia.client('simYOUR_ACTUAL_API_KEY_HERE')
```

**⚠️ Security Note**: Never commit your API key to version control!

**Better approach** (recommended):

Create a `.env` file:
```bash
ALGORITHMIA_API_KEY=simYOUR_ACTUAL_API_KEY_HERE
```

Update `algorithmia.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()
client = Algorithmia.client(os.getenv('ALGORITHMIA_API_KEY'))
```

Install python-dotenv:
```bash
pip install python-dotenv
```

### 5. Verify Directory Structure

Ensure these directories exist:

```bash
muze/
├── app.py
├── algorithmia.py
├── test.txt
├── snapshots/          # Create if missing
├── static/
│   ├── music/          # Should contain 001.mp3 - 903.mp3
│   └── jquery-1.7.1.min.js
└── templates/
    ├── base.html
    └── musi.html
```

Create missing directories:

```bash
mkdir -p snapshots
mkdir -p static/music
```

### 6. Verify Music Files

Check that music files are present:

```bash
# Windows
dir static\music\*.mp3

# macOS/Linux
ls static/music/*.mp3
```

You should see files: `001.mp3`, `002.mp3`, ..., `903.mp3`

**If music files are missing**: You'll need to obtain them from the MIREX 2007 dataset or provide your own music library.

---

## Running the Application

### Start the Server

```bash
python app.py
```

Expected output:
```
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: XXX-XXX-XXX
```

### Access the Application

1. Open your web browser
2. Navigate to: `http://localhost:5000`
3. Allow webcam access when prompted
4. Wait 5 seconds for initial snapshot
5. Enjoy your personalized playlist!

---

## Troubleshooting Installation

### Python Version Issues

**Problem**: `SyntaxError` or compatibility issues

**Solution**: Check Python version
```bash
python --version
```

If using Python 3, ensure all code is compatible or use Python 2.7.

### Pickle Loading Error

**Problem**: `UnicodeDecodeError` when loading `test.txt`

**Solution**: Ensure encoding parameter is used
```python
pickle.load(fp, encoding='latin1')
```

### Module Not Found

**Problem**: `ModuleNotFoundError: No module named 'flask'`

**Solution**: Install missing module
```bash
pip install flask
```

### Algorithmia Import Error

**Problem**: `ImportError: No module named Algorithmia`

**Solution**: Install Algorithmia SDK
```bash
pip install Algorithmia
```

### Port Already in Use

**Problem**: `OSError: [Errno 48] Address already in use`

**Solution**: Change port in `app.py`
```python
if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Use different port
```

Or kill existing process:
```bash
# Find process using port 5000
lsof -i :5000

# Kill process
kill -9 <PID>
```

### Webcam Not Working

**Problem**: "getUserMedia not supported" or permission denied

**Solutions**:
1. Use HTTPS (required for some browsers)
2. Check browser permissions
3. Ensure webcam is not in use by another app
4. Try different browser

### API Key Invalid

**Problem**: `AlgorithmException: authorization required`

**Solution**: 
1. Verify API key is correct
2. Check Algorithmia account is active
3. Ensure API key has proper permissions

### Missing Music Files

**Problem**: Audio player shows error or no sound

**Solution**:
1. Verify MP3 files exist in `static/music/`
2. Check file naming (001.mp3, not 1.mp3)
3. Ensure files are valid MP3 format

---

## Verification Tests

### Test 1: Python Environment

```bash
python -c "import flask, Algorithmia, PIL, numpy, matplotlib; print('All modules imported successfully')"
```

### Test 2: File Permissions

```bash
# Check read permissions
python -c "import pickle; pickle.load(open('test.txt', 'rb'), encoding='latin1'); print('Song database loaded')"

# Check write permissions
python -c "open('snapshots/test.txt', 'w').write('test'); print('Snapshot directory writable')"
```

### Test 3: API Connection

```python
import Algorithmia

client = Algorithmia.client('YOUR_API_KEY')
algo = client.algo('deeplearning/EmotionRecognitionCNNMBP/1.0.1')
print("API connection successful")
```

### Test 4: Server Start

```bash
python app.py &
curl http://localhost:5000
# Should return HTML content
```

---

## Docker Installation (Alternative)

### Create Dockerfile

```dockerfile
FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_ENV=development

CMD ["python", "app.py"]
```

### Build and Run

```bash
# Build image
docker build -t muze .

# Run container
docker run -p 5000:5000 -e ALGORITHMIA_API_KEY=your_key muze
```

---

## Virtual Environment (Recommended)

### Create Virtual Environment

```bash
# Python 3
python -m venv venv

# Python 2
virtualenv venv
```

### Activate Virtual Environment

```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Deactivate

```bash
deactivate
```

---

## Production Deployment

### Using Gunicorn (Linux/macOS)

```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Waitress (Windows)

```bash
# Install Waitress
pip install waitress

# Run server
waitress-serve --port=5000 app:app
```

### Environment Variables

Create `.env` file for production:

```bash
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your_secure_random_secret_key
ALGORITHMIA_API_KEY=your_api_key
```

### Security Checklist

- [ ] Change Flask secret key from "bacon"
- [ ] Move API key to environment variable
- [ ] Use HTTPS in production
- [ ] Configure CORS properly
- [ ] Add rate limiting
- [ ] Implement input validation
- [ ] Set up logging
- [ ] Configure firewall rules

---

## Next Steps

After successful installation:

1. Read the [Quick Start Guide](Quick-Start.md)
2. Review [Configuration](Configuration.md) options
3. Explore [API Reference](API-Reference.md)
4. Check [Troubleshooting](Troubleshooting.md) for common issues

---

## Uninstallation

### Remove Virtual Environment

```bash
# Deactivate if active
deactivate

# Remove directory
rm -rf venv
```

### Remove Application

```bash
# Delete application directory
rm -rf muze
```

### Uninstall Python Packages

```bash
pip uninstall Flask hsaudiotag Jinja2 matplotlib numpy Pillow simplejson six urllib3 Werkzeug Algorithmia
```
