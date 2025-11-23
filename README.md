# Audiobook Player

[![PyPI](https://img.shields.io/pypi/v/audiobook-player.svg)](https://pypi.org/project/audiobook-player/)
[![Changelog](https://img.shields.io/github/v/release/sukhbinder/audiobook-player?include_prereleases&label=changelog)](https://github.com/sukhbinder/audiobook-player/releases)
[![Tests](https://github.com/sukhbinder/audiobook-player/actions/workflows/test.yml/badge.svg)](https://github.com/sukhbinder/audiobook-player/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/sukhbinder/audiobook-player/blob/master/LICENSE)

A simple, cross-platform command-line audiobook player.

## Features

- **Cross-platform:** Works on macOS and Raspberry Pi (Linux).
- **Natural Sorting:** Chapters are sorted naturally (e.g., "chapter 2.mp3" comes before "chapter 10.mp3").
- **Live Controls:** Control playback with keyboard shortcuts (next, previous, stop, quit).
- **Progress Saving:** Automatically saves your progress and resumes from where you left off.
- **Modular Backend:** The media player backend is pluggable, making it easy to add support for other platforms.

## Supported Platforms

- **macOS:** Uses `afplay` for audio playback.
- **Raspberry Pi (Linux):** Uses `omxplayer` for audio playback.

## Installation

Install this tool using `pip`:
```bash
pip install audiobook-player
```

## Usage

To start playing an audiobook, simply point the player to the folder containing your MP3 files:
```bash
aplayer /path/to/your/audiobook
```

If you don't provide a folder path, you will be prompted to enter one.

### Controls

Once the audiobook is playing, you can use the following keyboard shortcuts to control playback:

- `n`: Go to the next chapter.
- `p`: Go to the previous chapter.
- `s`: Stop playback and save your progress.
- `q`: Quit the player (your progress will be saved).
- `?`: Display the controls.

## Development

To contribute to this tool, first check out the code. Then create a new virtual environment:
```bash
cd audiobook-player
python -m venv venv
source venv/bin/activate
```

Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```

To run the tests:
```bash
python -m pytest
```
