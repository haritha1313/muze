# API Reference

## Flask Routes

### `GET /`

**Description**: Main application entry point. Renders the music player interface with an empty playlist.

**Request**: None

**Response**: HTML page (musi.html template)

**Template Variables**:
- `songs`: Empty list `[]`

**Example**:
```bash
curl http://localhost:5000/
```

---

### `POST /hook`

**Description**: Receives webcam snapshot, performs emotion detection, and generates a personalized playlist.

**Request**:
- **Method**: POST
- **Content-Type**: application/x-www-form-urlencoded
- **Body Parameters**:
  - `imageBase64` (string): Base64-encoded PNG image from webcam

**Response**: HTML page (musi.html template) with generated playlist

**Template Variables**:
- `songs`: List of song strings in format `"XXX.mp3_Song Name - Artist"`

**Process**:
1. Decode base64 image data
2. Save image to `snapshots/pic.png`
3. Call `get_playlist()` to generate songs
4. Render template with playlist

**Example**:
```javascript
$.ajax({
    type: "POST",
    url: "/hook",
    data: {
        imageBase64: "data:image/png;base64,iVBORw0KG..."
    },
    success: function(response) {
        document.write(response);
    }
});
```

---

### `GET /graph`

**Description**: Generates emotion history visualization and returns the music player with current playlist.

**Request**: None

**Response**: HTML page (musi.html template) with playlist

**Side Effects**:
- Creates emotion grid visualization
- Saves graph to `static/graph.jpg`

**Template Variables**:
- `songs`: List of songs from current session

**Example**:
```bash
curl http://localhost:5000/graph
```

---

## Python Functions

### `algorithmia.py`

#### `get_emotion()`

**Description**: Analyzes the saved snapshot image to detect facial emotions using Algorithmia's deep learning API.

**Parameters**: None (reads from `snapshots/pic.png`)

**Returns**: 
- `str`: Detected emotion name ("Happy", "Sad", "Angry", "Fear", "Surprise", "Disgust", or "Neutral")

**Side Effects**:
- Appends emotion color code to global `emot_list`
- Prints emotion list to console

**Algorithm**:
1. Read image from `snapshots/pic.png`
2. Send to Algorithmia EmotionRecognitionCNNMBP API
3. Parse confidence scores for each emotion
4. Return emotion with highest confidence
5. Default to "Neutral" if no face detected

**API Call**:
```python
client = Algorithmia.client('api-key')
algo = client.algo('deeplearning/EmotionRecognitionCNNMBP/1.0.1')
result = algo.pipe(input).result
```

**Emotion Color Mapping**:
```python
{
    'Neutral': 11,
    'Sad': 31,
    'Disgust': 51,
    'Fear': 61,
    'Surprise': 41,
    'Happy': 21,
    'Angry': 1
}
```

**Example**:
```python
from algorithmia import get_emotion

emotion = get_emotion()
print(f"Detected emotion: {emotion}")
# Output: "Detected emotion: Happy"
```

---

#### `get_playlist()`

**Description**: Generates a personalized music playlist based on detected emotion using cluster-based selection.

**Parameters**: None

**Returns**:
- `list`: Playlist of song strings in format `"XXX.mp3_Song Name - Artist"`

**Dependencies**:
- Calls `get_emotion()` internally
- Reads song database from `test.txt`

**Cluster Mapping**:
```python
songlist = {
    1: [1, 170],      # Energetic/Upbeat
    2: [171, 334],    # Moderate Energy
    3: [335, 549],    # Neutral/Mixed
    4: [550, 740],    # Calm/Mellow
    5: [741, 903]     # Intense/Dark
}
```

**Emotion-to-Cluster Logic**:

| Emotion | Cluster Distribution | Total Songs |
|---------|---------------------|-------------|
| Anger, Fear | 5×2, 3×7, 2×12 | 21 songs |
| Sad | 3×4, 4×4, 2×13 | 42 songs |
| Neutral, Disgust, Surprise | 3×2, 4×5, 2×7, 1×5 | 19 songs |
| Happy | 2×10, 4×5, 1×6 | 21 songs |

**Algorithm**:
1. Detect current emotion
2. Select cluster distribution based on emotion
3. For each cluster in distribution:
   - Randomly select N songs from that cluster's range
4. Return complete playlist

**Example**:
```python
from algorithmia import get_playlist

playlist = get_playlist()
print(f"Generated {len(playlist)} songs")
print(f"First song: {playlist[0]}")
# Output: "Generated 21 songs"
# Output: "First song: 741.mp3_Song Name - Artist"
```

---

#### `get_emotion_grid()`

**Description**: Creates a visual grid representation of emotion history throughout the listening session.

**Parameters**: None (uses global `emot_list`)

**Returns**: None

**Side Effects**:
- Generates matplotlib figure
- Saves image to `static/graph.jpg`
- Displays plot window (plt.show())

**Grid Specifications**:
- **Size**: 5 rows × 10 columns (50 cells)
- **Fill Order**: Left-to-right, top-to-bottom
- **Default Color**: White (81) for unused cells

**Color Scheme**:
- Red: Angry
- Blue: Neutral
- Yellow: Happy
- Green: Sad
- Cyan: Surprise
- Magenta: Disgust
- Black: Fear
- White: No data

**Example**:
```python
from algorithmia import get_emotion_grid

# After several emotion detections
get_emotion_grid()
# Creates static/graph.jpg with emotion timeline
```

---

## Data Formats

### Song Database (test.txt)

**Format**: Pickled Python list

**Structure**:
```python
[
    "Song Name - Artist",
    "Song Name - Artist",
    ...
]
```

**Total Entries**: 903 songs (indices 0-902)

**Loading**:
```python
import pickle

with open("test.txt", "rb") as fp:
    songnames = pickle.load(fp, encoding='latin1')
```

---

### Playlist Format

**Structure**: List of strings

**String Format**: `"{index:03d}.mp3_{song_name}"`

**Example**:
```python
[
    "001.mp3_(Mama) He Treats Your Daughter Mean - Brown",
    "234.mp3_Night in Tunisia - Blakey",
    "567.mp3_Along Came Jones - Coasters"
]
```

**Parsing**:
```javascript
var parts = songlist[i].split("_");
var filename = parts[0];  // "001.mp3"
var displayName = parts[1];  // "Song Name - Artist"
```

---

## External APIs

### Algorithmia EmotionRecognitionCNNMBP

**Endpoint**: `deeplearning/EmotionRecognitionCNNMBP/1.0.1`

**Authentication**: API Key (required)

**Input**: Binary image data (PNG/JPEG)

**Output**:
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

**Error Cases**:
- Empty `results` array: No face detected
- API timeout: Network error
- Invalid API key: Authentication failure

---

## Configuration

### Required Environment Variables

Currently hardcoded, but should be moved to environment variables:

```python
# Algorithmia API Key
ALGORITHMIA_API_KEY = "your-api-key-here"

# Flask Secret Key
FLASK_SECRET_KEY = "your-secret-key-here"

# Server Configuration
FLASK_DEBUG = True
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
```

### File Paths

```python
# Snapshot storage
SNAPSHOT_PATH = "snapshots/pic.png"

# Song database
SONG_DATABASE = "test.txt"

# Music files
MUSIC_DIRECTORY = "static/music/"

# Emotion graph output
GRAPH_OUTPUT = "static/graph.jpg"
```
