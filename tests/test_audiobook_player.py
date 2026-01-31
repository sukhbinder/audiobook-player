import os
import json
import threading
from unittest.mock import MagicMock, patch
from audiobook_player import audioplayer
import pytest


@pytest.fixture
def player():
    with patch("audiobook_player.audioplayer.get_media_player"), patch(
        "audiobook_player.audioplayer.Getch"
    ):
        player = audioplayer.AudiobookPlayer("tests/fixtures/book")
        yield player


def test_find_mp3_files(tmpdir):
    # Create dummy mp3 files
    folder = tmpdir.mkdir("test_folder")
    file1 = folder.join("file1.mp3")
    file2 = folder.join("file2.mp3")
    file1.write("dummy content")
    file2.write("dummy content")

    # Test find_mp3_files function
    mp3_files = audioplayer.find_mp3_files(str(folder))
    assert len(mp3_files) == 2
    assert os.path.basename(mp3_files[0]) == "file1.mp3"
    assert os.path.basename(mp3_files[1]) == "file2.mp3"


def test_save_and_load_progress(tmpdir):
    # Test save_progress function
    folder = tmpdir.mkdir("test_folder")
    audioplayer.save_progress(str(folder), 3)

    # Test load_progress function
    progress, durations = audioplayer.load_progress(str(folder))
    assert progress == 3
    assert durations == {}


def test_save_and_load_progress_with_durations(tmpdir):
    # Test save_progress with durations
    folder = tmpdir.mkdir("test_folder")
    durations = {"file1.mp3": 123.45, "file2.mp3": 456.78}

    audioplayer.save_progress(str(folder), 3, durations)

    # Test load_progress with durations
    progress, loaded_durations = audioplayer.load_progress(str(folder))
    assert progress == 3
    assert loaded_durations == durations


def test_duration_calculator_initialization(player):
    # Test duration calculator initialization
    assert player.duration_calculator is not None
    assert isinstance(player.duration_calculator, audioplayer.DurationCalculator)


def test_duration_calculator_get_duration(player):
    # Test getting durations from calculator
    # Mock get_mp3_duration to return a known value
    with patch('audiobook_player.audioplayer.get_mp3_duration', return_value=123.45):
        # Get duration for first chapter
        duration = player.duration_calculator.get_duration(player.chapters[0])
        assert duration is None  # Initially None (not calculated yet)

        # Manually trigger calculation since background thread may not run in test
        player.duration_calculator.calculate_missing_durations()
        
        # Now duration should be available (check by filename)
        filename = os.path.basename(player.chapters[0])
        with player.duration_calculator.lock:
            duration = player.duration_calculator.durations.get(filename)
        assert duration == 123.45


def test_duration_calculator_thread_safety(player):
    # Test thread safety of duration calculator
    calculator = player.duration_calculator
    
    # Test concurrent access
    results = []
    
    def get_duration_worker():
        duration = calculator.get_duration(player.chapters[0])
        results.append(duration)
    
    # Create multiple threads accessing the calculator
    threads = []
    for _ in range(5):
        thread = threading.Thread(target=get_duration_worker)
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # All results should be the same (None initially)
    assert len(results) == 5
    assert all(result is None for result in results)


def test_natural_key():
    # Test natural_key function
    key = audioplayer.natural_key("chapter10.mp3")
    assert key == ["chapter", 10, ".mp3"]
    key = audioplayer.natural_key("chapter2.mp3")
    assert key == ["chapter", 2, ".mp3"]
    key = audioplayer.natural_key("track 1.mp3")
    assert key == ["track ", 1, ".mp3"]


def test_handle_cmd_n(player):
    # Test 'n' command (next)
    player.current = 0
    player._handle_cmd("n")
    assert player.current == 1


def test_handle_cmd_p(player):
    # Test 'p' command (previous)
    player.current = 1
    player._handle_cmd("p")
    assert player.current == 0


def test_handle_cmd_s(player):
    # Test 's' command (stop)
    with patch("audiobook_player.audioplayer.save_progress") as mock_save_progress:
        player._handle_cmd("s")
        assert player.stop_flag.is_set()
        mock_save_progress.assert_called_once_with(
            player.folder, 
            player.current,
            player.duration_calculator.durations
        )


def test_handle_cmd_q(player):
    # Test 'q' command (quit)
    with patch("audiobook_player.audioplayer.save_progress") as mock_save_progress:
        player._handle_cmd("q")
        assert player.stop_flag.is_set()
        mock_save_progress.assert_called_once_with(
            player.folder, 
            player.current,
            player.duration_calculator.durations
        )
