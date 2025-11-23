import argparse

def create_parser():
    parser = argparse.ArgumentParser(description="Simple audiobook player")
    parser.add_argument("name", type=str, help="Dummy argument")
    return parser


def cli():
    "Simple audiobook player"
    parser = create_parser()
    args = parser.parse_args()
    mycommand(args)


def mycommand(args):
    print(args)