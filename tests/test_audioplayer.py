import os
import json
from unittest.mock import MagicMock, patch
from audiobook_player import audioplayer
import pytest

# Mock mutagen for testing
@patch('audiobook_player.audioplayer.MP3')
def test_get_mp3_duration(mock_mp3):
    # Test with valid MP3
    mock_audio = MagicMock()
    mock_audio.info.length = 125.5
    mock_mp3.return_value = mock_audio
    
    duration = audioplayer.get_mp3_duration('test.mp3')
    assert duration == 125.5
    
    # Test with exception
    mock_mp3.side_effect = Exception('Test error')
    duration = audioplayer.get_mp3_duration('test.mp3')
    assert duration is None
    
    # Test with MP3=None (mutagen not available)
    with patch('audiobook_player.audioplayer.MP3', None):
        duration = audioplayer.get_mp3_duration('test.mp3')
        assert duration is None


def test_format_duration():
    # Test various duration formats
    assert audioplayer.format_duration(65.5) == "1:05"
    assert audioplayer.format_duration(3665.2) == "1:01:05"
    assert audioplayer.format_duration(125.0) == "2:05"
    assert audioplayer.format_duration(None) == "Unknown"
    assert audioplayer.format_duration(0) == "0:00"

@pytest.fixture
def player():
    with patch('audiobook_player.audioplayer.get_media_player'), \
         patch('audiobook_player.audioplayer.Getch'):
        player = audioplayer.AudiobookPlayer('tests/fixtures/book')
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

def test_natural_key():
    # Test natural_key function
    key = audioplayer.natural_key("chapter10.mp3")
    assert key == ['chapter', 10, '.mp3']
    key = audioplayer.natural_key("chapter2.mp3")
    assert key == ['chapter', 2, '.mp3']
    key = audioplayer.natural_key("track 1.mp3")
    assert key == ['track ', 1, '.mp3']

def test_handle_cmd_n(player):
    # Test 'n' command (next)
    player.current = 0
    player._handle_cmd('n')
    assert player.current == 1

def test_handle_cmd_p(player):
    # Test 'p' command (previous)
    player.current = 1
    player._handle_cmd('p')
    assert player.current == 0

def test_handle_cmd_s(player):
    # Test 's' command (stop)
    with patch('audiobook_player.audioplayer.save_progress') as mock_save_progress:
        player._handle_cmd('s')
        assert player.stop_flag.is_set()
        mock_save_progress.assert_called_once_with(
            player.folder, 
            player.current,
            player.duration_calculator.durations
        )

def test_handle_cmd_q(player):
    # Test 'q' command (quit)
    with patch('audiobook_player.audioplayer.save_progress') as mock_save_progress:
        player._handle_cmd('q')
        assert player.stop_flag.is_set()
        mock_save_progress.assert_called_once_with(
            player.folder, 
            player.current,
            player.duration_calculator.durations
        )


def test_list_chapters(player):
    # Test list_chapters method
    with patch('builtins.print') as mock_print:
        player.list_chapters()
        # Should print chapter information
        assert mock_print.call_count > 0
        # Check that it prints the expected format
        calls = [str(call) for call in mock_print.call_args_list]
        assert any('Found 2 chapters' in str(call) for call in calls)


def test_list_chapters_with_real_mp3():
    """Test list_chapters with real MP3 files that have proper duration info."""
    import os
    from audiobook_player.audioplayer import AudiobookPlayer
    
    # Check if the test MP3 files exist
    test_dir = 'test_mp3'
    if os.path.exists(test_dir) and os.path.isdir(test_dir):
        mp3_files = [f for f in os.listdir(test_dir) if f.endswith('.mp3')]
        if mp3_files:
            player = AudiobookPlayer(test_dir)
            
            # Wait for background duration calculation to complete
            player.duration_calculator.calculation_complete.wait(timeout=10.0)
            
            # Capture the output
            import io
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            with redirect_stdout(f):
                player.list_chapters()
            
            output = f.getvalue()
            
            # Verify the output contains expected information
            assert 'Found 3 chapters' in output
            assert 'earlyhistoryairplane_1_wright_64kb.mp3' in output
            assert 'earlyhistoryairplane_2_wright_64kb.mp3' in output
            assert 'earlyhistoryairplane_3_wright_64kb.mp3' in output
            assert 'Total duration:' in output
            
            # Check that durations are displayed (not "Unknown")
            # The exact duration might vary, so just check it's not "Unknown"
            assert 'Unknown' not in output
            assert '26:07' in output
            assert '34:04' in output
            
            print("✓ Real MP3 test passed - durations extracted correctly")
        else:
            print("⚠ Real MP3 test skipped - no MP3 files found in test_mp3/")
    else:
        print("⚠ Real MP3 test skipped - test_mp3/ directory not found")
