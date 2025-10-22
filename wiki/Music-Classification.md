# Music Classification System

## Overview

Muze organizes 903 songs into 5 emotional clusters and uses a sophisticated selection algorithm to generate playlists that match detected emotions. This document explains the music classification system, cluster organization, and playlist generation logic.

## Song Database

### Structure

**File**: `test.txt`

**Format**: Pickled Python list (Python 2 pickle protocol)

**Total Songs**: 903 (indexed 0-902)

**Entry Format**: `"Song Name - Artist"`

**Example Entries**:
```python
[
    "(Mama) He Treats Your Daughter Mean - Brown",
    "Night in Tunisia - Blakey",
    "Along Came Jones - Coasters",
    "Back in Black - AC/DC",
    "Bad Reputation - Jett",
    ...
]
```

### Loading the Database

```python
import pickle

with open("test.txt", "rb") as fp:
    songnames = pickle.load(fp, encoding='latin1')

# Access songs by index
print(songnames[0])  # First song
print(songnames[902])  # Last song
```

### File Naming Convention

**Audio Files**: `static/music/XXX.mp3`

**Naming Pattern**: Zero-padded 3-digit index
- `001.mp3` → Song at index 1
- `045.mp3` → Song at index 45
- `234.mp3` → Song at index 234
- `903.mp3` → Song at index 903

**Note**: Index 0 appears to be unused or reserved

## Cluster System

### Cluster Definitions

Songs are organized into **5 clusters** based on emotional characteristics:

```python
songlist = {
    1: [1, 170],      # Cluster 1: Songs 1-170 (170 songs)
    2: [171, 334],    # Cluster 2: Songs 171-334 (164 songs)
    3: [335, 549],    # Cluster 3: Songs 335-549 (215 songs)
    4: [550, 740],    # Cluster 4: Songs 550-740 (191 songs)
    5: [741, 903]     # Cluster 5: Songs 741-903 (163 songs)
}
```

### Cluster Characteristics

Based on the MIREX 2007 Audio Music Mood Classification dataset:

| Cluster | Range | Count | Likely Mood | Energy Level | Example Genres |
|---------|-------|-------|-------------|--------------|----------------|
| **1** | 1-170 | 170 | Energetic/Upbeat | High | Rock, Pop, Dance |
| **2** | 171-334 | 164 | Moderate Energy | Medium-High | Blues, Jazz, Soul |
| **3** | 335-549 | 215 | Neutral/Mixed | Medium | Various, Eclectic |
| **4** | 550-740 | 191 | Calm/Mellow | Low-Medium | Ballads, Soft Rock |
| **5** | 741-903 | 163 | Intense/Dark | High | Metal, Punk, Aggressive |

**Note**: Exact cluster characteristics are inferred from emotion mappings and typical music therapy practices.

## Emotion-to-Cluster Mapping

### Mapping Algorithm

Each emotion maps to a specific **cluster distribution** that defines:
1. Which clusters to use
2. How many songs from each cluster

```python
def get_playlist():
    current = get_emotion()
    
    if (current == "Anger") | (current == "Fear"):
        cluster_def = [[5, 2], [3, 7], [2, 12]]
    elif current == "Sad":
        cluster_def = [[3, 4], [4, 4], [2, 13]]
    elif (current == "Neutral") | (current == "Disgust") | (current == "Surprise"):
        cluster_def = [[3, 2], [4, 5], [2, 7], [1, 5]]
    else:  # Happy
        cluster_def = [[2, 10], [4, 5], [1, 6]]
```

### Detailed Mappings

#### 😠 Anger / 😨 Fear
**Strategy**: Intense then calming progression

| Cluster | Songs | Purpose |
|---------|-------|---------|
| 5 (Intense) | 2 | Match intense emotion |
| 3 (Neutral) | 7 | Transition to calm |
| 2 (Moderate) | 12 | Settle into moderate mood |

**Total**: 21 songs

**Rationale**: Start with intense music to match the emotion, then gradually calm down

---

#### 😢 Sad
**Strategy**: Acknowledge sadness, then uplift

| Cluster | Songs | Purpose |
|---------|-------|---------|
| 3 (Neutral) | 4 | Gentle start |
| 4 (Calm) | 4 | Acknowledge sadness |
| 2 (Moderate) | 13 | Gradually uplift |

**Total**: 21 songs

**Rationale**: Validate the emotion with mellow songs, then slowly introduce more energy

---

#### 😐 Neutral / 🤢 Disgust / 😲 Surprise
**Strategy**: Balanced variety

| Cluster | Songs | Purpose |
|---------|-------|---------|
| 3 (Neutral) | 2 | Safe middle ground |
| 4 (Calm) | 5 | Relaxing element |
| 2 (Moderate) | 7 | Moderate energy |
| 1 (Energetic) | 5 | Uplifting boost |

**Total**: 19 songs

**Rationale**: Provide variety to help discover mood or shift neutral state

---

#### 😊 Happy
**Strategy**: Maintain and enhance positive mood

| Cluster | Songs | Purpose |
|---------|-------|---------|
| 2 (Moderate) | 10 | Sustained positive energy |
| 4 (Calm) | 5 | Prevent overstimulation |
| 1 (Energetic) | 6 | Peak happiness |

**Total**: 21 songs

**Rationale**: Keep energy high but balanced to maintain happiness without exhaustion

## Playlist Generation Algorithm

### Random Selection Process

```python
playlist = []

for sets in cluster_def:
    cluster_id = sets[0]  # Which cluster
    num_songs = sets[1]   # How many songs
    
    for i in range(num_songs):
        # Random song index from cluster range
        ss = random.randint(
            songlist[cluster_id][0],  # Start of range
            songlist[cluster_id][1]   # End of range
        )
        
        # Format: "XXX.mp3_Song Name - Artist"
        playlist.append(f"{ss:03d}.mp3_{songnames[ss]}")

return playlist
```

### Example Execution

**Emotion**: Happy

**Cluster Definition**: `[[2, 10], [4, 5], [1, 6]]`

**Step 1**: Cluster 2, 10 songs
```python
random.randint(171, 334)  # 10 times
# Results: [234, 189, 312, 201, 278, 245, 198, 321, 267, 223]
```

**Step 2**: Cluster 4, 5 songs
```python
random.randint(550, 740)  # 5 times
# Results: [612, 689, 571, 634, 702]
```

**Step 3**: Cluster 1, 6 songs
```python
random.randint(1, 170)  # 6 times
# Results: [45, 123, 89, 156, 34, 98]
```

**Final Playlist**:
```python
[
    "234.mp3_Night in Tunisia - Blakey",
    "189.mp3_Along Came Jones - Coasters",
    "312.mp3_Some Song - Artist",
    # ... 18 more songs
]
```

### Playlist Characteristics

**Length**: 19-21 songs (varies by emotion)

**Duration**: ~60-90 minutes (assuming 3-4 min per song)

**Randomization**: New playlist every time, even for same emotion

**Ordering**: Follows cluster sequence (not shuffled after generation)

## Music Therapy Principles

### Iso Principle

**Definition**: Start with music matching current mood, then gradually shift

**Application in Muze**:
- Anger/Fear: Start intense (Cluster 5) → Calm down (Clusters 3, 2)
- Sad: Start mellow (Clusters 3, 4) → Uplift (Cluster 2)

### Mood Regulation

**Strategies**:
1. **Matching**: Validate current emotion (first few songs)
2. **Transitioning**: Gradual shift through clusters
3. **Targeting**: End at desired emotional state

### Energy Management

**Considerations**:
- Avoid extreme jumps in energy
- Cluster sequences provide smooth transitions
- Balance high and low energy songs

## Data Source

### MIREX 2007 Dataset

**Full Name**: Music Information Retrieval Evaluation eXchange 2007

**Task**: Audio Music Mood Classification

**URL**: http://www.music-ir.org/mirex/wiki/2007:Audio_Music_Mood_Classification

**Dataset Details**:
- Academic research dataset
- Pre-classified by mood/emotion
- Used for benchmarking mood detection algorithms

**Mood Categories** (typical):
1. Cluster 1: Rowdy, Rousing, Confident, Boisterous
2. Cluster 2: Amiable, Good-natured
3. Cluster 3: Literate, Poignant, Wistful, Bittersweet
4. Cluster 4: Humorous, Silly, Campy, Quirky
5. Cluster 5: Aggressive, Fiery, Tense, Anxious

**Note**: Exact mapping to Muze clusters may vary

## Limitations & Considerations

### Current Limitations

1. **Fixed Clusters**: No dynamic re-clustering
2. **No Song Metadata**: Tempo, key, genre not used
3. **Random Selection**: No similarity-based selection
4. **No User Preferences**: Can't skip or favorite songs
5. **Limited Library**: Only 903 songs
6. **No Repeat Prevention**: Same song can appear multiple times

### Potential Improvements

#### 1. Enhanced Selection
```python
# Track played songs to avoid repeats
played_songs = set()

while len(playlist) < num_songs:
    ss = random.randint(start, end)
    if ss not in played_songs:
        playlist.append(ss)
        played_songs.add(ss)
```

#### 2. Weighted Selection
```python
# Prefer songs with higher mood match scores
weights = get_song_weights(cluster_id, emotion)
ss = random.choices(range(start, end), weights=weights)[0]
```

#### 3. User Feedback
```python
# Learn from user skips and likes
if user_skipped(song_id):
    reduce_weight(song_id, emotion)
if user_liked(song_id):
    increase_weight(song_id, emotion)
```

#### 4. Audio Features
```python
# Use tempo, energy, valence for better matching
songs = get_songs_by_features(
    tempo_range=(120, 140),
    energy_min=0.7,
    valence_min=0.6
)
```

#### 5. Smooth Transitions
```python
# Order songs by similarity within cluster
playlist = sort_by_similarity(selected_songs)
```

## Playlist Format

### Server-Side Format
```python
[
    "001.mp3_(Mama) He Treats Your Daughter Mean - Brown",
    "234.mp3_Night in Tunisia - Blakey",
    "567.mp3_Along Came Jones - Coasters"
]
```

### Client-Side Parsing
```javascript
var songlist = {{ songs|tojson }};

// Parse each entry
var parts = songlist[i].split("_");
var filename = parts[0];      // "234.mp3"
var displayName = parts[1];   // "Night in Tunisia - Blakey"

// Build audio source URL
var audioUrl = "/static/music/" + filename;
```

### Display Format
```javascript
document.getElementById('ss').innerHTML = displayName;
// Shows: "Night in Tunisia - Blakey"
```

## Performance Considerations

### Generation Speed
- **Cluster lookup**: O(1)
- **Random selection**: O(n) where n = songs per cluster
- **Total time**: <100ms for typical playlist

### Memory Usage
- **Song database**: ~50KB (pickled list)
- **Playlist**: ~2-5KB (21 strings)
- **Minimal overhead**

### Scalability
- Current system handles 903 songs efficiently
- Could scale to 10,000+ songs without issues
- Bottleneck would be file storage, not algorithm

## Testing & Validation

### Verify Cluster Ranges
```python
# Ensure no overlap
for i in range(1, 5):
    assert songlist[i][1] + 1 == songlist[i+1][0]

# Verify total coverage
assert songlist[1][0] == 1
assert songlist[5][1] == 903
```

### Test Playlist Generation
```python
# Test each emotion
for emotion in ["Happy", "Sad", "Angry", "Fear", "Neutral", "Disgust", "Surprise"]:
    playlist = get_playlist_for_emotion(emotion)
    assert len(playlist) > 0
    assert all("mp3" in song for song in playlist)
```

### Validate Song Indices
```python
# Ensure all indices are valid
for song in playlist:
    index = int(song.split(".")[0])
    assert 1 <= index <= 903
    assert index in songnames
```
