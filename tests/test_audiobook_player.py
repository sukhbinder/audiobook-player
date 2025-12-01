import os
import json
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
    progress = audioplayer.load_progress(str(folder))
    assert progress == 3


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
        mock_save_progress.assert_called_once_with(player.folder, player.current)


def test_handle_cmd_q(player):
    # Test 'q' command (quit)
    with patch("audiobook_player.audioplayer.save_progress") as mock_save_progress:
        player._handle_cmd("q")
        assert player.stop_flag.is_set()
        mock_save_progress.assert_called_once_with(player.folder, player.current)
