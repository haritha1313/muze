# muze
Online Music Therapist

## Requirements

|Library|Version|
|-------|-------|
|Algorithmia||
|Flask|`0.12.2`|
|hsaudiotag|`1.1.1`|
|Jinja2|`2.10`|
|Matplotlib|`2.1.2`|
|NumPy|`1.14.0`|
|Pillow|`5.0.0`|
|simplejson|`3.13.2`|
|six|`1.11.0`|
|urllib3|`1.22`|
|Werkzeug|`0.14.1`|

## Data credits
- http://www.music-ir.org/mirex/wiki/2007:Audio_Music_Mood_Classification

## Setup
Edit line 17 in `algorithmia.py` and add your Algorithmia API key:

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
