import flask, flask.views
from flask import request
from algorithmia import get_playlist
from algorithmia import get_emotion_grid
import numpy as np
from PIL import Image
import re
from io import BytesIO
import base64

app = flask.Flask(__name__)
app.secret_key = "bacon"

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

if __name__ == '__main__':
    app.run(debug=True)
