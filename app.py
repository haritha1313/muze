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

def get_snapshot_size():
    import os
    if os.path.exists("snapshots/pic.png"):
        return os.path.getsize("snapshots/pic.png")
    return 0

if __name__ == '__main__':
    app.run(debug=True)
