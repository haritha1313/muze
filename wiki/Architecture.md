# System Architecture

## High-Level Architecture

Muze follows a client-server architecture with external AI services:

```
┌─────────────────┐
│   Web Browser   │
│  (Client-Side)  │
│                 │
│  - Webcam       │
│  - Audio Player │
│  - UI Controls  │
└────────┬────────┘
         │ HTTP/AJAX
         ▼
┌─────────────────┐
│  Flask Server   │
│  (Backend)      │
│                 │
│  - Routes       │
│  - Image Proc   │
│  - Playlist Gen │
└────────┬────────┘
         │ API Call
         ▼
┌─────────────────┐
│  Algorithmia    │
│   (External)    │
│                 │
│  - Emotion AI   │
│  - CNN Model    │
└─────────────────┘
```

## Component Breakdown

### 1. Frontend Layer (Client)

**Location**: `templates/musi.html`, `static/`

**Responsibilities**:
- Webcam capture via WebRTC
- Audio playback control
- User interface rendering
- Snapshot capture and transmission
- Playlist management

**Key Technologies**:
- HTML5 Canvas for image capture
- getUserMedia API for webcam access
- jQuery for AJAX requests
- HTML5 Audio element for playback

### 2. Backend Layer (Server)

**Location**: `app.py`, `algorithmia.py`

**Responsibilities**:
- HTTP request handling
- Image processing and storage
- Emotion detection coordination
- Playlist generation logic
- File serving

**Key Technologies**:
- Flask web framework
- Pillow for image manipulation
- Base64 encoding/decoding
- Pickle for data serialization

### 3. AI/ML Layer (External)

**Service**: Algorithmia API

**Responsibilities**:
- Facial emotion recognition
- Deep learning inference
- Confidence scoring

**Model**: EmotionRecognitionCNNMBP v1.0.1

### 4. Data Layer

**Location**: `test.txt`, `static/music/`

**Responsibilities**:
- Song metadata storage
- Audio file hosting
- Emotion-to-cluster mapping

**Format**: Pickled Python list (903 songs)

## Request Flow

### Initial Load

```
1. User visits http://localhost:5000/
2. Flask serves musi.html template (empty playlist)
3. Browser requests webcam access
4. After 5 seconds, snapshot() is called
5. Canvas captures webcam frame
6. Image sent to /hook endpoint via AJAX
7. Backend saves image to snapshots/pic.png
8. get_emotion() calls Algorithmia API
9. get_playlist() generates song list
10. Template re-renders with playlist
11. Audio player starts playing songs
```

### Continuous Playback

```
1. Audio element plays current song
2. On 'ended' event, load next song
3. After 20 songs, take new snapshot
4. Repeat emotion detection cycle
5. Generate new playlist
6. Continue playback
```

### Emotion Report

```
1. User clicks "Stop WebCam / See report"
2. Webcam stream stops
3. Redirect to /graph endpoint
4. get_emotion_grid() generates visualization
5. Matplotlib creates color-coded grid
6. Image saved to static/graph.jpg
7. Template displays emotion history
```

## Data Structures

### Song List Format
```python
# test.txt (pickled list)
[
    "(Mama) He Treats Your Daughter Mean - Brown",
    "Night in Tunisia - Blakey",
    "Along Came Jones - Coasters",
    ...
]
```

### Playlist Entry Format
```python
# Format: "XXX.mp3_Song Name - Artist"
"001.mp3_(Mama) He Treats Your Daughter Mean - Brown"
```

### Emotion Mapping
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

### Cluster Definitions
```python
# Cluster ID: [start_index, end_index]
songlist = {
    1: [1, 170],      # Cluster 1: Songs 1-170
    2: [171, 334],    # Cluster 2: Songs 171-334
    3: [335, 549],    # Cluster 3: Songs 335-549
    4: [550, 740],    # Cluster 4: Songs 550-740
    5: [741, 903]     # Cluster 5: Songs 741-903
}
```

## Security Considerations

### Current Implementation
- **API Key**: Hardcoded in `algorithmia.py` (line 17)
- **Session Secret**: Hardcoded as "bacon" in `app.py`
- **File Upload**: No validation on uploaded images
- **CORS**: Not configured

### Recommendations
- Move API key to environment variables
- Use secure session secret generation
- Implement file type/size validation
- Add rate limiting for API calls
- Configure CORS headers properly

## Scalability Considerations

### Current Limitations
- Single-threaded Flask development server
- Synchronous API calls block requests
- No caching mechanism
- Local file storage only

### Potential Improvements
- Deploy with production WSGI server (Gunicorn/uWSGI)
- Implement async API calls
- Add Redis caching for emotion results
- Use cloud storage for snapshots
- Implement CDN for static music files

## Performance Characteristics

- **Emotion Detection**: ~2-5 seconds (API latency)
- **Playlist Generation**: <100ms (local computation)
- **Snapshot Capture**: ~500ms (client-side)
- **Page Load**: ~1-2 seconds (initial render)

## Error Handling

### Current Approach
- Empty emotion result defaults to "Neutral"
- No retry logic for failed API calls
- Console logging for debugging
- No user-facing error messages

### Areas for Improvement
- Implement exponential backoff for API retries
- Add user-friendly error notifications
- Graceful degradation when API unavailable
- Fallback to random playlist on errors
