"""save.py - save each game to a file so we can review games and debug.

Usage (Bella, at the end of run_game, or when the game pauses):
    from save import save_game
    save_game(state)

Each game becomes one file like games/game_2026-11-14_22-10-05.json
The games/ folder is in .gitignore, so test games don't get pushed.
"""

import json
import os
from datetime import datetime

from agents import SHOW_NAMES

GAMES_FOLDER = "games"

# Engine bookkeeping that isn't useful when reviewing a game
SKIP_KEYS = {"turn_index", "waiting_for", "events"}


def save_game(state, folder=GAMES_FOLDER):
    """Write the game state to a new JSON file. Returns the file path.

    Works on finished games and on games that paused partway, so a crash
    or a pause still leaves something to debug.
    """
    os.makedirs(folder, exist_ok=True)

    record = {key: value for key, value in state.items() if key not in SKIP_KEYS}
    record["saved_at"] = datetime.now().isoformat(timespec="seconds")
    record["status"] = "finished" if state.get("phase") == "finished" else "unfinished"
    # Who was who, so the file is readable without the code
    record["show_names"] = {
        role: SHOW_NAMES.get(role, role) for role in state.get("cast", [])
    }

    filename = f"game_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    path = os.path.join(folder, filename)

    # default=list turns pairs (tuples) and any sets into lists JSON can store
    with open(path, "w", encoding="utf-8") as file:
        json.dump(record, file, indent=2, ensure_ascii=False, default=list)

    print(f"Game saved to {path}")
    return path


def load_game(path):
    """Read a saved game back in (for reviewing or the end screen later)."""
    with open(path, encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":
    # Quick test: python save.py (no API calls, no key needed)
    fake_state = {
        "phase": "finished",
        "round": 2,
        "cast": ["You", "Charmer", "Villain", "Loyalist"],
        "players": ["You", "Charmer"],
        "pairs": [("You", "Charmer")],
        "transcript": ["Abel: Hi!", "You: Hello.", "Selena: Interesting..."],
        "confessionals": {"You": "I don't trust Selena.", "Villain": "Abel is easy."},
        "votes": {"You": [1], "Charmer": [1]},
        "eliminated": ["Villain", "Loyalist"],
        "winner": ("You", "Charmer"),
        "turn_index": 3,
        "waiting_for": None,
        "events": ["..."],
    }
    path = save_game(fake_state, folder="games_test")
    loaded = load_game(path)
    print("Status:", loaded["status"], "| Winner:", loaded["winner"])
    print("Show names:", loaded["show_names"])