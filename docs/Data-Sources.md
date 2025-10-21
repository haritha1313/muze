# Data Sources and Credits

## Overview

This document provides information about the data sources used in Muze, including the music dataset, emotion recognition model, and other resources.

---

## Music Dataset

### MIREX 2007: Audio Music Mood Classification

**Source**: Music Information Retrieval Evaluation eXchange (MIREX)

**URL**: http://www.music-ir.org/mirex/wiki/2007:Audio_Music_Mood_Classification

**Year**: 2007

**Purpose**: Academic research dataset for evaluating music mood classification algorithms

---

### Dataset Details

**Total Songs**: 903 tracks

**Organization**: 5 emotional clusters

**File Format**: MP3 audio files

**Metadata Format**: Pickled Python list (`test.txt`)

---

### Cluster Organization

| Cluster | Song Range | Count | Characteristics |
|---------|------------|-------|-----------------|
| 1 | 1-170 | 170 | Energetic, upbeat, high energy |
| 2 | 171-334 | 164 | Moderate energy, amiable |
| 3 | 335-549 | 215 | Neutral, mixed moods |
| 4 | 550-740 | 191 | Calm, mellow, low energy |
| 5 | 741-903 | 163 | Intense, aggressive, dark |

---

### Mood Categories

Based on MIREX 2007 classification:

**Cluster 1 - Energetic/Positive**
- Rowdy
- Rousing
- Confident
- Boisterous
- Passionate

**Cluster 2 - Moderate/Friendly**
- Amiable
- Good-natured
- Pleasant
- Agreeable

**Cluster 3 - Neutral/Reflective**
- Literate
- Poignant
- Wistful
- Bittersweet
- Thoughtful

**Cluster 4 - Calm/Relaxed**
- Humorous
- Silly
- Campy
- Quirky
- Whimsical

**Cluster 5 - Intense/Negative**
- Aggressive
- Fiery
- Tense
- Anxious
- Volatile

---

### Song Metadata

**Format**: `"Song Title - Artist Name"`

**Example Entries**:
```
(Mama) He Treats Your Daughter Mean - Brown
Night in Tunisia - Blakey
Along Came Jones - Coasters
Back in Black - AC/DC
Bad Reputation - Jett
```

**Storage**: Pickled Python list in `test.txt`

**Encoding**: Latin-1

---

### Dataset Usage

**Academic Purpose**: Originally created for research

**Mood Classification**: Pre-labeled by music experts

**Evaluation**: Used to benchmark mood detection algorithms

**Public Availability**: Dataset available for research purposes

---

## Emotion Recognition

### Algorithmia EmotionRecognitionCNNMBP

**Provider**: Algorithmia (now DataRobot)

**URL**: https://algorithmia.com/

**Algorithm**: `deeplearning/EmotionRecognitionCNNMBP/1.0.1`

**Type**: Convolutional Neural Network with Multi-task Learning

---

### Model Details

**Training Dataset**: Likely FER-2013 (Facial Expression Recognition 2013)

**Dataset Size**: ~35,000 facial images

**Emotion Categories**: 7 emotions
- Happy
- Sad
- Angry
- Fear
- Surprise
- Disgust
- Neutral

**Input**: RGB or grayscale images

**Output**: Confidence scores for each emotion (0.0 to 1.0)

---

### FER-2013 Dataset

**Source**: Kaggle competition (2013)

**Images**: 35,887 grayscale images (48×48 pixels)

**Collection Method**: Scraped from Google Image Search

**Labeling**: Crowdsourced via Amazon Mechanical Turk

**Distribution**:
- Training: 28,709 images
- Public Test: 3,589 images
- Private Test: 3,589 images

**Challenges**:
- Low resolution
- Varied lighting conditions
- Occlusions (glasses, hands)
- Age and ethnicity diversity

---

## Third-Party Libraries

### Python Libraries

#### Flask
- **Version**: 0.12.2
- **License**: BSD-3-Clause
- **Purpose**: Web framework
- **URL**: https://flask.palletsprojects.com/

#### Algorithmia
- **Version**: 1.0.0+
- **License**: MIT
- **Purpose**: API client for Algorithmia platform
- **URL**: https://algorithmia.com/developers

#### Pillow (PIL)
- **Version**: 5.0.0
- **License**: PIL License
- **Purpose**: Image processing
- **URL**: https://python-pillow.org/

#### NumPy
- **Version**: 1.14.0
- **License**: BSD
- **Purpose**: Numerical computing
- **URL**: https://numpy.org/

#### Matplotlib
- **Version**: 2.1.2
- **License**: PSF-based
- **Purpose**: Data visualization
- **URL**: https://matplotlib.org/

#### Jinja2
- **Version**: 2.10
- **License**: BSD-3-Clause
- **Purpose**: Template engine
- **URL**: https://jinja.palletsprojects.com/

---

### JavaScript Libraries

#### jQuery
- **Version**: 1.7.1
- **License**: MIT
- **Purpose**: DOM manipulation, AJAX
- **URL**: https://jquery.com/

**Note**: Consider upgrading to latest version (3.x)

---

## Visual Assets

### Plutchik Emotion Wheel

**File**: `Plutchik-Model-600.png`

**Source**: Robert Plutchik's Wheel of Emotions

**Purpose**: Reference for emotion theory

**Description**: Visual representation of 8 primary emotions and their combinations

**License**: Public domain (educational use)

---

## APIs and Services

### Algorithmia Platform

**Service**: Cloud-based machine learning platform

**Pricing**: 
- Free tier: 5,000 credits/month
- Paid plans available

**API Endpoint**: `https://api.algorithmia.com/v1/algo/`

**Authentication**: API key required

**Rate Limits**: Varies by plan

---

### WebRTC

**Technology**: Web Real-Time Communication

**Purpose**: Webcam access in browser

**Specification**: W3C standard

**Browser Support**: Chrome, Firefox, Safari, Edge

**License**: Open standard

---

## Data Privacy

### User Data

**Webcam Images**:
- Captured locally in browser
- Sent to Algorithmia API for processing
- Temporarily stored in `snapshots/pic.png`
- Overwritten on each capture
- Not permanently stored by Muze

**Emotion Data**:
- Stored in-memory during session
- Used for emotion history visualization
- Cleared on server restart
- Not persisted to database

**Music Preferences**:
- Not currently tracked
- No user accounts or profiles
- No data collection

---

### Third-Party Data Sharing

**Algorithmia**:
- Receives webcam snapshots
- Processes images for emotion detection
- Subject to Algorithmia privacy policy
- Data retention per their terms

**No Other Sharing**:
- No analytics services
- No advertising networks
- No social media integration
- No third-party cookies

---

## Licensing

### Project License

**Muze**: See LICENSE file in repository

### Dataset License

**MIREX 2007**: Academic research use

**Restrictions**:
- Verify licensing for commercial use
- Respect artist copyrights
- Attribute original sources

### Dependencies

All third-party libraries used under their respective licenses:
- MIT License: Algorithmia SDK, jQuery
- BSD License: Flask, NumPy, Pillow
- PSF-based: Matplotlib

---

## Attribution

### Required Attribution

When using or distributing Muze, please include:

```
Music dataset: MIREX 2007 Audio Music Mood Classification
http://www.music-ir.org/mirex/wiki/2007:Audio_Music_Mood_Classification

Emotion recognition: Algorithmia EmotionRecognitionCNNMBP
https://algorithmia.com/
```

---

## Data Updates

### Updating Music Library

To use your own music:

1. **Prepare MP3 files**:
   - Name files: `001.mp3`, `002.mp3`, etc.
   - Place in `static/music/`

2. **Create metadata**:
   ```python
   import pickle
   
   songs = [
       "Song 1 - Artist 1",
       "Song 2 - Artist 2",
       # ... add all songs
   ]
   
   with open("test.txt", "wb") as f:
       pickle.dump(songs, f)
   ```

3. **Update cluster ranges**:
   ```python
   # In algorithmia.py
   songlist = {
       1: [1, 200],      # Adjust ranges
       2: [201, 400],
       3: [401, 600],
       4: [601, 800],
       5: [801, 1000]
   }
   ```

---

### Updating Emotion Model

To use different emotion detection:

1. **Find alternative algorithm** on Algorithmia

2. **Update API call**:
   ```python
   # In algorithmia.py
   algo = client.algo('deeplearning/YourChosenAlgorithm/1.0.0')
   ```

3. **Adjust emotion mapping** if categories differ

---

## Research Citations

### MIREX

```
@inproceedings{mirex2007mood,
  title={MIREX 2007: Audio Music Mood Classification},
  booktitle={Music Information Retrieval Evaluation eXchange},
  year={2007},
  url={http://www.music-ir.org/mirex/wiki/2007:Audio_Music_Mood_Classification}
}
```

### FER-2013

```
@article{goodfellow2013challenges,
  title={Challenges in representation learning: A report on three machine learning contests},
  author={Goodfellow, Ian J and Erhan, Dumitru and Carrier, Pierre Luc and Courville, Aaron and Mirza, Mehdi and Hamner, Ben and Cukierski, Will and Tang, Yichuan and Thaler, David and Lee, Dong-Hyun and others},
  journal={Neural Networks},
  volume={64},
  pages={59--63},
  year={2015},
  publisher={Elsevier}
}
```

---

## Acknowledgments

### Contributors

- Original MIREX 2007 dataset creators
- Algorithmia/DataRobot for emotion recognition API
- Open source library maintainers
- Music artists whose work is included

### Inspiration

- Music therapy research
- Emotion psychology (Plutchik, Ekman)
- Music information retrieval community

---

## Contact

For questions about data sources or licensing:

- Check repository issues
- Review documentation
- Contact repository maintainers

---

## Disclaimer

**Music Rights**: Ensure you have proper licenses for any music files used. The original MIREX dataset was for research purposes.

**API Usage**: Algorithmia API subject to their terms of service and pricing.

**No Warranty**: Data provided as-is for educational/research purposes.

**Privacy**: Users should be informed about webcam usage and data processing.
