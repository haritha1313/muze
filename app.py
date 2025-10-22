import flask, flask.views
from flask import request, jsonify
from algorithmia import get_playlist
from algorithmia import get_emotion_grid
import numpy as np
from PIL import Image
import re
from io import BytesIO
import base64
import json
import datetime
from collections import defaultdict

app = flask.Flask(__name__)
app.secret_key = "bacon"

# Emotion tracking storage
emotion_history = []

@app.route('/')
def index():
    return flask.render_template("musi.html", songs=[])

@app.route('/hook', methods=['POST'])
def get_image():
    #convert base64 image
    image_b64 = request.values['imageBase64']
    image_data = re.sub('^data:image/.+;base64,', '', image_b64)
    image_PIL = Image.open(BytesIO(base64.b64decode(image_data)))
    image_PIL.save("snapshots/pic.png", mode='RGB')
    songs = get_playlist()
    print(songs)
    return flask.render_template("musi.html", songs=songs)
    
@app.route('/graph')
def get_graph():
    #draw emotion grid
    get_emotion_grid()
    songs = get_playlist()
    return flask.render_template("musi.html", songs=songs)

def validate_snapshot():
    import os
    return os.path.exists("snapshots/pic.png")

def cleanup_old_snapshots():
    import os
    import time
    snapshot_dir = "snapshots"
    if os.path.exists(snapshot_dir):
        for filename in os.listdir(snapshot_dir):
            filepath = os.path.join(snapshot_dir, filename)
            if os.path.isfile(filepath) and filename.endswith('.png'):
                file_age = time.time() - os.path.getmtime(filepath)
                if file_age > 3600:  # older than 1 hour
                    os.remove(filepath)

def get_emotion_summary(emotion_data):
    """
    Analyze emotion data and return a summary with dominant emotions.
    
    This function processes emotion detection results and identifies
    the primary and secondary emotions detected in the user's facial expression.
    """
    if not emotion_data or not isinstance(emotion_data, dict):
        return {"primary": "neutral", "secondary": None, "confidence": 0.0}
    
    # Sort emotions by confidence score
    sorted_emotions = sorted(emotion_data.items(), key=lambda x: x[1], reverse=True)
    
    primary = sorted_emotions[0][0] if sorted_emotions else "neutral"
    secondary = sorted_emotions[1][0] if len(sorted_emotions) > 1 else None
    confidence = sorted_emotions[0][1] if sorted_emotions else 0.0
    
    return {
        "primary": primary,
        "secondary": secondary,
        "confidence": confidence,
        "all_emotions": dict(sorted_emotions)
    }

def filter_playlist_by_mood(songs, mood_category):
    """
    Filter and rank songs based on the detected mood category.
    
    Takes a list of songs and a mood category (e.g., 'happy', 'sad', 'energetic')
    and returns songs that best match the mood, sorted by relevance.
    """
    mood_mappings = {
        "happy": ["joy", "excitement", "contentment"],
        "sad": ["sadness", "melancholy", "longing"],
        "energetic": ["excitement", "anticipation", "joy"],
        "calm": ["serenity", "peace", "contentment"],
        "angry": ["anger", "frustration", "intensity"]
    }
    
    if mood_category not in mood_mappings:
        return songs
    
    # Filter songs that match the mood
    filtered_songs = []
    target_emotions = mood_mappings[mood_category]
    
    for song in songs:
        if hasattr(song, 'mood') and song.mood in target_emotions:
            filtered_songs.append(song)
    
    return filtered_songs if filtered_songs else songs

def track_emotion_event(emotion, confidence, image_path=None):
    """
    Record an emotion detection event with timestamp and metadata.

    Stores emotion detection results in the emotion_history list for later analysis.
    Each event includes the detected emotion, confidence score, timestamp, and optional
    image reference for tracking user's emotional journey over time.

    Args:
        emotion: The detected emotion label (e.g., 'happy', 'sad')
        confidence: Confidence score (0.0 to 1.0) for the detection
        image_path: Optional path to the snapshot image

    Returns:
        dict: The created emotion event record
    """
    event = {
        "emotion": emotion,
        "confidence": float(confidence),
        "timestamp": datetime.datetime.now().isoformat(),
        "image_path": image_path,
        "session_id": flask.session.get('session_id', 'unknown')
    }
    emotion_history.append(event)
    return event

def get_emotion_trends(time_window_minutes=60):
    """
    Analyze emotion trends over a specified time window.

    Processes recent emotion history to identify patterns, dominant emotions,
    and emotional transitions. Useful for understanding user's emotional state
    progression over time.

    Args:
        time_window_minutes: Number of minutes to look back in history (default: 60)

    Returns:
        dict: Analysis containing:
            - dominant_emotion: Most frequent emotion in the time window
            - emotion_distribution: Percentage breakdown of all emotions
            - transition_count: Number of emotion changes
            - average_confidence: Mean confidence across all detections
            - trend_direction: Whether emotions are trending positive/negative
    """
    if not emotion_history:
        return {
            "dominant_emotion": None,
            "emotion_distribution": {},
            "transition_count": 0,
            "average_confidence": 0.0,
            "trend_direction": "neutral"
        }

    # Filter by time window
    now = datetime.datetime.now()
    cutoff_time = now - datetime.timedelta(minutes=time_window_minutes)

    recent_emotions = [
        e for e in emotion_history
        if datetime.datetime.fromisoformat(e['timestamp']) > cutoff_time
    ]

    if not recent_emotions:
        return {
            "dominant_emotion": None,
            "emotion_distribution": {},
            "transition_count": 0,
            "average_confidence": 0.0,
            "trend_direction": "neutral"
        }

    # Calculate distribution
    emotion_counts = defaultdict(int)
    total_confidence = 0.0

    for event in recent_emotions:
        emotion_counts[event['emotion']] += 1
        total_confidence += event['confidence']

    total_events = len(recent_emotions)
    emotion_distribution = {
        emotion: (count / total_events) * 100
        for emotion, count in emotion_counts.items()
    }

    # Find dominant emotion
    dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]

    # Count transitions
    transitions = 0
    for i in range(1, len(recent_emotions)):
        if recent_emotions[i]['emotion'] != recent_emotions[i-1]['emotion']:
            transitions += 1

    # Determine trend direction
    positive_emotions = {'happy', 'joy', 'excitement', 'contentment'}
    negative_emotions = {'sad', 'angry', 'fear', 'disgust'}

    recent_half = recent_emotions[len(recent_emotions)//2:]
    earlier_half = recent_emotions[:len(recent_emotions)//2]

    positive_score_recent = sum(1 for e in recent_half if e['emotion'].lower() in positive_emotions)
    positive_score_earlier = sum(1 for e in earlier_half if e['emotion'].lower() in positive_emotions)

    if positive_score_recent > positive_score_earlier:
        trend_direction = "improving"
    elif positive_score_recent < positive_score_earlier:
        trend_direction = "declining"
    else:
        trend_direction = "stable"

    return {
        "dominant_emotion": dominant_emotion,
        "emotion_distribution": emotion_distribution,
        "transition_count": transitions,
        "average_confidence": total_confidence / total_events,
        "trend_direction": trend_direction,
        "sample_size": total_events
    }

@app.route('/api/emotion-analytics')
def emotion_analytics():
    """
    API endpoint to retrieve emotion analytics and trends.

    Returns JSON with comprehensive emotion analysis including:
    - Recent emotion trends
    - Historical patterns
    - Session statistics
    """
    time_window = request.args.get('window', default=60, type=int)
    trends = get_emotion_trends(time_window_minutes=time_window)

    return jsonify({
        "status": "success",
        "analytics": trends,
        "total_events": len(emotion_history)
    })

@app.route('/api/emotion-history')
def get_emotion_history_api():
    """
    API endpoint to retrieve raw emotion history data.

    Returns the complete emotion detection history with optional filtering
    by time range or session.
    """
    limit = request.args.get('limit', default=50, type=int)
    return jsonify({
        "status": "success",
        "history": emotion_history[-limit:],
        "total_count": len(emotion_history)
    })

if __name__ == '__main__':
    app.run(debug=True)
