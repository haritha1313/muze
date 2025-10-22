# Overview

## What is Muze?

**Muze** is an AI-powered music therapy web application that analyzes your emotions in real-time and creates personalized music playlists to match or improve your mood. Using advanced facial recognition technology, Muze detects your emotional state and selects songs from a curated library designed to complement your feelings.

## The Problem

Music has a profound impact on our emotional well-being, but finding the right music for your current mood can be challenging. Traditional music apps require manual selection and don't adapt to your emotional state in real-time.

## The Solution

Muze combines:
- **Computer Vision**: Real-time facial emotion detection via webcam
- **Machine Learning**: Algorithmia's deep learning emotion recognition model
- **Music Psychology**: Scientifically-organized music library based on emotional clusters
- **Adaptive Playlists**: Dynamic song selection that responds to mood changes

## How It Works

1. **Capture**: Your webcam captures your facial expression
2. **Analyze**: AI analyzes your face to detect emotions (Happy, Sad, Angry, Fear, Surprise, Disgust, Neutral)
3. **Select**: Algorithm selects songs from emotional clusters matching your mood
4. **Play**: Personalized playlist starts playing automatically
5. **Adapt**: Every 20 songs, Muze rechecks your emotion and adjusts the playlist

## Key Features

### 🎭 Emotion Detection
- Detects 7 emotions: Happy, Sad, Angry, Fear, Surprise, Disgust, Neutral
- Uses state-of-the-art CNN-based emotion recognition
- Real-time processing via webcam

### 🎵 Smart Playlist Generation
- 900+ songs organized into 5 emotional clusters
- Cluster-based selection algorithm
- Mood-appropriate song sequences

### 📊 Emotion Tracking
- Visual emotion history grid
- Color-coded emotion timeline
- Track mood changes over listening sessions

### 🔄 Continuous Adaptation
- Periodic emotion re-evaluation (every 20 songs)
- Dynamic playlist adjustment
- Responsive to mood shifts

## Technology Stack

- **Backend**: Flask (Python)
- **AI/ML**: Algorithmia EmotionRecognitionCNNMBP API
- **Frontend**: HTML5, JavaScript, jQuery
- **Media**: WebRTC getUserMedia API
- **Visualization**: Matplotlib
- **Image Processing**: Pillow (PIL)

## Use Cases

- **Late Night Listening**: Discover music that matches your nocturnal moods
- **Emotional Support**: Find comfort through mood-appropriate music
- **Mood Enhancement**: Lift your spirits with energizing tracks
- **Stress Relief**: Calm down with soothing selections
- **Music Discovery**: Explore songs you might not have found otherwise

## Limitations

- Requires webcam access
- Needs Algorithmia API key (external service)
- Limited to pre-loaded music library (903 songs)
- Emotion detection accuracy depends on lighting and camera quality
- Internet connection required for emotion recognition API

## Data Credits

Music dataset sourced from:
- [MIREX 2007: Audio Music Mood Classification](http://www.music-ir.org/mirex/wiki/2007:Audio_Music_Mood_Classification)
