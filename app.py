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

if __name__ == '__main__':
    app.run(debug=True)
