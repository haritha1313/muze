# Emotion Detection System

## Overview

Muze uses facial emotion recognition powered by Algorithmia's deep learning model to detect user emotions in real-time. This document explains how the emotion detection system works, from image capture to emotion classification.

## Emotion Categories

The system detects **7 distinct emotions**:

| Emotion | Description | Musical Response |
|---------|-------------|------------------|
| **Happy** | Joy, contentment, pleasure | Upbeat, energetic songs |
| **Sad** | Sorrow, melancholy, grief | Mellow, contemplative songs |
| **Angry** | Rage, frustration, irritation | Intense, powerful songs |
| **Fear** | Anxiety, worry, apprehension | Calming or intense songs |
| **Surprise** | Shock, amazement, wonder | Mixed tempo songs |
| **Disgust** | Aversion, distaste, repulsion | Neutral to moderate songs |
| **Neutral** | No strong emotion detected | Balanced mix of songs |

## Detection Pipeline

### 1. Image Acquisition

**Source**: User's webcam via WebRTC

**Specifications**:
- **Resolution**: 400×350 pixels
- **Format**: RGB PNG
- **Capture Method**: HTML5 Canvas `drawImage()`
- **Frequency**: Initial load + every 20 songs

**Code**:
```javascript
// Capture video frame to canvas
ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

// Convert to base64 PNG
var dataURL = canvas.toDataURL("image/png");
```

### 2. Image Preprocessing

**Server-Side Processing**:
```python
# Remove data URI prefix
image_data = re.sub('^data:image/.+;base64,', '', image_b64)

# Decode base64 to binary
binary_data = base64.b64decode(image_data)

# Convert to PIL Image
image_PIL = Image.open(BytesIO(binary_data))

# Save as PNG
image_PIL.save("snapshots/pic.png", mode='RGB')
```

**Transformations**:
1. Base64 string → Binary data
2. Binary → PIL Image object
3. PIL Image → PNG file (RGB mode)

### 3. API Call

**Service**: Algorithmia Cloud Platform

**Model**: `deeplearning/EmotionRecognitionCNNMBP/1.0.1`

**Technology**: Convolutional Neural Network (CNN) with Multi-task Learning

**Code**:
```python
# Read image as bytearray
input = bytearray(open("snapshots/pic.png", "rb").read())

# Initialize client
client = Algorithmia.client('api-key')

# Get algorithm
algo = client.algo('deeplearning/EmotionRecognitionCNNMBP/1.0.1')

# Make prediction
result = algo.pipe(input).result
```

**Request**:
- **Method**: Binary pipe
- **Input**: Raw PNG bytes
- **Size**: ~50-150 KB
- **Timeout**: 5 seconds (default)

### 4. Response Parsing

**API Response Structure**:
```json
{
    "results": [
        {
            "emotions": [
                {
                    "label": "Happy",
                    "confidence": 0.8523
                },
                {
                    "label": "Neutral",
                    "confidence": 0.0892
                },
                {
                    "label": "Sad",
                    "confidence": 0.0234
                },
                {
                    "label": "Surprise",
                    "confidence": 0.0156
                },
                {
                    "label": "Angry",
                    "confidence": 0.0089
                },
                {
                    "label": "Fear",
                    "confidence": 0.0067
                },
                {
                    "label": "Disgust",
                    "confidence": 0.0039
                }
            ]
        }
    ]
}
```

**Parsing Logic**:
```python
# Extract results
op = algo.pipe(input).result["results"]

# Handle no face detected
if op == []:
    current = "Neutral"
else:
    # Get emotions array
    emotion = op[0]["emotions"]
    
    # Build confidence dictionary
    analyze = {}
    for emo in emotion:
        analyze[str(emo["label"])] = float(emo["confidence"])
    
    # Select emotion with highest confidence
    current = max(analyze, key=analyze.get)
```

### 5. Emotion Encoding

**Purpose**: Store emotion history for visualization

**Color Code Mapping**:
```python
emotion_color_dict = {
    'Neutral': 11,   # Blue
    'Sad': 31,       # Green
    'Disgust': 51,   # Magenta
    'Fear': 61,      # Black
    'Surprise': 41,  # Cyan
    'Happy': 21,     # Yellow
    'Angry': 1       # Red
}
```

**Storage**:
```python
# Append to global list
emot_list.append(emotion_color_dict[current])
```

## Model Details

### EmotionRecognitionCNNMBP

**Architecture**: Convolutional Neural Network

**Training Data**: 
- FER-2013 dataset (likely)
- 35,887 facial images
- 7 emotion categories

**Input Requirements**:
- Grayscale or RGB images
- Face should be visible and centered
- Minimum resolution: 48×48 pixels
- Supported formats: PNG, JPEG, BMP

**Output**:
- Confidence scores for all 7 emotions
- Scores sum to approximately 1.0
- Range: 0.0 to 1.0 per emotion

**Performance**:
- Latency: 2-5 seconds (including network)
- Accuracy: ~65-70% on FER-2013 test set (typical for this task)

## Edge Cases & Error Handling

### No Face Detected

**Scenario**: User not in frame, poor lighting, or face obscured

**API Response**:
```json
{
    "results": []
}
```

**Handling**:
```python
if op == []:
    current = "Neutral"
```

**Result**: Defaults to Neutral emotion, playlist continues

### Multiple Faces

**Scenario**: Multiple people in webcam view

**Behavior**: API typically returns emotions for the most prominent face

**Handling**: No special handling; uses first result

### Poor Image Quality

**Scenario**: Low light, motion blur, extreme angles

**Behavior**: Lower confidence scores, potentially incorrect classification

**Handling**: No validation of confidence threshold; accepts any result

### API Failures

**Scenario**: Network timeout, invalid API key, service down

**Current Behavior**: Exception raised, no playlist generated

**Improvement Needed**:
```python
try:
    op = algo.pipe(input).result["results"]
except Exception as e:
    print(f"API Error: {e}")
    current = "Neutral"  # Fallback
```

## Accuracy Considerations

### Factors Affecting Accuracy

1. **Lighting Conditions**
   - Optimal: Well-lit, even lighting
   - Poor: Backlighting, shadows, darkness

2. **Face Position**
   - Optimal: Frontal view, centered
   - Poor: Profile view, tilted, partially visible

3. **Image Quality**
   - Optimal: Clear, high resolution, in focus
   - Poor: Blurry, pixelated, compressed

4. **User Characteristics**
   - Age, gender, ethnicity can affect accuracy
   - Facial hair, glasses, makeup may impact results

5. **Expression Intensity**
   - Strong expressions: Higher accuracy
   - Subtle expressions: Lower accuracy

### Confidence Thresholds

**Current Implementation**: No threshold filtering

**Recommendation**: Implement confidence threshold
```python
if max(analyze.values()) < 0.5:
    current = "Neutral"  # Low confidence
else:
    current = max(analyze, key=analyze.get)
```

## Emotion History Tracking

### Storage Mechanism

**Global Variable**:
```python
emot_list = []  # Stores color codes
```

**Append on Detection**:
```python
emot_list.append(emotion_color_dict[current])
```

**Persistence**: In-memory only (lost on server restart)

### Visualization

**Grid Layout**: 5 rows × 10 columns = 50 emotions max

**Color Mapping**:
```python
cmap = colors.ListedColormap([
    'red',      # Angry (0-10)
    'blue',     # Neutral (10-20)
    'yellow',   # Happy (20-30)
    'green',    # Sad (30-40)
    'cyan',     # Surprise (40-50)
    'magenta',  # Disgust (50-60)
    'black',    # Fear (60-70)
    'white'     # No data (80+)
])
```

**Generation**:
```python
def get_emotion_grid():
    data = np.full((5, 10), 81)  # Initialize with white
    
    a = 0
    for i in range(5):
        for q in range(10):
            if a == len(emot_list):
                break
            data[i, q] = emot_list[a]
            a += 1
    
    fig, ax = plt.subplots()
    ax.imshow(data, cmap=cmap, norm=norm)
    plt.savefig("static/graph.jpg")
```

## Performance Metrics

### Timing Breakdown

| Step | Duration | Notes |
|------|----------|-------|
| Canvas capture | 10-50ms | Client-side |
| Base64 encoding | 50-100ms | Client-side |
| AJAX transmission | 100-500ms | Network dependent |
| Image decoding | 50-100ms | Server-side |
| File save | 10-50ms | Disk I/O |
| API call | 2000-5000ms | **Bottleneck** |
| Response parsing | 1-5ms | Server-side |
| Playlist generation | 10-50ms | Server-side |
| Template render | 50-100ms | Server-side |

**Total**: ~2.5-6 seconds per detection

### Optimization Opportunities

1. **Reduce Image Size**: Downscale to 224×224 (common CNN input)
2. **Compress Image**: Use JPEG with 80% quality
3. **Cache Results**: Store recent emotions to avoid redundant calls
4. **Async Processing**: Don't block user while detecting
5. **Local Model**: Run emotion detection client-side (TensorFlow.js)

## Privacy & Security

### Data Handling

**Captured Images**:
- Stored temporarily in `snapshots/pic.png`
- Overwritten on each detection
- Not persisted long-term
- Not transmitted to any service except Algorithmia

**API Transmission**:
- Sent to Algorithmia cloud service
- Subject to Algorithmia's privacy policy
- No control over data retention

**Recommendations**:
1. Inform users about webcam usage
2. Add option to disable emotion detection
3. Implement local processing if possible
4. Clear snapshots on session end
5. Use HTTPS for all API calls

### User Consent

**Current Implementation**: No explicit consent mechanism

**Best Practices**:
- Display webcam indicator
- Request permission before capture
- Provide opt-out option
- Show privacy policy link

## Future Improvements

### Enhanced Detection
- Multi-face support with selection UI
- Confidence threshold filtering
- Emotion smoothing (average over time)
- Fallback to manual emotion selection

### Performance
- Client-side emotion detection (TensorFlow.js)
- Image optimization before upload
- Caching and rate limiting
- Async/background processing

### Accuracy
- Calibration phase for individual users
- Lighting quality detection
- Face position validation
- Confidence score display

### Privacy
- Local-only processing option
- Automatic image deletion
- Encrypted transmission
- User consent workflow
