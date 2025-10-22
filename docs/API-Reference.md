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


## API Reference











### get_emotion_count

*Source: `algorithmia.py`*

{
  "updated_doc": "## get_emotion_count()

Returns the total number of emotions currently available in the emotion list.

### Returns
- `int`: The count of emotions in `emot_list`

### Description
This utility function provides a way to check how many distinct emotions are defined in the system by returning the length of the global `emot_list` variable.

### Example
```python
count = get_emotion_count()
print(f'Number of available emotions: {count}')
```

### Notes
- This function is read-only and does not modify the emotion list
- Returns 0 if the emotion list is empty
- Depends on the global `emot_list` variable being properly initialized",
  "explanation": "This is a simple utility function that returns the length of a global emotion list. The function appears to be used for getting a count of available emotions in the system. While the implementation is straightforward, documenting the return type, dependencies, and usage is important for API consumers.",
  "confidence": 0.90
}

### clear_emotion_history

*Source: `algorithmia.py`*

{
  "updated_doc": "## clear_emotion_history

Clears the global emotion history list by resetting it to an empty list.

### Returns
- `int`: The length of the cleared emotion list (always returns 0)

### Details
- Modifies the global `emot_list` variable
- Resets the list to empty (`[]`)
- Returns the new length immediately after clearing

### Example Usage
```python
current_size = clear_emotion_history()  # Returns 0
```

### Notes
- This is a stateful operation that affects global application state
- Previous emotion history cannot be recovered after clearing
- Safe to call multiple times",
  "explanation": "This is a simple utility function that resets a global emotion tracking list. The function is straightforward - it clears a global list and returns its new length. The documentation focuses on the state-changing nature of the function and its return value. While the implementation is basic, it's important to note the global state modification for developers.",
  "confidence": 0.95
}

### _select_song_from_cluster

*Source: `algorithmia.py`*

## _select_song_from_cluster

Selects and returns a random song from a specified music cluster.

### Parameters

- `cluster_id` (int): The identifier for the music cluster to select from. Must correspond to a valid cluster ID in `SONG_CLUSTERS`.

### Returns

`Tuple[int, str]`: A tuple containing:
- `song_id` (int): The numeric ID of the selected song
- `formatted_name` (str): The formatted song filename in the format `"XXX.mp3_SongName"` where XXX is the zero-padded song ID

### Description

This internal method:
1. Loads the song database
2. Gets the valid song ID range for the specified cluster
3. Randomly selects a song ID within that range
4. Formats the song name according to the required pattern

### Example

```python
song_id, formatted_name = _select_song_from_cluster(1)
# Might return: (45, "045.mp3_Song Title")
```

### Notes

- Requires `SONG_CLUSTERS` to be properly initialized with valid ranges
- Depends on `_load_song_database()` to provide song name mapping
- Internal method (denoted by leading underscore)

### _call_emotion_api

*Source: `algorithmia.py`*

## _call_emotion_api

Makes a call to the Algorithmia Emotion Recognition API to analyze emotions in an image.

### Parameters

- `image_path` (str, optional)
  - Path to the image file to analyze
  - Default value: "snapshots/pic.png"

### Returns

- `Dict`
  - Response dictionary from the emotion recognition API containing analysis results

### Raises

- `FileNotFoundError`
  - If the specified image file cannot be found at the given path
- `RuntimeError`
  - If the API call fails for any reason (network error, invalid response, etc.)

### Example Usage

```python
try:
    result = _call_emotion_api("path/to/image.jpg")
    print(result)  # Prints emotion analysis results
except RuntimeError as e:
    print(f"API call failed: {e}")
```

### Notes

- Requires a valid Algorithmia API key to be configured
- Uses the deeplearning/EmotionRecognitionCNNMBP/1.0.1 algorithm
- Image file is read as binary data before being sent to the API
- All errors are logged before being re-raised

### _get_emotion_color_mapping

*Source: `algorithmia.py`*

{
  "updated_doc": "## _get_emotion_color_mapping

Returns a dictionary mapping emotion labels to their corresponding numerical color codes.

### Returns
`Dict[str, int]`: A dictionary where:
- Keys are emotion labels (`str`): 'Neutral', 'Sad', 'Disgust', 'Fear', 'Surprise', 'Happy', 'Angry'
- Values are integer color codes (`int`): ranging from 1 to 61

### Details
The function provides a static mapping between seven basic emotions and their assigned color codes:
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

### Notes
- This is an internal helper function (denoted by the leading underscore)
- The mapping is fixed and does not accept any parameters
- Color codes are non-sequential integers
",
  "explanation": "This is a simple utility function that provides a static mapping between emotion labels and color codes. The function is internal (private) as indicated by the underscore prefix. It's a new addition to the codebase with no previous version to compare against. The documentation focuses on the return value structure and the specific mappings since that's the core functionality.",
  "confidence": 0.95
}

### generate_playlist

*Source: `algorithmia.py`*

## generate_playlist(emotion: str, shuffle: bool = True) -> List[str]

Generates a personalized playlist of songs based on a given emotional state.

### Parameters

- `emotion` (str): The emotional state to generate music for. If the emotion is not recognized, defaults to "Neutral"
- `shuffle` (bool, optional): Whether to randomize the order of songs in the playlist. Defaults to True

### Returns

- List[str]: A list of song filenames that match the requested emotional state

### Description

This function creates a playlist by:
1. Looking up the cluster configuration associated with the input emotion
2. Selecting the specified number of songs from each configured music cluster
3. Optionally shuffling the final playlist

### Example Usage

```python
playlist = music_system.generate_playlist("Happy", shuffle=True)
# Returns: ['song1.mp3', 'song2.mp3', ...]
```

### Notes

- If an unrecognized emotion is provided, the function will fall back to "Neutral" and log a warning
- The number and type of songs selected is determined by the EMOTION_CLUSTER_MAPPING configuration
- Songs are selected from predefined clusters that correspond to different mood categories

### Logging

The function logs:
- INFO level when starting playlist generation and completing it
- WARNING level if an unknown emotion is provided
- DEBUG level when adding songs from specific clusters

### get_emotion_detailed

*Source: `algorithmia.py`*

{
  "updated_doc": "## get_emotion_detailed

Analyzes an image file to detect emotions and returns detailed emotion detection results including confidence scores for all detected emotions.

### Parameters

| Parameter    | Type   | Description                                    | Default            |
|-------------|--------|------------------------------------------------|--------------------|
| image_path  | str    | File path to the image to be analyzed          | 'snapshots/pic.png'|

### Returns

`EmotionResult`
- A custom type containing the complete emotion detection analysis data

### Description

This function performs two main operations:
1. Calls the emotion detection API with the provided image
2. Parses and structures the API response into an EmotionResult object

The function handles both the API communication and result parsing internally, providing a clean interface for emotion detection.

### Example Usage

```python
result = get_emotion_detailed('path/to/image.jpg')
# Returns EmotionResult object with detailed emotion data
```

### Notes

- The function expects the image file to exist at the specified path
- Uses an internal `_call_emotion_api` function to make the actual API request
- Results are parsed through an internal `_parse_emotion_results` function",
  "explanation": "This is a new function that provides a high-level interface for emotion detection in images. It abstracts away the complexity of API calls and response parsing, providing a simple way to get detailed emotion analysis results. The function is well-structured with clear input/output types and follows good programming practices by separating concerns (API calling vs result parsing).",
  "confidence": 0.85
}

### __init__

*Source: `algorithmia.py`*

## __init__

Initializes a new playlist generator instance.

### Parameters

- `song_database_path` (str, optional): Path to the pickled song database file
  - Default value: "test.txt"

### Attributes

- `song_database_path`: Stores the provided database file path
- `_song_names`: Internal cache for song names (initialized as None)

### Example

```python
# Initialize with default database path
playlist_gen = PlaylistGenerator()

# Initialize with custom database path
playlist_gen = PlaylistGenerator(song_database_path='songs.pkl')
```

### Notes

- The song database file should exist and be in a valid pickled format
- The `_song_names` attribute is used internally for caching and is initialized as None

### _parse_emotion_results

*Source: `algorithmia.py`*

## _parse_emotion_results

Parses raw emotion detection API response data into a structured EmotionResult object.

### Parameters
- `api_response` (Dict): Raw API response containing emotion detection results

### Returns
- `EmotionResult`: Object containing:
  - `emotion` (EmotionType): Dominant emotion enum value
  - `confidence` (float): Confidence score (0.0-1.0) for dominant emotion
  - `all_emotions` (Dict[str, float]): All detected emotions and their confidence scores
  - `color_code` (int): Color code associated with dominant emotion

### Behavior
1. If no results are found, defaults to Neutral emotion with 100% confidence
2. Extracts emotion confidence scores from API response
3. Determines dominant emotion based on highest confidence score
4. Maps emotion to corresponding color code
5. Maintains emotion history in global `emot_list`
6. Logs detection results

### Example Response Structure
```python
EmotionResult(
    emotion=EmotionType.HAPPY,
    confidence=0.85,
    all_emotions={'Happy': 0.85, 'Neutral': 0.12, 'Sad': 0.03},
    color_code=5
)
```

### Notes
- Automatically falls back to Neutral emotion if parsing fails or invalid emotion detected
- Logs emotion detection results at INFO level
- Maintains detection history in global `emot_list`

### _load_song_database

*Source: `algorithmia.py`*

## _load_song_database

**Private method that loads and caches song metadata from a pickle database file.**

### Returns
`Dict[int, str]` - Dictionary mapping song IDs (integers) to song names (strings)

### Raises
- `FileNotFoundError`: If the song database file specified in `self.song_database_path` cannot be found

### Details
- Loads song data from a pickle file using Latin-1 encoding
- Caches results in `self._song_names` to avoid repeated disk reads
- Thread-safe: Returns cached data if already loaded

### Example
```python
song_db = music_handler._load_song_database()
# Returns: {1: 'Song Name 1', 2: 'Song Name 2', ...}
```

### Notes
- This is an internal method (denoted by leading underscore)
- The database file should be a pickled dictionary with integer keys and string values
- Successful loads are logged at INFO level
- Failed loads are logged at ERROR level before raising exception

