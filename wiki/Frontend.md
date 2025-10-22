# Frontend Components

## Overview

The Muze frontend is built with HTML5, JavaScript, and jQuery, providing webcam capture, audio playback, and user interface functionality. This document details all frontend components and their interactions.

## File Structure

```
templates/
├── base.html          # Base template with common structure
├── musi.html          # Main music player interface
├── init.html          # Initial webcam test page
├── index.html         # Simple landing page
├── trial.html         # Development/testing page
├── showgraph.html     # Emotion graph display
└── styling.css        # CSS styles

static/
├── jquery-1.7.1.min.js   # jQuery library
├── music/                # MP3 files (001.mp3 - 903.mp3)
└── graph.jpg             # Generated emotion visualization
```

## Templates

### base.html

**Purpose**: Base template providing common HTML structure

**Structure**:
```html
<!DOCTYPE html>
<html>
    <head>
        <title>Muze</title>
        <link rel="stylesheet" href="/static/style.css" />
        <script src="/static/jquery-1.7.1.min.js"></script>
    </head>
    <body>
        <div id="content">
            {% block body %}{% endblock %}
        </div>
    </body>
</html>
```

**Features**:
- Jinja2 template inheritance
- jQuery 1.7.1 inclusion
- CSS stylesheet link
- Content block for child templates

---

### musi.html

**Purpose**: Main application interface with webcam, audio player, and controls

**Template Variables**:
```python
songs: List[str]  # Playlist from backend
```

**Key Sections**:

#### 1. Script Variables
```html
<script>
var songlist = {{ songs|tojson }};
var i = 0;
</script>
```

#### 2. UI Elements
```html
<article>
    <img id="im">                    <!-- Placeholder image -->
    <div class="cont">
        <h2 id="ss"></h2>            <!-- Song name display -->
    </div>
    <audio id="aud" controls autoplay>
        <source src="/static/music/init.mp3">
    </audio>
    <button onclick="stopWebcam();">Stop WebCam / See report</button>
    <button onclick="play_again();">Get more music</button>
    <canvas hidden id="myCanvas" width="400" height="350"></canvas>
</article>

<video id="video" width="200" height="200" controls autoplay></video>
```

#### 3. WebRTC Setup
```javascript
navigator.getUserMedia = (
    navigator.getUserMedia ||
    navigator.webkitGetUserMedia ||
    navigator.mozGetUserMedia ||
    navigator.msGetUserMedia ||
    navigator.mediaDevices.getUserMedia
);

navigator.getUserMedia(
    { video: true, audio: false },
    function(stream) {
        video.src = window.URL.createObjectURL(stream);
        webcamStream = stream;
    },
    function(err) {
        console.log("Error: " + err);
    }
);
```

**Browser Compatibility**: Supports Chrome, Firefox, Safari, Edge

---

## JavaScript Functions

### Webcam Management

#### `init()`
**Purpose**: Initialize canvas context on page load

```javascript
function init() {
    canvas = document.getElementById("myCanvas");
    ctx = canvas.getContext('2d');
}
```

**Called**: `<body onload="init();">`

---

#### `snapshot()`
**Purpose**: Capture webcam frame and send to server

```javascript
function snapshot() {
    // Draw video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Convert to base64 PNG
    var dataURL = canvas.toDataURL("image/png");
    
    // Send to server
    $.ajax({
        type: "POST",
        url: "/hook",
        data: { imageBase64: dataURL },
        success: function(response) {
            document.write(response);
        }
    }).done(function() {
        console.log('sent');
    });
}
```

**Triggered**:
- After 5 seconds on initial load (empty playlist)
- After 20 songs during playback

**Data Flow**:
1. Video frame → Canvas (400×350)
2. Canvas → Base64 PNG string
3. AJAX POST → `/hook` endpoint
4. Response → Replace page content

---

#### `stopWebcam()`
**Purpose**: Stop webcam stream and navigate to emotion report

```javascript
function stopWebcam() {
    webcamStream.stop();
    window.location.href = "/graph";
}
```

**Triggered**: User clicks "Stop WebCam / See report" button

**Effect**: 
- Releases webcam access
- Redirects to graph visualization page

---

### Playlist Management

#### `play_again()`
**Purpose**: Restart the experience with new emotion detection

```javascript
function play_again() {
    window.location.href = "/";
}
```

**Triggered**: User clicks "Get more music" button

**Effect**: Reloads main page, starts fresh session

---

### Audio Playback

#### Audio 'ended' Event Handler
**Purpose**: Automatically play next song in playlist

```javascript
$('#aud').on('ended', function() {
    // Parse song entry
    var str = (songlist[i].split("_"))[0];   // "234.mp3"
    var name = (songlist[i].split("_"))[1];  // "Song Name - Artist"
    
    // Update display
    document.getElementById('ss').innerHTML = name;
    
    // Increment counter
    i = i + 1;
    
    // Check if time for new snapshot
    if (i == 20) {
        setTimeout(snapshot, 5000);
    }
    
    // Load next song
    $('#aud').attr('src', '/static/music/' + str);
    $('#aud').load();
});
```

**Flow**:
1. Current song ends
2. Parse next song from playlist
3. Update UI with song name
4. Increment playlist index
5. After 20 songs, trigger snapshot
6. Load and play next song

---

#### Initial Snapshot Trigger
```javascript
if (songlist.length == 0) {
    setTimeout(snapshot, 5000);
}
```

**Logic**: If playlist is empty (first load), wait 5 seconds then capture snapshot

---

## UI Components

### Song Display

**Element**: `<h2 id="ss"></h2>`

**Purpose**: Show currently playing song name

**Update**:
```javascript
document.getElementById('ss').innerHTML = "Night in Tunisia - Blakey";
```

**Styling**: White text color (`color: #ffffff`)

---

### Audio Player

**Element**: `<audio id="aud" controls autoplay>`

**Attributes**:
- `controls`: Show playback controls
- `autoplay`: Start playing automatically
- `id="aud"`: JavaScript reference

**Initial Source**: `/static/music/init.mp3`

**Dynamic Source**: Updated via jQuery
```javascript
$('#aud').attr('src', '/static/music/234.mp3');
$('#aud').load();
```

---

### Video Preview

**Element**: `<video id="video" width="200" height="200">`

**Position**: Bottom-right corner (`position:absolute;bottom:0;right:0;`)

**Purpose**: Show live webcam feed to user

**Source**: WebRTC stream
```javascript
video.src = window.URL.createObjectURL(webcamStream);
```

---

### Hidden Canvas

**Element**: `<canvas hidden id="myCanvas" width="400" height="350">`

**Purpose**: Offscreen buffer for capturing video frames

**Visibility**: Hidden from user

**Usage**: Draw video frame, convert to image

---

### Control Buttons

#### Stop WebCam Button
```html
<button onclick="stopWebcam();">Stop WebCam / See report</button>
```

**Action**: Stop camera, view emotion history

---

#### Get More Music Button
```html
<button onclick="play_again();">Get more music</button>
```

**Action**: Restart with new emotion detection

---

## Data Flow Visualization

```
┌──────────────┐
│ Page Load    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ init()       │
│ - Setup      │
│   canvas     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ getUserMedia │
│ - Request    │
│   webcam     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Video Stream │
│ - Display in │
│   <video>    │
└──────┬───────┘
       │
       │ (5 sec delay)
       ▼
┌──────────────┐
│ snapshot()   │
│ - Capture    │
│ - Upload     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Server       │
│ Processing   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Page Reload  │
│ with         │
│ Playlist     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Audio Play   │
│ - Song 1     │
└──────┬───────┘
       │
       │ (on 'ended')
       ▼
┌──────────────┐
│ Next Song    │
│ - Update UI  │
│ - Load audio │
└──────┬───────┘
       │
       │ (repeat)
       ▼
┌──────────────┐
│ After 20     │
│ Songs        │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ snapshot()   │
│ again        │
└──────────────┘
```

## Browser Compatibility

### WebRTC Support

| Browser | getUserMedia | Notes |
|---------|--------------|-------|
| Chrome 53+ | ✅ | Full support |
| Firefox 36+ | ✅ | Full support |
| Safari 11+ | ✅ | Requires HTTPS |
| Edge 12+ | ✅ | Full support |
| IE 11 | ❌ | Not supported |

### HTML5 Audio

| Browser | MP3 Support | Notes |
|---------|-------------|-------|
| Chrome | ✅ | Native |
| Firefox | ✅ | Native |
| Safari | ✅ | Native |
| Edge | ✅ | Native |
| IE 9+ | ✅ | Native |

### Canvas API

**Support**: All modern browsers (IE 9+)

---

## Security Considerations

### Webcam Access

**Permission Required**: User must grant camera access

**HTTPS Requirement**: Modern browsers require HTTPS for getUserMedia (except localhost)

**Indicator**: Browser shows camera active indicator

---

### CORS

**Current Setup**: No CORS headers configured

**Issue**: May block cross-origin requests

**Fix**:
```python
from flask_cors import CORS
CORS(app)
```

---

### Content Security Policy

**Current**: No CSP headers

**Recommendation**:
```python
@app.after_request
def set_csp(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "media-src 'self' blob:; "
        "script-src 'self' 'unsafe-inline';"
    )
    return response
```

---

## Performance Optimization

### Current Issues

1. **Page Reload**: Full page reload on playlist generation
2. **Blocking AJAX**: Synchronous page replacement
3. **No Caching**: Static assets not cached
4. **Large Images**: Base64 encoding increases size by ~33%

### Improvements

#### 1. AJAX Without Reload
```javascript
$.ajax({
    url: "/hook",
    data: { imageBase64: dataURL },
    success: function(data) {
        songlist = JSON.parse(data.songs);
        i = 0;
        playNextSong();
    }
});
```

#### 2. Image Compression
```javascript
var dataURL = canvas.toDataURL("image/jpeg", 0.8);
```

#### 3. Progressive Enhancement
```javascript
// Check for getUserMedia support
if (!navigator.getUserMedia) {
    alert("Webcam not supported. Using random playlist.");
    loadRandomPlaylist();
}
```

#### 4. Lazy Loading
```javascript
// Preload next song
var nextAudio = new Audio('/static/music/' + nextSong);
nextAudio.load();
```

---

## Accessibility

### Current Issues

- No keyboard navigation
- No screen reader support
- No captions for audio
- No alternative to webcam

### Improvements

```html
<!-- Add ARIA labels -->
<button aria-label="Stop webcam and view emotion report">
    Stop WebCam / See report
</button>

<!-- Add keyboard shortcuts -->
<script>
document.addEventListener('keydown', function(e) {
    if (e.key === ' ') {
        $('#aud')[0].paused ? $('#aud')[0].play() : $('#aud')[0].pause();
    }
});
</script>

<!-- Add skip option -->
<button onclick="skipSong();">Skip Song</button>
```

---

## Error Handling

### Current Approach

**Minimal error handling**:
- Console logging only
- No user feedback
- No retry logic

### Recommended Improvements

```javascript
// Webcam error handling
function(err) {
    alert("Camera access denied. Please enable camera permissions.");
    console.log("Error: " + err);
}

// Audio error handling
$('#aud').on('error', function() {
    console.log("Audio load failed, skipping...");
    i++;
    playNextSong();
});

// AJAX error handling
$.ajax({
    // ...
    error: function(xhr, status, error) {
        alert("Failed to generate playlist. Please try again.");
        console.error(error);
    }
});
```

---

## Testing

### Manual Testing Checklist

- [ ] Webcam permission prompt appears
- [ ] Video preview shows in corner
- [ ] Initial snapshot taken after 5 seconds
- [ ] Playlist loads and plays automatically
- [ ] Song name displays correctly
- [ ] Audio controls work (play/pause/volume)
- [ ] Next song loads on 'ended' event
- [ ] Snapshot taken after 20 songs
- [ ] "Stop WebCam" button works
- [ ] "Get more music" button works
- [ ] Graph displays emotion history

### Browser Testing

Test in:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

### Device Testing

- Desktop (Windows/Mac/Linux)
- Mobile (iOS/Android) - Note: Limited support
- Tablet

---

## Future Enhancements

### UI Improvements
- Modern CSS framework (Tailwind, Bootstrap)
- Responsive design
- Dark/light theme toggle
- Visualizer for audio playback
- Progress bar for playlist

### Features
- Skip song button
- Favorite/like songs
- Volume control
- Playlist shuffle
- Repeat mode
- Download playlist

### UX Enhancements
- Loading indicators
- Smooth transitions
- Toast notifications
- Onboarding tutorial
- Help tooltips
