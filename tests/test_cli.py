from audiobook_player import cli

def test_create_parser():
    parser = cli.create_parser()
    result = parser.parse_args(["/path/to/folder"])
    assert result.folder == "/path/to/folder"
