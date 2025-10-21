# Contributing to Muze

Thank you for your interest in contributing to Muze! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Coding Standards](#coding-standards)
6. [Testing](#testing)
7. [Documentation](#documentation)
8. [Pull Request Process](#pull-request-process)
9. [Issue Guidelines](#issue-guidelines)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, background, or identity.

### Expected Behavior

- Be respectful and considerate
- Welcome newcomers and help them get started
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

---

## Getting Started

### Prerequisites

- Python 2.7 or 3.6+
- Git
- GitHub account
- Algorithmia API key (for testing)

### Fork and Clone

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/muze.git
   cd muze
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/muze.git
   ```

---

## Development Setup

### 1. Create Virtual Environment

```bash
# Python 3
python -m venv venv

# Python 2
virtualenv venv
```

### 2. Activate Virtual Environment

```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists
```

### 4. Configure Environment

Create `.env` file:
```bash
ALGORITHMIA_API_KEY=your_key_here
FLASK_SECRET_KEY=your_secret_here
FLASK_ENV=development
FLASK_DEBUG=True
```

### 5. Verify Setup

```bash
python app.py
# Open http://localhost:5000
```

---

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

**Branch Naming Convention**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Adding tests
- `chore/` - Maintenance tasks

### 2. Make Your Changes

- Write clean, readable code
- Follow existing code style
- Add comments for complex logic
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run the application
python app.py

# Test manually in browser
# Verify all functionality works
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new emotion detection algorithm"
```

**Commit Message Format**:
```
<type>: <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Example**:
```
feat: add support for multiple music libraries

- Added library selection in configuration
- Created separate song databases for different genres
- Updated playlist generation to use selected library

Closes #123
```

---

## Coding Standards

### Python Style Guide

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide:

```python
# Good
def get_emotion():
    """Detect emotion from snapshot image."""
    input_data = bytearray(open("snapshots/pic.png", "rb").read())
    client = Algorithmia.client(api_key)
    return process_result(client.algo().pipe(input_data))

# Bad
def getEmotion():
    inputData=bytearray(open("snapshots/pic.png","rb").read())
    client=Algorithmia.client(api_key)
    return process_result(client.algo().pipe(inputData))
```

### JavaScript Style Guide

```javascript
// Good
function snapshot() {
    const canvas = document.getElementById('myCanvas');
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataURL = canvas.toDataURL('image/png');
    sendToServer(dataURL);
}

// Bad
function snapshot(){
  var canvas=document.getElementById('myCanvas')
  var ctx=canvas.getContext('2d')
  ctx.drawImage(video,0,0,canvas.width,canvas.height)
  var dataURL=canvas.toDataURL('image/png')
  sendToServer(dataURL)
}
```

### Code Organization

```python
# Imports at top
import os
import sys
from flask import Flask, request

# Constants
API_KEY = os.getenv('ALGORITHMIA_API_KEY')
SNAPSHOT_DIR = 'snapshots'

# Functions
def get_emotion():
    """Docstring explaining function."""
    pass

# Main execution
if __name__ == '__main__':
    app.run()
```

---

## Testing

### Manual Testing Checklist

Before submitting a PR, test:

- [ ] Application starts without errors
- [ ] Webcam access works
- [ ] Emotion detection completes successfully
- [ ] Playlist generates correctly
- [ ] Audio playback works
- [ ] All buttons function properly
- [ ] Emotion graph displays
- [ ] No console errors
- [ ] Works in multiple browsers

### Writing Tests

Create test files in `tests/` directory:

```python
# tests/test_algorithmia.py
import unittest
from algorithmia import get_emotion, get_playlist

class TestEmotionDetection(unittest.TestCase):
    
    def test_get_emotion_returns_string(self):
        """Test that get_emotion returns a string."""
        # Setup test image
        # ...
        emotion = get_emotion()
        self.assertIsInstance(emotion, str)
    
    def test_get_playlist_returns_list(self):
        """Test that get_playlist returns a list."""
        playlist = get_playlist()
        self.assertIsInstance(playlist, list)
        self.assertGreater(len(playlist), 0)

if __name__ == '__main__':
    unittest.main()
```

Run tests:
```bash
python -m unittest discover tests/
```

---

## Documentation

### Code Documentation

Add docstrings to all functions:

```python
def get_emotion():
    """
    Detect emotion from webcam snapshot using Algorithmia API.
    
    Reads the image from snapshots/pic.png, sends it to the
    EmotionRecognitionCNNMBP algorithm, and returns the detected
    emotion with highest confidence.
    
    Returns:
        str: Detected emotion name (Happy, Sad, Angry, Fear, 
             Surprise, Disgust, or Neutral)
    
    Raises:
        AlgorithmException: If API call fails
        FileNotFoundError: If snapshot image doesn't exist
    
    Example:
        >>> emotion = get_emotion()
        >>> print(emotion)
        'Happy'
    """
    pass
```

### Update Documentation

When making changes, update relevant docs:

- `README.md` - Project overview
- `docs/` - Detailed documentation
- Inline comments - Complex code sections
- API documentation - New endpoints or functions

---

## Pull Request Process

### 1. Update Your Branch

```bash
git fetch upstream
git rebase upstream/main
```

### 2. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 3. Create Pull Request

1. Go to GitHub repository
2. Click "New Pull Request"
3. Select your branch
4. Fill out PR template

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Code refactoring

## Testing
- [ ] Tested locally
- [ ] All existing features still work
- [ ] Added tests for new functionality

## Screenshots (if applicable)
Add screenshots showing changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added to complex code
- [ ] Documentation updated
- [ ] No new warnings generated
```

### 4. Code Review

- Respond to feedback promptly
- Make requested changes
- Push updates to same branch
- Request re-review when ready

### 5. Merge

Once approved:
- PR will be merged by maintainer
- Your branch can be deleted
- Celebrate your contribution! 🎉

---

## Issue Guidelines

### Before Creating an Issue

1. **Search existing issues** - Check if already reported
2. **Check documentation** - Might be answered there
3. **Try latest version** - Bug might be fixed

### Creating a Good Issue

**Bug Report Template**:
```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Windows 10]
- Python: [e.g., 3.9.5]
- Browser: [e.g., Chrome 91]

## Screenshots
If applicable

## Additional Context
Any other relevant information
```

**Feature Request Template**:
```markdown
## Feature Description
Clear description of proposed feature

## Use Case
Why is this feature needed?

## Proposed Solution
How should it work?

## Alternatives Considered
Other approaches you've thought about

## Additional Context
Any other relevant information
```

---

## Areas for Contribution

### Good First Issues

- Fix typos in documentation
- Add code comments
- Improve error messages
- Add input validation
- Write tests

### Feature Ideas

- User authentication
- Playlist history
- Song favorites
- Custom music libraries
- Offline mode
- Mobile app
- Social sharing
- Spotify integration

### Code Improvements

- Refactor for better structure
- Add type hints
- Improve error handling
- Optimize performance
- Security enhancements

### Documentation

- Tutorial videos
- API examples
- Deployment guides
- Troubleshooting tips
- Translation to other languages

---

## Development Tips

### Debugging

```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use pdb for debugging
import pdb; pdb.set_trace()

# Print variables
print(f"Debug: emotion={emotion}, playlist={len(playlist)}")
```

### Testing Locally

```bash
# Test with different Python versions
python2.7 app.py
python3.9 app.py

# Test in different browsers
# Chrome, Firefox, Safari, Edge

# Test with different webcams
# Built-in, external USB
```

### Performance Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

---

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Pull Requests**: Code contributions

### Getting Help

- Read the [documentation](docs/)
- Check [troubleshooting guide](docs/Troubleshooting.md)
- Search existing issues
- Ask in GitHub Discussions

---

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

Thank you for contributing to Muze! 🎵
