#!/usr/bin/env python3

"""
audiobook.py

Cross-platform CLI audiobook player:
- macOS  → afplay
- Raspberry Pi (Linux) → omxplayer

Features:
- natural sorting of MP3s
- live controls (n, p, s, q)
- progress saving to .progress.json
- automatic resume
- modular media-player backend (pluggable)
- single file deployment
"""

import os
import sys
import json
import re
import platform
import subprocess
import threading
import queue
import time
import signal
import termios
import tty
from abc import ABC, abstractmethod


############################################################
# Media Player Base (plugin architecture)
############################################################


class MediaPlayerBase(ABC):
    def __init__(self):
        self.proc = None

    @abstractmethod
    def play(self, filepath: str):
        """Start playback of a file. Must return a subprocess.Popen."""
        pass

    def stop(self):
        """Stop playback and kill process."""
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass
            try:
                self.proc.kill()
            except Exception:
                pass
        self.proc = None

    def is_playing(self):
        return self.proc is not None and self.proc.poll() is None


############################################################
# macOS Player Backend (afplay)
############################################################


class AfplayPlayer(MediaPlayerBase):
    def play(self, filepath: str):
        try:
            self.proc = subprocess.Popen(["afplay", filepath])
            return self.proc
        except FileNotFoundError:
            print("Error: 'afplay' not found. macOS required.")
            raise


############################################################
# Raspberry Pi Player Backend (omxplayer)
############################################################


class OmxPlayer(MediaPlayerBase):
    def play(self, filepath: str):
        try:
            # Use local audio output
            self.proc = subprocess.Popen(
                ["omxplayer", "-o", "local", filepath],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
            return self.proc
        except FileNotFoundError:
            print("Error: 'omxplayer' not found. Install with:")
            print("  sudo apt install omxplayer")
            raise


############################################################
# Factory: Pick correct backend based on OS
############################################################


def get_media_player():
    system = platform.system()

    if system == "Darwin":
        return AfplayPlayer()

    elif system == "Linux":
        return OmxPlayer()

    else:
        raise RuntimeError(f"Unsupported OS: {system}")


############################################################
# Utility functions
############################################################

PROGRESS_FILENAME = ".progress.json"


def natural_key(s: str):
    parts = re.split(r"(\d+)", s)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def find_mp3_files(folder: str):
    files = [
        f
        for f in os.listdir(folder)
        if f.lower().endswith(".mp3") and os.path.isfile(os.path.join(folder, f))
    ]
    files.sort(key=natural_key)
    return [os.path.join(folder, f) for f in files]


def save_progress(folder: str, idx: int):
    path = os.path.join(folder, PROGRESS_FILENAME)
    try:
        with open(path, "w") as f:
            json.dump({"last_chapter": idx}, f)
    except Exception as e:
        print(f"Warning: could not save progress: {e}")


def load_progress(folder: str):
    path = os.path.join(folder, PROGRESS_FILENAME)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            obj = json.load(f)
        return obj.get("last_chapter")
    except:
        return None


############################################################
# Single-key input helper
############################################################


class Getch:
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)

    def enable_raw(self):
        tty.setraw(self.fd)

    def disable_raw(self):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

    def get(self):
        return sys.stdin.read(1)


############################################################
# Main Audiobook Player
############################################################


class AudiobookPlayer:
    def __init__(self, folder: str):
        self.folder = os.path.abspath(folder)
        self.chapters = find_mp3_files(self.folder)
        self.current = 0
        self.command_q = queue.Queue()
        self.stop_flag = threading.Event()
        self.getch = Getch()

        # plug-in backend
        self.player = get_media_player()

        signal.signal(signal.SIGINT, self._on_sigint)

    def _on_sigint(self, sig, frame):
        print("\nCaught Ctrl+C — restoring terminal.")
        self.stop_flag.set()
        self.player.stop()
        save_progress(self.folder, self.current)
        self.getch.disable_raw()
        sys.exit(0)

    def load_or_prompt_progress(self):
        saved = load_progress(self.folder)
        if saved is None:
            return

        if 0 <= saved < len(self.chapters):
            ans = input(f"Resume from chapter {saved + 1}? (Y/n): ").strip().lower()
            if ans in ("", "y", "yes"):
                self.current = saved
            else:
                self.current = 0

    def _keyboard_thread(self):
        try:
            self.getch.enable_raw()
            while not self.stop_flag.is_set():
                ch = self.getch.get()
                if ch:
                    self.command_q.put(ch)
        except Exception as e:
            print("Keyboard thread error:", e)
        finally:
            # This ALWAYS runs, even on Ctrl+C
            self.getch.disable_raw()

    def _print_controls(self):
        print("Controls: n=next, p=prev, s=stop & save, q=quit\n")

    def _handle_cmd(self, cmd):
        cmd = cmd.lower()
        if cmd == "n":
            print("\nSkipping to next.")
            self.player.stop()
            self.current = min(self.current + 1, len(self.chapters) - 1)

        elif cmd == "p":
            print("\nGoing to previous.")
            self.player.stop()
            self.current = max(self.current - 1, 0)

        elif cmd == "s":
            print("\nStopping and saving progress.")
            save_progress(self.folder, self.current)
            self.player.stop()
            self.stop_flag.set()

        elif cmd == "q":
            print("\nQuitting (progress saved).")
            save_progress(self.folder, self.current)
            self.player.stop()
            self.stop_flag.set()

        elif cmd == "?":
            self._print_controls()

    def start(self):
        if not os.path.isdir(self.folder):
            print(f"Folder not found: {self.folder}")
            return

        if not self.chapters:
            print("No MP3 files found.")
            return

        print(f"Found {len(self.chapters)} chapters.")
        self.load_or_prompt_progress()
        self._print_controls()

        threading.Thread(target=self._keyboard_thread, daemon=True).start()

        while not self.stop_flag.is_set():
            if not (0 <= self.current < len(self.chapters)):
                print("Reached end.")
                save_progress(self.folder, max(0, len(self.chapters) - 1))
                break

            chapter = self.chapters[self.current]
            print(
                f"\nPlaying chapter {self.current + 1}/{len(self.chapters)}: {os.path.basename(chapter)}"
            )

            self.player.play(chapter)

            # inner loop: check process and commands
            while True:
                # process commands
                try:
                    cmd = self.command_q.get_nowait()
                    self._handle_cmd(cmd)
                    if self.stop_flag.is_set() or not self.player.is_playing():
                        break
                except queue.Empty:
                    pass

                # if track naturally ends
                if not self.player.is_playing():
                    self.current += 1
                    break

                time.sleep(0.1)

        print("Goodbye.")
        self.player.stop()
        save_progress(self.folder, min(self.current, len(self.chapters) - 1))
        self.getch.disable_raw()


############################################################
# CLI Entry
############################################################


def main():
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Enter audiobook folder: ").strip()

    player = AudiobookPlayer(folder)
    player.start()


if __name__ == "__main__":
    main()
