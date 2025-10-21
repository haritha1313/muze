# Data Flow

## Complete User Journey

This document traces how data flows through the Muze application from initial page load to playlist generation.

## Flow Diagram

```
┌─────────────┐
│ User visits │
│     /       │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ Flask: index()          │
│ Returns musi.html       │
│ songs = []              │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ Browser renders page    │
│ - Requests webcam       │
│ - Initializes canvas    │
│ - Starts video stream   │
└──────┬──────────────────┘
       │
       │ (5 second delay)
       ▼
┌─────────────────────────┐
│ snapshot() triggered    │
│ - Capture video frame   │
│ - Convert to base64     │
└──────┬──────────────────┘
       │
       │ AJAX POST
       ▼
┌─────────────────────────┐
│ Flask: /hook            │
│ - Decode image          │
│ - Save to disk          │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ get_emotion()           │
│ - Read image file       │
│ - Call Algorithmia API  │
└──────┬──────────────────┘
       │
       │ API Response
       ▼
┌─────────────────────────┐
│ Emotion Analysis        │
│ - Parse confidence      │
│ - Select max emotion    │
│ - Store color code      │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ get_playlist()          │
│ - Load song database    │
│ - Map emotion→clusters  │
│ - Random selection      │
└──────┬──────────────────┘
       │
       │ Playlist array
       ▼
┌─────────────────────────┐
│ Flask: render template  │
│ songs = [21 items]      │
└──────┬──────────────────┘
       │
       │ HTML Response
       ▼
┌─────────────────────────┐
│ Browser: Page reload    │
│ - Parse song list       │
│ - Start audio playback  │
└──────┬──────────────────┘
       │
       │ (Every song end)
       ▼
┌─────────────────────────┐
│ Audio 'ended' event     │
│ - Load next song        │
│ - Update display        │
└──────┬──────────────────┘
       │
       │ (After 20 songs)
       ▼
┌─────────────────────────┐
│ snapshot() again        │
│ (Cycle repeats)         │
└─────────────────────────┘
```

## Detailed Step-by-Step Flow

### Phase 1: Initialization

#### Step 1: Page Load
```
User → Browser → Flask Server
GET http://localhost:5000/
```

**Server Action**:
```python
@app.route('/')
def index():
    return flask.render_template("musi.html", songs=[])
```

**Data Sent**:
- HTML template
- Empty songs array: `[]`
- Static resources (CSS, JS, jQuery)

---

#### Step 2: Webcam Initialization
```
Browser → User's Webcam
navigator.getUserMedia()
```

**Client Action**:
```javascript
navigator.getUserMedia(
    { video: true, audio: false },
    function(stream) {
        video.src = window.URL.createObjectURL(stream);
        webcamStream = stream;
    },
    function(err) { console.log(err); }
);
```

**Data Flow**:
- Browser requests camera permission
- User grants access
- Video stream → `<video>` element
- Stream stored in `webcamStream` variable

---

### Phase 2: Emotion Detection

#### Step 3: Snapshot Capture (After 5 seconds)
```
Video Stream → Canvas → Base64 String
```

**Client Action**:
```javascript
function snapshot() {
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    var dataURL = canvas.toDataURL("image/png");
    // dataURL format: "data:image/png;base64,iVBORw0KG..."
}
```

**Data Transformation**:
1. Video frame (raw pixels) → Canvas (400×350)
2. Canvas → PNG image
3. PNG → Base64 string
4. String prefixed with `data:image/png;base64,`

---

#### Step 4: Image Upload
```
Browser → Flask Server
POST /hook
```

**Client Action**:
```javascript
$.ajax({
    type: "POST",
    url: "/hook",
    data: { imageBase64: dataURL }
});
```

**Data Sent**:
- `imageBase64`: Full base64 string (~50-100KB)

**Server Action**:
```python
@app.route('/hook', methods=['POST'])
def get_image():
    image_b64 = request.values['imageBase64']
    image_data = re.sub('^data:image/.+;base64,', '', image_b64)
    image_PIL = Image.open(BytesIO(base64.b64decode(image_data)))
    image_PIL.save("snapshots/pic.png", mode='RGB')
```

**Data Transformation**:
1. Base64 string → Remove prefix
2. Base64 → Binary data
3. Binary → PIL Image object
4. PIL Image → PNG file on disk

**File Created**: `snapshots/pic.png` (400×350 RGB)

---

#### Step 5: Emotion Recognition
```
Flask Server → Algorithmia API
```

**Server Action**:
```python
def get_emotion():
    input = bytearray(open("snapshots/pic.png", "rb").read())
    client = Algorithmia.client('api-key')
    algo = client.algo('deeplearning/EmotionRecognitionCNNMBP/1.0.1')
    op = algo.pipe(input).result
```

**Data Sent to API**:
- Binary image data (PNG file as bytearray)
- Size: ~50-150KB

**API Response**:
```json
{
    "results": [
        {
            "emotions": [
                {"label": "Happy", "confidence": 0.85},
                {"label": "Sad", "confidence": 0.05},
                {"label": "Angry", "confidence": 0.02},
                {"label": "Neutral", "confidence": 0.03},
                {"label": "Fear", "confidence": 0.01},
                {"label": "Disgust", "confidence": 0.02},
                {"label": "Surprise", "confidence": 0.02}
            ]
        }
    ]
}
```

**Data Processing**:
```python
emotion = op[0]["emotions"]
analyze = {}
for emo in emotion:
    analyze[emo["label"]] = float(emo["confidence"])
current = max(analyze, key=analyze.get)  # "Happy"
```

**Output**: String emotion name (e.g., "Happy")

---

### Phase 3: Playlist Generation

#### Step 6: Cluster Selection
```
Emotion String → Cluster Distribution
```

**Server Action**:
```python
def get_playlist():
    current = get_emotion()  # "Happy"
    
    # Emotion → Cluster mapping
    if current == "Happy":
        cluster_def = [[2, 10], [4, 5], [1, 6]]
        # Cluster 2: 10 songs
        # Cluster 4: 5 songs
        # Cluster 1: 6 songs
```

**Cluster Ranges**:
```python
songlist = {
    1: [1, 170],      # 170 songs
    2: [171, 334],    # 164 songs
    3: [335, 549],    # 215 songs
    4: [550, 740],    # 191 songs
    5: [741, 903]     # 163 songs
}
```

---

#### Step 7: Song Selection
```
Cluster Distribution → Random Song Indices → Song Names
```

**Server Action**:
```python
with open("test.txt", "rb") as fp:
    songnames = pickle.load(fp, encoding='latin1')

playlist = []
for sets in cluster_def:  # [[2, 10], [4, 5], [1, 6]]
    for i in range(sets[1]):  # Repeat N times
        ss = random.randint(songlist[sets[0]][0], songlist[sets[0]][1])
        playlist.append(f"{ss:03d}.mp3_{songnames[ss]}")
```

**Example Execution** (Happy emotion):
1. Cluster 2, 10 songs: Random from 171-334
   - `"234.mp3_Night in Tunisia - Blakey"`
   - `"189.mp3_Along Came Jones - Coasters"`
   - ... (8 more)
2. Cluster 4, 5 songs: Random from 550-740
   - `"612.mp3_Some Song - Artist"`
   - ... (4 more)
3. Cluster 1, 6 songs: Random from 1-170
   - `"045.mp3_Another Song - Artist"`
   - ... (5 more)

**Output**: List of 21 formatted strings

---

#### Step 8: Response Generation
```
Playlist Array → HTML Template → HTTP Response
```

**Server Action**:
```python
return flask.render_template("musi.html", songs=playlist)
```

**Data Sent**:
```html
<script>
var songlist = [
    "234.mp3_Night in Tunisia - Blakey",
    "189.mp3_Along Came Jones - Coasters",
    ...
];
</script>
```

---

### Phase 4: Playback

#### Step 9: Audio Playback
```
Song List → Audio Element → Speaker
```

**Client Action**:
```javascript
$('#aud').on('ended', function() {
    var str = (songlist[i].split("_"))[0];  // "234.mp3"
    var name = (songlist[i].split("_"))[1]; // "Night in Tunisia - Blakey"
    
    document.getElementById('ss').innerHTML = name;
    i = i + 1;
    
    $('#aud').attr('src', '/static/music/' + str);
    $('#aud').load();
});
```

**Data Flow**:
1. Parse song string → filename + display name
2. Update UI with song name
3. Set audio source: `/static/music/234.mp3`
4. Browser requests MP3 file from server
5. Audio decoded and played

---

#### Step 10: Continuous Monitoring
```
Song Counter → Snapshot Trigger
```

**Client Action**:
```javascript
if (i == 20) {
    setTimeout(snapshot, 5000);
}
```

**Data Flow**:
- After 20th song ends
- Wait 5 seconds
- Capture new snapshot
- Return to Phase 2 (Emotion Detection)

---

### Phase 5: Emotion Report

#### Step 11: Graph Generation
```
Emotion History → Matplotlib → Image File
```

**Triggered by**: User clicks "Stop WebCam / See report"

**Client Action**:
```javascript
function stopWebcam() {
    webcamStream.stop();
    window.location.href = "/graph";
}
```

**Server Action**:
```python
@app.route('/graph')
def get_graph():
    get_emotion_grid()
    songs = get_playlist()
    return flask.render_template("musi.html", songs=songs)
```

**Graph Generation**:
```python
def get_emotion_grid():
    data = np.full((5, 10), 81)  # 5×10 grid, default white
    
    for i in range(5):
        for q in range(10):
            if a < len(emot_list):
                data[i, q] = emot_list[a]  # Color code
                a += 1
    
    plt.savefig("static/graph.jpg")
```

**Data Transformation**:
1. `emot_list` (color codes) → NumPy array
2. NumPy array → Matplotlib figure
3. Figure → JPEG file
4. File saved to `static/graph.jpg`

---

## Data Persistence

### Session Data (In-Memory)
- `emot_list`: Global list of emotion color codes
- `webcamStream`: Active video stream object
- `songlist`: Current playlist (client-side)
- `i`: Current song index (client-side)

### Persistent Data (Disk)
- `snapshots/pic.png`: Latest webcam snapshot (overwritten each time)
- `static/graph.jpg`: Emotion history visualization (overwritten)
- `test.txt`: Song database (read-only)
- `static/music/*.mp3`: Audio files (read-only)

### External Data
- Algorithmia API: Emotion detection results (not stored)

---

## Data Size Estimates

| Data Type | Size | Frequency |
|-----------|------|-----------|
| Webcam snapshot | 50-150 KB | Every 20 songs |
| Base64 image | 70-200 KB | Every 20 songs |
| API request | 50-150 KB | Every 20 songs |
| API response | 1-2 KB | Every 20 songs |
| Playlist data | 2-5 KB | Every 20 songs |
| MP3 file | 3-5 MB | Per song |
| HTML page | 10-20 KB | Per page load |
| Graph image | 50-100 KB | On demand |

---

## Performance Bottlenecks

1. **Algorithmia API Call**: 2-5 seconds (network + processing)
2. **Image Encoding**: 100-500ms (client-side)
3. **MP3 Loading**: 1-3 seconds (depends on file size)
4. **Graph Generation**: 500ms-1s (matplotlib rendering)

## Error Scenarios

### No Face Detected
```
API returns empty results → Default to "Neutral" → Continue
```

### API Timeout
```
Network error → Exception → No playlist generated → User sees error
```

### Webcam Access Denied
```
getUserMedia fails → No video stream → Cannot capture snapshots
```

### Missing Song File
```
Audio element fails to load → 'error' event → Skip to next song
```
