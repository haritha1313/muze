import Algorithmia
import json
import pickle
import random
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt, mpld3
from matplotlib import colors
import matplotlib.patches as mpatches
from collections import deque
from datetime import datetime
import math

# Store emotion history with timestamps and confidence scores
emot_list = list()
emotion_history = deque(maxlen=10)  # Rolling window for smoothing
emotion_weights = {'Angry': 1.2, 'Fear': 1.1, 'Sad': 0.9, 'Happy': 1.0, 'Neutral': 0.8, 'Disgust': 1.0, 'Surprise': 0.95}

def calculate_weighted_emotion(emotions_dict):
    """Apply weighted scoring to emotion confidences"""
    weighted_scores = {}
    for emotion, confidence in emotions_dict.items():
        weight = emotion_weights.get(emotion, 1.0)
        # Apply exponential scaling for more dramatic differences
        weighted_scores[emotion] = (confidence ** 1.5) * weight
    return weighted_scores

def smooth_emotion_with_history(current_emotion, current_confidence):
    """Smooth emotion detection using historical data"""
    emotion_history.append({'emotion': current_emotion, 'confidence': current_confidence, 'timestamp': datetime.now()})

    if len(emotion_history) < 3:
        return current_emotion

    # Calculate weighted average based on recency and confidence
    emotion_scores = {}
    total_weight = 0

    for idx, entry in enumerate(emotion_history):
        # More recent emotions have higher weight
        recency_weight = (idx + 1) / len(emotion_history)
        confidence_weight = entry['confidence']
        combined_weight = recency_weight * confidence_weight

        emo = entry['emotion']
        emotion_scores[emo] = emotion_scores.get(emo, 0) + combined_weight
        total_weight += combined_weight

    # Normalize scores
    for emo in emotion_scores:
        emotion_scores[emo] /= total_weight

    # Only switch emotion if new emotion has significantly higher score
    if current_emotion in emotion_scores and emotion_scores[current_emotion] < 0.3:
        return max(emotion_scores, key=emotion_scores.get)
    return current_emotion

def get_emotion():
    print("Getting emotion with advanced weighted analysis...")
    # API call
    input = bytearray(open("snapshots/pic.png", "rb").read())
    client = Algorithmia.client('api-key')
    algo = client.algo('deeplearning/EmotionRecognitionCNNMBP/1.0.1')
    op = (algo.pipe(input).result)["results"]

    if(op==[]):
        current = "Neutral"
        confidence = 0.5
    else:
        emotion = ((op[0])["emotions"])
        analyze = dict()

        for emo in emotion:
            analyze[str(emo["label"])] = float(emo["confidence"])

        # Apply weighted scoring instead of simple max
        weighted_scores = calculate_weighted_emotion(analyze)
        current = max(weighted_scores, key=weighted_scores.get)
        confidence = analyze[current]

        # Apply smoothing algorithm
        current = smooth_emotion_with_history(current, confidence)

        # Color code emotions
        emotion_color_dict = {'Neutral':11 , 'Sad':31 , 'Disgust':51 , 'Fear':61 , 'Surprise':41, 'Happy':21, 'Angry':1}
        emot_list.append(emotion_color_dict[current])
        print(f"Detected: {current} (confidence: {confidence:.2f}, weighted)")
        print(emot_list)

    return current

def calculate_cluster_distribution(emotion, intensity=1.0):
    """Dynamically calculate cluster distribution based on emotion and intensity"""
    # Base cluster weights for different emotions (cluster_id: weight)
    emotion_profiles = {
        'Angry': {5: 0.5, 3: 0.3, 1: 0.2},
        'Fear': {5: 0.4, 3: 0.4, 2: 0.2},
        'Sad': {3: 0.4, 4: 0.35, 2: 0.25},
        'Neutral': {3: 0.3, 4: 0.25, 2: 0.25, 1: 0.2},
        'Disgust': {3: 0.35, 4: 0.3, 2: 0.25, 1: 0.1},
        'Surprise': {4: 0.4, 2: 0.3, 1: 0.3},
        'Happy': {2: 0.4, 4: 0.35, 1: 0.25}
    }

    profile = emotion_profiles.get(emotion, emotion_profiles['Neutral'])

    # Adjust distribution based on intensity
    adjusted_profile = {}
    for cluster, weight in profile.items():
        adjusted_profile[cluster] = weight * (0.7 + 0.6 * intensity)

    # Normalize
    total = sum(adjusted_profile.values())
    return {k: v/total for k, v in adjusted_profile.items()}

def probabilistic_song_selection(cluster_range, num_songs, diversity_factor=0.3):
    """Select songs using probability distribution to avoid repetition"""
    songs = []
    used_songs = set()

    # Create probability distribution favoring middle of range
    mid_point = (cluster_range[0] + cluster_range[1]) / 2
    range_span = cluster_range[1] - cluster_range[0]

    for _ in range(num_songs):
        attempts = 0
        while attempts < 50:
            # Use normal distribution centered at midpoint
            if random.random() < diversity_factor:
                # Sometimes pick uniformly for diversity
                song_id = random.randint(cluster_range[0], cluster_range[1])
            else:
                # Usually pick from gaussian distribution
                std_dev = range_span / 4
                song_id = int(random.gauss(mid_point, std_dev))
                song_id = max(cluster_range[0], min(cluster_range[1], song_id))

            if song_id not in used_songs:
                used_songs.add(song_id)
                songs.append(song_id)
                break
            attempts += 1

        if attempts >= 50:
            # Fallback to random if can't find unique
            song_id = random.randint(cluster_range[0], cluster_range[1])
            songs.append(song_id)

    return songs

def get_playlist():
    current = get_emotion()

    with open("test.txt", "rb") as fp:
        songnames = pickle.load(fp, encoding='latin1')

    songlist = {1: [1,170], 2:[171,334], 3:[335,549], 4:[550, 740], 5:[741,903]}

    # Calculate emotion intensity from history
    intensity = 1.0
    if len(emotion_history) >= 3:
        recent_emotions = [e['emotion'] for e in list(emotion_history)[-3:]]
        if recent_emotions.count(current) == 3:
            intensity = 1.3  # High intensity if same emotion persists
        else:
            intensity = 0.8  # Lower intensity if emotions are mixed

    # Get dynamic cluster distribution
    cluster_dist = calculate_cluster_distribution(current, intensity)

    # Calculate total songs (variable based on emotion intensity)
    base_songs = 20
    total_songs = int(base_songs * (0.8 + 0.4 * intensity))

    # Distribute songs across clusters based on weights
    playlist = list()
    for cluster_id, weight in cluster_dist.items():
        num_songs = max(1, int(total_songs * weight))
        song_ids = probabilistic_song_selection(songlist[cluster_id], num_songs)

        for song_id in song_ids:
            playlist.append(str(song_id).zfill(3) + ".mp3_" + songnames[song_id])

    # Shuffle to mix clusters
    random.shuffle(playlist)

    print(f"Generated playlist: {len(playlist)} songs for {current} (intensity: {intensity:.2f})")
    return playlist
    
def get_emotion_grid():
    data = np.full((5,10), 81)
    a = 0

    #color according to emotion
    for i in range(0,5):
        for q in range(0,10):
            if(a == len(emot_list)):
                break
            print(i, q, a)
            data[i,q] = emot_list[a]
            a = a+1

    cmap = colors.ListedColormap(['red', 'blue', 'yellow', 'green', 'cyan', 'magenta', 'black', 'white'])
    bounds = [0,10,20,30,40,50,60]
    norm = colors.BoundaryNorm(bounds, cmap.N)

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.imshow(data, cmap=cmap, norm=norm)

    # draw gridlines
    ax.grid(which='major', axis='both', linestyle='-', color='k', linewidth=2)
    ax.set_xticks(np.arange(-.5, 10, 1));
    ax.set_yticks(np.arange(-.5, 10, 1));

    #add legend
    red_patch = mpatches.Patch(color='red', label='Angry')
    blue_patch = mpatches.Patch(color='blue', label='Neutral')
    yellow_patch = mpatches.Patch(color='yellow', label='Happy')
    green_patch = mpatches.Patch(color='green', label='Sad')
    cyan_patch = mpatches.Patch(color='cyan', label='Surprise')
    magenta_patch = mpatches.Patch(color='magenta', label='Disgust')
    black_patch = mpatches.Patch(color='black', label='Fear')

    plt.legend(handles=[red_patch, blue_patch, yellow_patch, green_patch, cyan_patch, magenta_patch, black_patch],
               loc='upper left', bbox_to_anchor=(1.05, 1))

    # Add trend analysis as title if available
    if len(emotion_history) >= 3:
        trend_info = analyze_emotion_trend()
        profile = get_dominant_emotion_profile()

        title = f"Emotion History Grid\n"
        title += f"Trend: {trend_info['trend']} | Volatility: {trend_info['volatility']} | "
        title += f"Predicted: {trend_info['prediction']}\n"

        if profile:
            dominant = list(profile.keys())[0]
            title += f"Dominant: {dominant} ({profile[dominant]['percentage']}%)"

        plt.title(title, fontsize=10, pad=20)
    else:
        plt.title("Emotion History Grid", fontsize=12, pad=20)

    #save image
    plt.tight_layout()
    plt.savefig("static/graph.jpg", dpi=150, bbox_inches='tight')
    plt.show()
    print(f"Emotion grid saved with {len(emot_list)} recorded emotions")

def analyze_emotion_trend():
    """Analyze emotion trends over time and predict next likely emotion"""
    if len(emotion_history) < 3:
        return {'trend': 'insufficient_data', 'prediction': None, 'volatility': 0}

    emotions = [e['emotion'] for e in emotion_history]
    confidences = [e['confidence'] for e in emotion_history]

    # Calculate volatility (how much emotions are changing)
    unique_emotions = len(set(emotions))
    volatility = unique_emotions / len(emotions)

    # Detect trend patterns
    if unique_emotions == 1:
        trend = 'stable'
        prediction = emotions[0]
    elif emotions[-1] == emotions[-2] == emotions[-3]:
        trend = 'stabilizing'
        prediction = emotions[-1]
    else:
        trend = 'volatile'
        # Predict based on most frequent recent emotion
        recent = list(emotion_history)[-5:]
        emotion_counts = {}
        for e in recent:
            emotion_counts[e['emotion']] = emotion_counts.get(e['emotion'], 0) + 1
        prediction = max(emotion_counts, key=emotion_counts.get)

    # Calculate confidence trend (improving or degrading)
    if len(confidences) >= 5:
        early_avg = sum(confidences[:len(confidences)//2]) / (len(confidences)//2)
        late_avg = sum(confidences[len(confidences)//2:]) / (len(confidences) - len(confidences)//2)
        confidence_trend = 'improving' if late_avg > early_avg else 'degrading'
    else:
        confidence_trend = 'stable'

    return {
        'trend': trend,
        'prediction': prediction,
        'volatility': round(volatility, 2),
        'confidence_trend': confidence_trend,
        'history_length': len(emotion_history)
    }

def get_emotion_transition_matrix():
    """Calculate transition probabilities between emotions"""
    if len(emotion_history) < 2:
        return {}

    transitions = {}
    emotions_list = [e['emotion'] for e in emotion_history]

    for i in range(len(emotions_list) - 1):
        current = emotions_list[i]
        next_emo = emotions_list[i + 1]

        if current not in transitions:
            transitions[current] = {}

        transitions[current][next_emo] = transitions[current].get(next_emo, 0) + 1

    # Normalize to probabilities
    for current, nexts in transitions.items():
        total = sum(nexts.values())
        for next_emo in nexts:
            nexts[next_emo] = round(nexts[next_emo] / total, 2)

    return transitions

def get_dominant_emotion_profile():
    """Get statistical profile of dominant emotions"""
    if not emotion_history:
        return None

    emotion_counts = {}
    total_confidence = {}

    for entry in emotion_history:
        emo = entry['emotion']
        conf = entry['confidence']

        emotion_counts[emo] = emotion_counts.get(emo, 0) + 1
        total_confidence[emo] = total_confidence.get(emo, 0) + conf

    # Calculate averages
    profile = {}
    for emo in emotion_counts:
        profile[emo] = {
            'count': emotion_counts[emo],
            'percentage': round(emotion_counts[emo] / len(emotion_history) * 100, 1),
            'avg_confidence': round(total_confidence[emo] / emotion_counts[emo], 2)
        }

    return dict(sorted(profile.items(), key=lambda x: x[1]['count'], reverse=True))

def clear_emotion_history():
    global emot_list, emotion_history
    emot_list = []
    emotion_history.clear()
    return len(emot_list)

def get_emotion_count():
    return len(emot_list)

def get_last_emotion():
    if emot_list:
        emotion_reverse_map = {1: 'Angry', 11: 'Neutral', 21: 'Happy', 31: 'Sad', 41: 'Surprise', 51: 'Disgust', 61: 'Fear'}
        return emotion_reverse_map.get(emot_list[-1], 'Unknown')
    return None
