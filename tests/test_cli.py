from audiobook_player import cli

def test_create_parser():
    parser = cli.create_parser()
    result = parser.parse_args(["/path/to/folder"])
    assert result.folder == "/path/to/folder"

def test_create_parser_with_list():
    parser = cli.create_parser()
    result = parser.parse_args(["/path/to/folder", "--list"])
    assert result.folder == "/path/to/folder"
    assert result.list == True

def test_create_parser_with_list_short():
    parser = cli.create_parser()
    result = parser.parse_args(["/path/to/folder", "-l"])
    assert result.folder == "/path/to/folder"
    assert result.list == True
