import Algorithmia
import json
import pickle
import random
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt, mpld3
from matplotlib import colors
import matplotlib.patches as mpatches

emot_list= list()

def get_emotion():
    print("Getting emotion...")
    # API call
    input = bytearray(open("snapshots/pic.png", "rb").read())
    client = Algorithmia.client('api-key')
    algo = client.algo('deeplearning/EmotionRecognitionCNNMBP/1.0.1')
    op = (algo.pipe(input).result)["results"]

    # Returned from API call
    
    if(op==[]):
        current = "Neutral"
    else:
        emotion = ((op[0])["emotions"])
        analyze = dict()

        for emo in emotion:
            analyze[str(emo["label"])] = float(emo["confidence"])
        current = max(analyze, key=analyze.get)

	# Color code emotions
        emotion_color_dict = {'Neutral':11 , 'Sad':31 , 'Disgust':51 , 'Fear':61 , 'Surprise':41, 'Happy':21, 'Angry':1}
        emot_list.append(emotion_color_dict[current])
        print(emot_list)

    return current

def get_playlist():
    current = get_emotion()
    #get playlist from emotion

    with open("test.txt", "rb") as fp:
        songnames = pickle.load(fp, encoding='latin1')
    songlist = {1: [1,170], 2:[171,334], 3:[335,549], 4:[550, 740], 5:[741,903]}
    if ((current == "Anger") | (current == "Fear")):
        cluster_def = [[5, 2], [3, 7], [2, 12]]
    elif(current == "Sad"):
        cluster_def = [[3, 4], [4, 4], [2, 13]]
    elif((current == "Neutral") | (current == "Disgust") | (current == "Surprise")):
        cluster_def = [[3, 2], [4, 5], [2, 7], [1, 5]]
    else:
        cluster_def = [[2, 10], [4, 5], [1, 6]]
    
    playlist = list()
    for sets in cluster_def:
        for i in range(sets[1]):
            ss = random.randint(songlist[sets[0]][0], songlist[sets[0]][1]);
            playlist.append(str(ss).zfill(3)+".mp3_"+songnames[ss]);
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
