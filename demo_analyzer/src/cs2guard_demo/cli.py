"""Command-line interface for the offline Demo Analyzer."""

import argparse
from pathlib import Path
import sys

from cs2guard_demo.analysis import analyze_demo


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(prog="cs2guard")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze = commands.add_parser("analyze", help="Analyze a CS2 demo with a persisted M5 model")
    analyze.add_argument("demo", type=Path)
    analyze.add_argument("--model", type=Path, required=True, help="M5 .joblib model; adjacent .json metadata required")
    analyze.add_argument("--output", type=Path, help="Report directory (default: <demo stem>_analysis)")
    args = parser.parse_args(argv)
    output = args.output or Path(f"{args.demo.stem}_analysis")
    try:
        report = analyze_demo(args.demo, args.model, output)
    except Exception as error:
        print(f"Analysis failed: {str(error) or type(error).__name__}", file=sys.stderr)
        return 2
    summary = report["summary"]
    print(f"Match Analysis: {report['match']['match_id']} | {summary['status']}")
    print(f"Players: {summary['scored_player_count']}/{summary['player_count']} scored; windows: {summary['window_count']}")
    print("Supervised mean scores (uncalibrated; no cheating conclusion):")
    for player in report["players"]:
        score = f"{player['score']:.6f}" if player["score"] is not None else "N/A (insufficient data)"
        print(f"{player['rank'] or '-'}  {player['player_name']} [{player['player_id']}]  {score}  windows={player['window_count']}")
    print(f"Report: {(output / 'report.md').resolve()}")
    print(f"JSON: {(output / 'report.json').resolve()}")
    return 0 if summary["scored_player_count"] else 2
