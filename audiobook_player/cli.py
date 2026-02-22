import argparse
from datetime import datetime

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
    parser.add_argument(
        "--history",
        "-H",
        action="store_true",
        help="Show playback history and listening statistics"
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
    
    if args.history:
        show_playback_history(player)
        return
    
    player.start()


def show_playback_history(player):
    """Display playback history and listening statistics"""
    history = player.playback_timer.get_history()
    
    if not history:
        print("No playback history found.")
        return
    
    print(f"\n📊 Playback History for '{player.folder}'")
    print("=" * 60)
    
    total_listening_time = 0.0
    sessions_by_chapter = {}
    
    # Organize sessions by chapter
    for i, session in enumerate(history, 1):
        chapter = session['chapter']
        if chapter not in sessions_by_chapter:
            sessions_by_chapter[chapter] = []
        sessions_by_chapter[chapter].append(session)
        total_listening_time += session['duration_played']
    
    # Display summary
    print(f"Total Listening Time: {format_duration(total_listening_time)}")
    print(f"Total Sessions: {len(history)}")
    print(f"Chapters Listened: {len(sessions_by_chapter)}")
    print("-" * 60)
    
    # Display detailed history
    print("\n📋 Detailed Playback Sessions:")
    for i, session in enumerate(history, 1):
        chapter_name = f"Chapter {session['chapter'] + 1}"
        start_time = datetime.fromisoformat(session['start_time'])
        end_time = datetime.fromisoformat(session['end_time'])
        duration = session['duration_played']
        
        print(f"{i:2d}. {chapter_name:15s} | {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    → {end_time.strftime('%Y-%m-%d %H:%M:%S')} | Duration: {format_duration(duration)}")
    
    # Display chapter-by-chapter summary
    print("\n📚 Chapter-by-Chapter Summary:")
    for chapter, sessions in sorted(sessions_by_chapter.items()):
        chapter_name = f"Chapter {chapter + 1}"
        chapter_sessions = len(sessions)
        chapter_time = sum(s['duration_played'] for s in sessions)
        
        print(f"  {chapter_name:15s}: {chapter_sessions} session(s), {format_duration(chapter_time)}")
    
    print("=" * 60)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS format"""
    if seconds is None:
        return "Unknown"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"
