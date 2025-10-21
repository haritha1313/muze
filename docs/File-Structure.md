# File Structure

## Project Organization

```
muze/
├── .git/                           # Git version control
├── .github/                        # GitHub configuration
│   └── workflows/
│       └── doc-analysis.yml        # CI/CD workflow for documentation
├── docs/                           # Documentation wiki (this directory)
│   ├── README.md                   # Documentation index
│   ├── Overview.md                 # Project overview
│   ├── Architecture.md             # System architecture
│   ├── API-Reference.md            # API documentation
│   ├── Data-Flow.md                # Data flow diagrams
│   ├── Emotion-Detection.md        # Emotion detection details
│   ├── Music-Classification.md     # Music system details
│   ├── Frontend.md                 # Frontend documentation
│   ├── Installation.md             # Setup instructions
│   ├── Quick-Start.md              # Quick start guide
│   ├── File-Structure.md           # This file
│   ├── Configuration.md            # Configuration guide
│   ├── CI-CD.md                    # CI/CD documentation
│   ├── Troubleshooting.md          # Problem solving
│   ├── Contributing.md             # Contribution guidelines
│   └── Data-Sources.md             # Data credits
├── scripts/                        # Utility scripts
│   └── update_docs.py              # Auto-documentation generator
├── snapshots/                      # Temporary webcam captures
│   └── pic.png                     # Latest snapshot (overwritten)
├── static/                         # Static assets
│   ├── music/                      # Audio files
│   │   ├── 001.mp3                 # Song 1
│   │   ├── 002.mp3                 # Song 2
│   │   └── ...                     # Songs 3-903
│   ├── graph.jpg                   # Generated emotion visualization
│   └── jquery-1.7.1.min.js         # jQuery library
├── templates/                      # Jinja2 HTML templates
│   ├── base.html                   # Base template
│   ├── musi.html                   # Main music player
│   ├── init.html                   # Webcam test page
│   ├── index.html                  # Landing page
│   ├── trial.html                  # Development page
│   ├── showgraph.html              # Graph display
│   └── styling.css                 # CSS styles
├── __pycache__/                    # Python bytecode cache
├── app.py                          # Flask application (main entry)
├── algorithmia.py                  # Emotion detection & playlist logic
├── test.txt                        # Song database (pickled list)
├── LICENSE                         # License file
├── README.md                       # Project README
└── Plutchik-Model-600.png          # Emotion wheel reference image
```

---

## Core Files

### app.py

**Purpose**: Main Flask application entry point

**Size**: ~1 KB

**Key Components**:
- Flask app initialization
- Route definitions (`/`, `/hook`, `/graph`)
- Image processing logic
- Server configuration

**Dependencies**:
- `flask`
- `algorithmia` (local module)
- `PIL` (Pillow)
- `base64`, `re`, `io`

**Routes**:
```python
@app.route('/')              # Main page
@app.route('/hook')          # Snapshot upload
@app.route('/graph')         # Emotion visualization
```

---

### algorithmia.py

**Purpose**: Emotion detection and playlist generation

**Size**: ~3.5 KB

**Key Functions**:
- `get_emotion()` - Detect emotion from snapshot
- `get_playlist()` - Generate personalized playlist
- `get_emotion_grid()` - Create emotion visualization

**External Dependencies**:
- Algorithmia API
- `test.txt` song database

**Global Variables**:
- `emot_list` - Emotion history tracker

---

### test.txt

**Purpose**: Song database

**Format**: Pickled Python list (Python 2 protocol)

**Size**: ~37 KB

**Contents**: 903 song entries

**Structure**:
```python
["Song Name - Artist", ...]
```

**Encoding**: Latin-1

**Loading**:
```python
with open("test.txt", "rb") as fp:
    songnames = pickle.load(fp, encoding='latin1')
```

---

## Template Files

### templates/base.html

**Purpose**: Base template for inheritance

**Size**: ~361 bytes

**Features**:
- Common HTML structure
- jQuery inclusion
- CSS stylesheet link
- Content block definition

**Used By**: Other templates via `{% extends "base.html" %}`

---

### templates/musi.html

**Purpose**: Main music player interface

**Size**: ~3.5 KB

**Features**:
- Webcam capture
- Audio playback
- Playlist management
- User controls

**Template Variables**:
- `songs` - Playlist array from backend

**JavaScript**:
- WebRTC setup
- Snapshot capture
- Audio event handlers
- AJAX communication

---

### templates/init.html

**Purpose**: Webcam initialization test page

**Size**: ~2 KB

**Use Case**: Testing webcam functionality

**Features**:
- Basic webcam setup
- Snapshot capture
- Minimal UI

---

### templates/index.html

**Purpose**: Simple landing page

**Size**: ~61 bytes

**Content**: Minimal placeholder

---

### templates/trial.html

**Purpose**: Development/testing page

**Size**: ~2.3 KB

**Use Case**: Experimental features

---

### templates/showgraph.html

**Purpose**: Display emotion graph

**Size**: ~137 bytes

**Content**: Image display for `static/graph.jpg`

---

### templates/styling.css

**Purpose**: CSS styles

**Size**: ~967 bytes

**Styles**: UI components, layout, colors

---

## Static Assets

### static/music/

**Purpose**: Audio file storage

**File Count**: 903 MP3 files

**Naming**: `001.mp3` to `903.mp3` (zero-padded)

**Total Size**: ~2-3 GB (estimated)

**Format**: MP3 audio

**Access**: Served directly by Flask

**URL Pattern**: `/static/music/XXX.mp3`

---

### static/jquery-1.7.1.min.js

**Purpose**: jQuery library

**Version**: 1.7.1 (legacy)

**Size**: ~93 KB (minified)

**Usage**: AJAX, DOM manipulation, event handling

**Note**: Consider upgrading to latest version

---

### static/graph.jpg

**Purpose**: Emotion history visualization

**Generated By**: `get_emotion_grid()` function

**Size**: ~50-100 KB

**Format**: JPEG image

**Dimensions**: Variable (matplotlib default)

**Lifecycle**: Overwritten each time graph is generated

---

## Temporary Files

### snapshots/pic.png

**Purpose**: Latest webcam snapshot

**Size**: ~50-150 KB

**Format**: RGB PNG (400×350)

**Lifecycle**: 
- Created on snapshot capture
- Overwritten on next capture
- Not persisted long-term

**Privacy**: Contains user's facial image

---

## Configuration Files

### .github/workflows/doc-analysis.yml

**Purpose**: GitHub Actions workflow

**Triggers**: Pull requests (opened, synchronized, reopened)

**Actions**:
1. Checkout code
2. Setup Python 3.11
3. Install dependencies
4. Run analysis script

**Environment Variables**:
- `GITHUB_TOKEN`
- `PR_NUMBER`
- `REPO`
- `BASE_SHA`
- `HEAD_SHA`

---

## Utility Scripts

### scripts/update_docs.py

**Purpose**: Auto-generate documentation

**Size**: ~2 KB

**Features**:
- Analyze undocumented functions
- Generate doc templates
- Commit to repository

**Dependencies**:
- `analyze_pr.py` (referenced but not present)

**Usage**: Called by CI/CD pipeline

---

## Generated Files

### __pycache__/

**Purpose**: Python bytecode cache

**Contents**: `.pyc` files

**Generated By**: Python interpreter

**Safe to Delete**: Yes (regenerated automatically)

**Ignore in Git**: Yes

---

## Missing/Optional Files

### requirements.txt

**Status**: Not present (should be created)

**Purpose**: Python dependency list

**Recommended Content**:
```txt
Flask==0.12.2
Algorithmia>=1.0.0
Pillow==5.0.0
numpy==1.14.0
matplotlib==2.1.2
Jinja2==2.10
```

---

### .env

**Status**: Not present (should be created)

**Purpose**: Environment variables

**Recommended Content**:
```bash
ALGORITHMIA_API_KEY=your_key_here
FLASK_SECRET_KEY=your_secret_here
FLASK_ENV=development
```

---

### .gitignore

**Status**: May not be comprehensive

**Recommended Content**:
```
__pycache__/
*.pyc
*.pyo
.env
snapshots/*.png
static/graph.jpg
venv/
.DS_Store
```

---

## File Permissions

### Required Permissions

| Path | Read | Write | Execute |
|------|------|-------|---------|
| `app.py` | ✅ | ❌ | ✅ |
| `algorithmia.py` | ✅ | ❌ | ❌ |
| `test.txt` | ✅ | ❌ | ❌ |
| `templates/` | ✅ | ❌ | ❌ |
| `static/music/` | ✅ | ❌ | ❌ |
| `snapshots/` | ✅ | ✅ | ✅ |
| `static/graph.jpg` | ✅ | ✅ | ❌ |

---

## Storage Requirements

### Minimum Disk Space

| Component | Size |
|-----------|------|
| Python code | ~10 KB |
| Templates | ~10 KB |
| Song database | ~40 KB |
| Music files | ~2-3 GB |
| Dependencies | ~100 MB |
| **Total** | **~2.5-3.5 GB** |

### Runtime Storage

| Component | Size |
|-----------|------|
| Snapshots | ~150 KB |
| Graph images | ~100 KB |
| Logs | Variable |
| Cache | ~10 MB |

---

## File Dependencies

### Dependency Graph

```
app.py
├── algorithmia.py
│   ├── test.txt
│   └── snapshots/pic.png
├── templates/musi.html
│   ├── templates/base.html
│   └── static/jquery-1.7.1.min.js
└── static/music/*.mp3

algorithmia.py
├── test.txt
├── snapshots/pic.png
└── static/graph.jpg (output)
```

---

## Import Structure

### app.py Imports

```python
import flask
from flask import request
from algorithmia import get_playlist, get_emotion_grid
import numpy as np
from PIL import Image
import re
from io import BytesIO
import base64
```

### algorithmia.py Imports

```python
import Algorithmia
import json
import pickle
import random
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import mpld3
from matplotlib import colors
import matplotlib.patches as mpatches
```

---

## File Naming Conventions

### Python Files
- **Snake_case**: `algorithmia.py`, `update_docs.py`
- **Lowercase**: All Python modules

### Template Files
- **Lowercase**: `musi.html`, `base.html`
- **Descriptive**: Names indicate purpose

### Music Files
- **Zero-padded numbers**: `001.mp3`, `045.mp3`, `903.mp3`
- **Three digits**: Consistent width

### Image Files
- **Lowercase**: `graph.jpg`, `pic.png`
- **Descriptive**: Purpose clear from name

---

## Backup Recommendations

### Critical Files (Must Backup)
- `app.py`
- `algorithmia.py`
- `test.txt`
- `templates/`
- `static/music/` (if custom)

### Generated Files (Don't Backup)
- `__pycache__/`
- `snapshots/pic.png`
- `static/graph.jpg`

### Configuration Files (Backup Separately)
- `.env` (if created)
- API keys (secure storage)

---

## Development vs Production

### Development Files
- `templates/trial.html`
- `templates/init.html`
- `scripts/update_docs.py`
- Debug logs

### Production Files
- `app.py`
- `algorithmia.py`
- `templates/musi.html`
- `static/`
- `test.txt`

### Excluded in Production
- `.git/`
- `__pycache__/`
- Development templates
- Test scripts
- Documentation source

---

## File Modification Frequency

| File | Frequency | Reason |
|------|-----------|--------|
| `snapshots/pic.png` | Every 20 songs | Emotion rechecks |
| `static/graph.jpg` | On demand | User requests report |
| `app.py` | Rarely | Code updates |
| `algorithmia.py` | Rarely | Algorithm changes |
| `test.txt` | Never | Static database |
| `templates/` | Rarely | UI updates |
| `static/music/` | Never | Static library |

---

## Security Considerations

### Sensitive Files
- `algorithmia.py` (contains API key)
- `.env` (if created)
- `snapshots/pic.png` (user images)

### Public Files
- `templates/`
- `static/music/`
- `README.md`

### Recommendations
- Never commit API keys
- Add `.env` to `.gitignore`
- Clear snapshots periodically
- Use environment variables for secrets
