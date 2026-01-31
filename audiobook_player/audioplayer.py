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
from typing import Optional

try:
    from mutagen.mp3 import MP3
except ImportError:
    MP3 = None


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
                ["omxplayer", "--no-keys", "--no-osd", "-o", "local", filepath],
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

    elif system == "Windows":
        return AfplayPlayer()

    else:
        raise RuntimeError(f"Unsupported OS: {system}")


############################################################
# Utility functions
############################################################

PROGRESS_FILENAME = ".progress.json"


def get_mp3_duration(filepath: str) -> Optional[float]:
    """Get duration of MP3 file in seconds using mutagen."""
    if MP3 is None:
        return None

    try:
        audio = MP3(filepath)
        return audio.info.length
    except Exception:
        return None


def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS format."""
    if seconds is None:
        return "Unknown"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


def natural_key(s: str):
    name, ext = os.path.splitext(s)
    parts = re.split(r"(\d+)", name)
    # filter out empty strings
    parts = list(filter(None, parts))
    parts.append(ext)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def find_mp3_files(folder: str):
    files = [
        f
        for f in os.listdir(folder)
        if f.lower().endswith(".mp3") and os.path.isfile(os.path.join(folder, f))
    ]
    files.sort(key=natural_key)
    return [os.path.join(folder, f) for f in files]


def save_progress(folder: str, idx: int, durations: dict = None):
    path = os.path.join(folder, PROGRESS_FILENAME)
    try:
        progress_data = {}
        if os.path.exists(path):
            with open(path, "r") as f:
                progress_data = json.load(f)

        progress_data["last_chapter"] = idx

        # Only update durations if provided
        if durations is not None:
            if "durations" not in progress_data:
                progress_data["durations"] = {}
            progress_data["durations"].update(durations)

        with open(path, "w") as f:
            json.dump(progress_data, f)
    except Exception as e:
        print(f"Warning: could not save progress: {e}")


def load_progress(folder: str):
    path = os.path.join(folder, PROGRESS_FILENAME)
    if not os.path.exists(path):
        return None, {}

    try:
        with open(path, "r") as f:
            obj = json.load(f)

        last_chapter = obj.get("last_chapter")
        durations = obj.get("durations", {})

        return last_chapter, durations
    except Exception:
        return None, {}


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
# Duration Calculator (Background Thread)
############################################################

class DurationCalculator:
    def __init__(self, chapters, existing_durations=None):
        self.chapters = chapters
        self.durations = existing_durations or {}
        self.lock = threading.Lock()
        self.calculation_complete = threading.Event()
        self.update_callbacks = []

    def calculate_missing_durations(self):
        """Calculate durations for files not in cache (background thread)"""
        try:
            missing_files = [
                chap for chap in self.chapters
                if os.path.basename(chap) not in self.durations
            ]

            new_durations = {}
            for chapter in missing_files:
                duration = get_mp3_duration(chapter)
                if duration is not None:
                    filename = os.path.basename(chapter)
                    with self.lock:
                        self.durations[filename] = duration
                        new_durations[filename] = duration

            # Notify callbacks if we have new durations
            if new_durations:
                for callback in self.update_callbacks:
                    try:
                        callback(new_durations)
                    except Exception:
                        pass

            self.calculation_complete.set()
            return new_durations

        except Exception:
            self.calculation_complete.set()
            return {}

    def get_duration(self, chapter_path):
        """Get duration for a chapter (thread-safe)"""
        filename = os.path.basename(chapter_path)
        with self.lock:
            return self.durations.get(filename)

    def add_update_callback(self, callback):
        """Add callback for when durations are updated"""
        self.update_callbacks.append(callback)

    def is_complete(self):
        """Check if background calculation is complete"""
        return self.calculation_complete.is_set()


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
        self.getch = None

        # plug-in backend
        self.player = get_media_player()

        # Initialize durations and start background calculation
        self.duration_calculator = None
        self._initialize_durations()

        signal.signal(signal.SIGINT, self._on_sigint)

    def _on_sigint(self, sig, frame):
        print("\nCaught Ctrl+C — restoring terminal.")
        self.stop_flag.set()
        self.player.stop()
        save_progress(
            self.folder,
            self.current,
            self.duration_calculator.durations if self.duration_calculator else {}
        )
        if self.getch:
            self.getch.disable_raw()
        sys.exit(0)

    def list_chapters(self, block_for_durations=True):
        """List all chapters with their durations."""
        if not self.chapters:
            print("No MP3 files found.")
            return

        # For --list command, block until all durations are calculated
        if block_for_durations:
            # Check if we have all durations already
            with self.duration_calculator.lock:
                missing_count = sum(
                    1 for chap in self.chapters
                    if os.path.basename(chap) not in self.duration_calculator.durations
                )

            if missing_count > 0:
                print("Calculating durations...")
                self.duration_calculator.calculate_missing_durations()

        print(f"Found {len(self.chapters)} chapters in '{self.folder}':")
        print("-" * 60)

        for i, chapter in enumerate(self.chapters, 1):
            duration = self.duration_calculator.get_duration(chapter)
            duration_str = format_duration(duration) if duration is not None else "Unknown"
            filename = os.path.basename(chapter)
            print(f"{i:2d}. {filename:40s} {duration_str}")

        print("-" * 60)
        total_duration = sum(
            dur for dur in self.duration_calculator.durations.values()
            if dur is not None
        )
        total_str = format_duration(total_duration)
        print(f"Total duration: {total_str}")

    def _initialize_durations(self):
        """Load existing durations and start background calculation"""
        _, existing_durations = load_progress(self.folder)

        # Create duration calculator with existing durations
        self.duration_calculator = DurationCalculator(
            self.chapters,
            existing_durations
        )

        # Start background calculation thread
        calc_thread = threading.Thread(
            target=self.duration_calculator.calculate_missing_durations,
            daemon=True
        )
        calc_thread.start()

    def load_or_prompt_progress(self):
        saved, _ = load_progress(self.folder)
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
        self.safe_print("Controls: n=next, p=prev, s=stop & save, q=quit\n")

    def safe_print(self, msg=""):
        print("\r" + msg, flush=True)

    def _handle_cmd(self, cmd):
        cmd = cmd.lower()
        if cmd == "n":
            self.safe_print("Skipping to next.")
            self.player.stop()
            self.current = min(self.current + 1, len(self.chapters) - 1)

        elif cmd == "p":
            self.safe_print("\nGoing to previous.")
            self.player.stop()
            self.current = max(self.current - 1, 0)

        elif cmd == "s":
            self.safe_print("\nStopping and saving progress.")
            save_progress(
                self.folder,
                self.current,
                self.duration_calculator.durations
            )
            self.player.stop()
            self.stop_flag.set()

        elif cmd == "q":
            self.safe_print("\nQuitting (progress saved).")
            save_progress(
                self.folder,
                self.current,
                self.duration_calculator.durations
            )
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

        self.getch = Getch()
        threading.Thread(target=self._keyboard_thread, daemon=True).start()

        while not self.stop_flag.is_set():
            if not (0 <= self.current < len(self.chapters)):
                self.safe_print("Reached end.")
                save_progress(self.folder, max(0, len(self.chapters) - 1))
                break

            chapter = self.chapters[self.current]
            duration = self.duration_calculator.get_duration(chapter)
            duration_str = format_duration(duration) if duration is not None else "Unknown"
            self.safe_print(
                f"Playing chapter {self.current + 1}/{len(self.chapters)}: {os.path.basename(chapter).strip()} [{duration_str}]\n"
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

        self.safe_print("Goodbye.")
        self.player.stop()
        save_progress(
            self.folder,
            min(self.current, len(self.chapters) - 1),
            self.duration_calculator.durations
        )
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
