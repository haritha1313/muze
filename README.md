# muze
Feeling low? Feeling out of this world? Compliment it with a great selection of music specially tailored for you. Muze is your personal online Music Therapist for all those late night binge listening sessions. Powered by AI, muze uses state of the art machine learning algorithms to choose the best songs that can lift your mood or set it on fire.

## Requirements

|Library|Version|
|-------|-------|
|Algorithmia|[Visit Website](https://algorithmia.com/)|
|Flask|[0.12.2](https://pypi.org/project/Flask/0.12.2/)|
|hsaudiotag|[1.1.1](https://pypi.org/project/hsaudiotag/1.1.1/)|
|Jinja2|[2.10](https://pypi.org/project/Jinja2/)|
|Matplotlib|[2.1.2](https://pypi.org/project/matplotlib/2.1.2/)|
|NumPy|[1.14.0](https://pypi.org/project/numpy/1.14.0/)|
|Pillow|[5.0.0](https://pypi.org/project/Pillow/5.0.0/)|
|simplejson|[3.13.2](https://pypi.org/project/simplejson/3.13.2/)|
|six|[1.11.0](https://pypi.org/project/six/)|
|urllib3|[1.22](https://pypi.org/project/urllib3/1.22/)|
|Werkzeug|[0.14.1](https://pypi.org/project/Werkzeug/)|

## Setup
1. Sign up for an account on Algorithmia website and navigate to `Credentials` section in your profile to get your API key.

2. Replace `api-key` in line 17 of `algorithmia.py` with your Algorithmia API key:

```python
def get_emotion():
...
    client = Algorithmia.client('api-key')
...
```
## How to run
- In your terminal, type `python app.py`
- Visit `http://localhost:5000` in a web browser
- Enjoy the music!
- When the playlist ends, if you want to listen more, click on 'Get more music'

## Data credits
- http://www.music-ir.org/mirex/wiki/2007:Audio_Music_Mood_Classification


## API Reference

## get_last_emotion

Brief description.

**Parameters:**
- ...

**Returns:**
- ...

**Example:**
```python
from algorithmia import get_last_emotion
# get_last_emotion(...)
```
