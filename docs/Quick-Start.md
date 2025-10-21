# Quick Start Guide

## Get Up and Running in 5 Minutes

This guide will help you start using Muze as quickly as possible.

## Prerequisites

✅ Python installed (2.7 or 3.6+)  
✅ Webcam available  
✅ Internet connection  
✅ Algorithmia API key

---

## Quick Setup

### 1. Install Dependencies (2 minutes)

```bash
pip install Flask Algorithmia Pillow numpy matplotlib Jinja2
```

### 2. Configure API Key (1 minute)

Edit `algorithmia.py` line 17:

```python
client = Algorithmia.client('YOUR_API_KEY_HERE')
```

Get your API key: [algorithmia.com/users/sign_up](https://algorithmia.com/users/sign_up)

### 3. Start the Server (30 seconds)

```bash
python app.py
```

### 4. Open in Browser (30 seconds)

Navigate to: **http://localhost:5000**

### 5. Allow Webcam Access (30 seconds)

Click "Allow" when browser asks for camera permission.

### 6. Wait for Magic (5 seconds)

The app will:
- Capture your facial expression
- Detect your emotion
- Generate a personalized playlist
- Start playing music automatically

---

## First Use Walkthrough

### What You'll See

1. **Initial Page Load**
   - Webcam preview in bottom-right corner
   - Audio player at top
   - Two buttons: "Stop WebCam" and "Get more music"

2. **After 5 Seconds**
   - Page reloads with your personalized playlist
   - Music starts playing automatically
   - Song name appears on screen

3. **During Playback**
   - Songs play automatically one after another
   - Current song name updates with each track
   - After 20 songs, app rechecks your emotion

4. **View Emotion Report**
   - Click "Stop WebCam / See report"
   - See color-coded grid of your emotions over time

5. **Get New Playlist**
   - Click "Get more music"
   - Process restarts with fresh emotion detection

---

## Understanding Your Playlist

### Emotion Detection

The app detects 7 emotions:

| Emotion | What You'll Hear |
|---------|------------------|
| 😊 **Happy** | Upbeat, energetic songs |
| 😢 **Sad** | Mellow, contemplative tracks |
| 😠 **Angry** | Intense, powerful music |
| 😨 **Fear** | Calming or intense songs |
| 😲 **Surprise** | Mixed tempo variety |
| 🤢 **Disgust** | Neutral to moderate songs |
| 😐 **Neutral** | Balanced mix |

### Playlist Length

- **19-21 songs** per playlist
- **60-90 minutes** of music
- **Automatic progression** through emotional clusters

---

## Common First-Time Issues

### Webcam Not Working

**Problem**: No video preview appears

**Quick Fix**:
1. Check browser permissions (click lock icon in address bar)
2. Ensure no other app is using webcam
3. Try refreshing the page
4. Use Chrome or Firefox for best compatibility

---

### No Playlist Generated

**Problem**: Page reloads but no music plays

**Quick Fix**:
1. Check console for errors (F12 → Console tab)
2. Verify API key is correct in `algorithmia.py`
3. Ensure internet connection is active
4. Check Algorithmia account has API credits

---

### Music Won't Play

**Problem**: Playlist loads but audio doesn't start

**Quick Fix**:
1. Check browser audio isn't muted
2. Verify MP3 files exist in `static/music/` folder
3. Try clicking play button manually
4. Check browser console for errors

---

### "API Key Invalid" Error

**Problem**: Error message about authorization

**Quick Fix**:
1. Double-check API key in `algorithmia.py` line 17
2. Ensure no extra spaces or quotes
3. Verify Algorithmia account is active
4. Generate new API key if needed

---

## Tips for Best Experience

### 🎭 For Accurate Emotion Detection

- **Good lighting**: Face the light source
- **Center your face**: Look directly at camera
- **Clear expression**: Show your emotion clearly
- **Stay still**: Avoid moving during snapshot (5 sec delay)
- **Remove obstructions**: No hands covering face

### 🎵 For Better Music Experience

- **Use headphones**: Better audio quality
- **Let it play**: Give the playlist time to work its magic
- **Try different emotions**: Make different facial expressions
- **Check after 20 songs**: See how your mood changes

### 🔄 For Continuous Use

- **Restart anytime**: Click "Get more music" for fresh playlist
- **View your journey**: Click "Stop WebCam" to see emotion timeline
- **Multiple sessions**: Each session is independent

---

## Example Session

### Scenario: Feeling Stressed

1. **Start app** → Open http://localhost:5000
2. **Show stressed face** → Frown, tense expression
3. **Wait 5 seconds** → App captures your emotion
4. **Detected: Angry/Fear** → App generates calming playlist
5. **Listen** → Starts with intense songs, gradually calms
6. **After 20 songs** → App rechecks (you're now calmer)
7. **New playlist** → More relaxed, moderate energy songs
8. **Result** → Mood improved through music therapy

---

## Keyboard Shortcuts

Currently, Muze doesn't have keyboard shortcuts, but you can use browser defaults:

- **Space**: Play/Pause (when audio player focused)
- **F11**: Fullscreen mode
- **F12**: Open developer console (for debugging)
- **Ctrl+R**: Refresh page (restart session)

---

## What's Next?

### Explore More

- **[Architecture](Architecture.md)**: Understand how it works
- **[Emotion Detection](Emotion-Detection.md)**: Learn about the AI
- **[Music Classification](Music-Classification.md)**: See how songs are chosen
- **[API Reference](API-Reference.md)**: Technical details

### Customize

- **Add your own music**: Replace MP3 files in `static/music/`
- **Modify clusters**: Edit emotion-to-cluster mappings in `algorithmia.py`
- **Change UI**: Edit templates in `templates/` folder
- **Adjust timing**: Modify snapshot intervals in `musi.html`

### Troubleshoot

- **[Troubleshooting Guide](Troubleshooting.md)**: Detailed solutions
- **Check logs**: Look at terminal output for errors
- **Browser console**: F12 → Console for JavaScript errors

---

## Quick Reference Commands

```bash
# Start server
python app.py

# Stop server
Ctrl+C

# Check if running
curl http://localhost:5000

# View logs
# (Terminal shows real-time logs)

# Restart server
Ctrl+C
python app.py
```

---

## Getting Help

### Check These First

1. **Terminal output**: Look for Python errors
2. **Browser console**: F12 → Console tab
3. **Network tab**: F12 → Network (check API calls)
4. **Algorithmia dashboard**: Check API usage/credits

### Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| "Address already in use" | Port 5000 busy | Kill process or use different port |
| "Module not found" | Missing dependency | Run `pip install <module>` |
| "Authorization required" | Invalid API key | Check `algorithmia.py` line 17 |
| "getUserMedia not supported" | Browser issue | Use Chrome/Firefox |
| "No face detected" | Can't see face | Improve lighting, center face |

---

## Pro Tips

### 🎯 Maximize Accuracy

- Take snapshot in good lighting
- Make exaggerated facial expressions
- Look directly at camera
- Remove glasses if possible (optional)

### 🎼 Discover New Music

- Try different emotions intentionally
- Let full playlist play through
- Note songs you like (write down names)
- Explore different moods throughout day

### ⚡ Performance

- Close other apps using webcam
- Use wired internet for API calls
- Clear browser cache if slow
- Restart server if memory issues

### 🔒 Privacy

- App only captures snapshots (not continuous video)
- Images sent to Algorithmia API only
- Snapshots overwritten each time
- No long-term storage of your images

---

## Quick Troubleshooting Checklist

Before asking for help, verify:

- [ ] Python dependencies installed
- [ ] API key configured correctly
- [ ] Webcam working in other apps
- [ ] Internet connection active
- [ ] Port 5000 not in use
- [ ] Music files present in `static/music/`
- [ ] `test.txt` file exists
- [ ] `snapshots/` directory exists
- [ ] Browser supports WebRTC
- [ ] Algorithmia account has credits

---

## Ready to Go!

You're all set! Open **http://localhost:5000** and start your personalized music therapy session.

**Enjoy the music! 🎵**
