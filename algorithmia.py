import Algorithmia
import json
import pickle
import random
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt, mpld3
from matplotlib import colors
import matplotlib.patches as mpatches
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global emotion history storage
emot_list = list()

class EmotionType(Enum):
    """Enumeration of supported emotion types"""
    ANGRY = "Angry"
    NEUTRAL = "Neutral"
    HAPPY = "Happy"
    SAD = "Sad"
    SURPRISE = "Surprise"
    DISGUST = "Disgust"
    FEAR = "Fear"

@dataclass
class EmotionResult:
    """Data class for emotion detection results"""
    emotion: EmotionType
    confidence: float
    all_emotions: Dict[str, float]
    color_code: int

def _get_emotion_color_mapping() -> Dict[str, int]:
    """
    Get the color code mapping for emotions.

    Returns:
        Dictionary mapping emotion names to color codes
    """
    return {
        'Neutral': 11,
        'Sad': 31,
        'Disgust': 51,
        'Fear': 61,
        'Surprise': 41,
        'Happy': 21,
        'Angry': 1
    }

def _call_emotion_api(image_path: str = "snapshots/pic.png") -> Dict:
    """
    Make API call to emotion recognition service.

    Args:
        image_path: Path to the image file

    Returns:
        API response dictionary

    Raises:
        FileNotFoundError: If image file doesn't exist
        RuntimeError: If API call fails
    """
    try:
        with open(image_path, "rb") as img_file:
            input_data = bytearray(img_file.read())

        client = Algorithmia.client('api-key')
        algo = client.algo('deeplearning/EmotionRecognitionCNNMBP/1.0.1')
        result = algo.pipe(input_data).result

        return result
    except FileNotFoundError as e:
        logger.error(f"Image file not found: {image_path}")
        raise
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        raise RuntimeError(f"Emotion recognition API failed: {str(e)}")

def _parse_emotion_results(api_response: Dict) -> EmotionResult:
    """
    Parse API response and extract emotion information.

    Args:
        api_response: Raw API response

    Returns:
        EmotionResult object with parsed data
    """
    results = api_response.get("results", [])

    # Handle no detection case
    if not results:
        logger.info("No emotions detected, defaulting to Neutral")
        color_mapping = _get_emotion_color_mapping()
        return EmotionResult(
            emotion=EmotionType.NEUTRAL,
            confidence=1.0,
            all_emotions={"Neutral": 1.0},
            color_code=color_mapping['Neutral']
        )

    # Extract emotion confidences
    emotions_data = results[0].get("emotions", [])
    emotion_scores = {}

    for emotion_item in emotions_data:
        label = str(emotion_item["label"])
        confidence = float(emotion_item["confidence"])
        emotion_scores[label] = confidence

    # Find dominant emotion
    if not emotion_scores:
        dominant_emotion = "Neutral"
        confidence_score = 1.0
    else:
        dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
        confidence_score = emotion_scores[dominant_emotion]

    # Get color code
    color_mapping = _get_emotion_color_mapping()
    color_code = color_mapping.get(dominant_emotion, 11)  # Default to neutral color

    # Store in history
    global emot_list
    emot_list.append(color_code)
    logger.info(f"Detected emotion: {dominant_emotion} (confidence: {confidence_score:.2f})")
    logger.debug(f"Emotion history: {emot_list}")

    # Map to enum
    try:
        emotion_enum = EmotionType(dominant_emotion)
    except ValueError:
        emotion_enum = EmotionType.NEUTRAL

    return EmotionResult(
        emotion=emotion_enum,
        confidence=confidence_score,
        all_emotions=emotion_scores,
        color_code=color_code
    )

def get_emotion(image_path: str = "snapshots/pic.png") -> str:
    """
    Detect emotion from facial expression in image.

    This function uses deep learning to analyze facial expressions and
    identify the dominant emotion. Results are stored in global history
    for trend analysis.

    Args:
        image_path: Path to image file containing face (default: snapshots/pic.png)

    Returns:
        String name of detected emotion (e.g., 'Happy', 'Sad', 'Neutral')

    Raises:
        FileNotFoundError: If image file doesn't exist
        RuntimeError: If emotion detection fails
    """
    logger.info(f"Getting emotion from: {image_path}")

    try:
        # Call API
        api_response = _call_emotion_api(image_path)

        # Parse results
        emotion_result = _parse_emotion_results(api_response)

        # Return emotion name
        return emotion_result.emotion.value

    except Exception as e:
        logger.error(f"Error in emotion detection: {str(e)}")
        # Return neutral on error
        return EmotionType.NEUTRAL.value

def get_emotion_detailed(image_path: str = "snapshots/pic.png") -> EmotionResult:
    """
    Get detailed emotion detection results including all confidence scores.

    Args:
        image_path: Path to image file

    Returns:
        EmotionResult with full detection data
    """
    api_response = _call_emotion_api(image_path)
    return _parse_emotion_results(api_response)

@dataclass
class MusicCluster:
    """Configuration for music cluster selection"""
    cluster_id: int
    count: int
    mood_category: str

class PlaylistGenerator:
    """
    Advanced playlist generation based on detected emotions.

    This class handles the complex logic of mapping emotions to music clusters
    and generating personalized playlists.
    """

    # Song database configuration
    SONG_CLUSTERS = {
        1: (1, 170),
        2: (171, 334),
        3: (335, 549),
        4: (550, 740),
        5: (741, 903)
    }

    # Emotion to cluster mapping with weights
    EMOTION_CLUSTER_MAPPING = {
        "Angry": [
            MusicCluster(5, 2, "intense"),
            MusicCluster(3, 7, "energetic"),
            MusicCluster(2, 12, "powerful")
        ],
        "Fear": [
            MusicCluster(5, 2, "intense"),
            MusicCluster(3, 7, "dark"),
            MusicCluster(2, 12, "atmospheric")
        ],
        "Sad": [
            MusicCluster(3, 4, "melancholy"),
            MusicCluster(4, 4, "reflective"),
            MusicCluster(2, 13, "soothing")
        ],
        "Neutral": [
            MusicCluster(3, 2, "balanced"),
            MusicCluster(4, 5, "moderate"),
            MusicCluster(2, 7, "ambient"),
            MusicCluster(1, 5, "light")
        ],
        "Disgust": [
            MusicCluster(3, 2, "edgy"),
            MusicCluster(4, 5, "alternative"),
            MusicCluster(2, 7, "experimental"),
            MusicCluster(1, 5, "unusual")
        ],
        "Surprise": [
            MusicCluster(3, 2, "dynamic"),
            MusicCluster(4, 5, "upbeat"),
            MusicCluster(2, 7, "varied"),
            MusicCluster(1, 5, "exciting")
        ],
        "Happy": [
            MusicCluster(2, 10, "joyful"),
            MusicCluster(4, 5, "uplifting"),
            MusicCluster(1, 6, "cheerful")
        ]
    }

    def __init__(self, song_database_path: str = "test.txt"):
        """
        Initialize playlist generator.

        Args:
            song_database_path: Path to pickled song database
        """
        self.song_database_path = song_database_path
        self._song_names = None

    def _load_song_database(self) -> Dict[int, str]:
        """
        Load song names from database file.

        Returns:
            Dictionary mapping song IDs to names

        Raises:
            FileNotFoundError: If database file doesn't exist
        """
        if self._song_names is None:
            try:
                with open(self.song_database_path, "rb") as fp:
                    self._song_names = pickle.load(fp, encoding='latin1')
                logger.info(f"Loaded {len(self._song_names)} songs from database")
            except FileNotFoundError:
                logger.error(f"Song database not found: {self.song_database_path}")
                raise

        return self._song_names

    def _select_song_from_cluster(self, cluster_id: int) -> Tuple[int, str]:
        """
        Select a random song from specified cluster.

        Args:
            cluster_id: ID of the music cluster

        Returns:
            Tuple of (song_id, formatted_song_name)
        """
        song_names = self._load_song_database()
        cluster_range = self.SONG_CLUSTERS[cluster_id]

        song_id = random.randint(cluster_range[0], cluster_range[1])
        song_name = song_names[song_id]
        formatted_name = f"{str(song_id).zfill(3)}.mp3_{song_name}"

        return song_id, formatted_name

    def generate_playlist(self, emotion: str, shuffle: bool = True) -> List[str]:
        """
        Generate a playlist based on detected emotion.

        Args:
            emotion: Detected emotion string
            shuffle: Whether to shuffle the final playlist

        Returns:
            List of song filenames

        Raises:
            ValueError: If emotion is not recognized
        """
        logger.info(f"Generating playlist for emotion: {emotion}")

        # Get cluster configuration for this emotion
        if emotion not in self.EMOTION_CLUSTER_MAPPING:
            logger.warning(f"Unknown emotion: {emotion}, using Neutral")
            emotion = "Neutral"

        cluster_config = self.EMOTION_CLUSTER_MAPPING[emotion]

        # Build playlist
        playlist = []
        for music_cluster in cluster_config:
            logger.debug(f"Adding {music_cluster.count} songs from cluster {music_cluster.cluster_id} ({music_cluster.mood_category})")

            for _ in range(music_cluster.count):
                _, formatted_song = self._select_song_from_cluster(music_cluster.cluster_id)
                playlist.append(formatted_song)

        # Optional shuffle
        if shuffle:
            random.shuffle(playlist)

        logger.info(f"Generated playlist with {len(playlist)} songs")
        return playlist

def get_playlist(shuffle: bool = True) -> List[str]:
    """
    Generate a music playlist based on current detected emotion.

    This function detects the user's emotion from a facial image and creates
    a personalized playlist that matches their emotional state. Uses sophisticated
    clustering algorithms to map emotions to music categories.

    Args:
        shuffle: Whether to shuffle the playlist (default: True)

    Returns:
        List of song filenames (format: "###.mp3_songname")

    Raises:
        FileNotFoundError: If required files (image/database) don't exist
        RuntimeError: If emotion detection or playlist generation fails

    Example:
        >>> playlist = get_playlist()
        >>> print(f"Generated {len(playlist)} songs")
        Generated 21 songs
    """
    try:
        # Detect current emotion
        current_emotion = get_emotion()

        # Generate playlist
        generator = PlaylistGenerator()
        playlist = generator.generate_playlist(current_emotion, shuffle=shuffle)

        return playlist

    except Exception as e:
        logger.error(f"Playlist generation failed: {str(e)}")
        raise RuntimeError(f"Failed to generate playlist: {str(e)}")
    
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
    
    fig, ax = plt.subplots()
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

    plt.legend(handles=[red_patch, blue_patch, yellow_patch, green_patch, cyan_patch, magenta_patch, black_patch])
    #save image
    plt.savefig("static/graph.jpg")
    plt.show()

def clear_emotion_history():
    global emot_list
    emot_list = []
    return len(emot_list)

def get_emotion_count():
    return len(emot_list)

def get_last_emotion():
    if emot_list:
        emotion_reverse_map = {1: 'Angry', 11: 'Neutral', 21: 'Happy', 31: 'Sad', 41: 'Surprise', 51: 'Disgust', 61: 'Fear'}
        return emotion_reverse_map.get(emot_list[-1], 'Unknown')
    return None
