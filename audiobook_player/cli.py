import argparse

from .audioplayer import AudiobookPlayer


def create_parser():
    parser = argparse.ArgumentParser(description="Simple audiobook player")
    parser.add_argument("folder", type=str, help="Folder path")
    parser.add_argument(
        "--list", 
        "-l",
        action="store_true",
        help="List chapters with durations"
    )
    return parser


def cli():
    "Simple audiobook player"
    parser = create_parser()
    args = parser.parse_args()
    main(args)


def main(args):
    if args.folder:
        folder = args.folder
    else:
        folder = input("Enter audiobook folder: ").strip()

    player = AudiobookPlayer(folder)
    
    if args.list:
        player.list_chapters(block_for_durations=True)
        return
    
    player.start()
