"""human.py - the human player's turns.

Each turn has two parts:
  - a check function (is_valid_...) that only looks at the answer
  - an input function (human_...) that keeps asking until the answer passes

The check functions don't use input(), so the Streamlit version can reuse them later.
"""

HUMAN_NAME = "You"


# ---------- checks (no input() here) ----------

def is_valid_speech(text):
    return len(text.strip()) > 0


def is_valid_partner(choice, players):
    """Partner must be a player still in the game, and not yourself."""
    return choice in players and choice != HUMAN_NAME


def is_valid_vote(choice, pair_options, my_pair):
    """Vote must be a pair number on the ballot, and not your own pair."""
    return choice.isdigit() and int(choice) in pair_options and int(choice) != my_pair


# ---------- turns (these ask you to type) ----------

def human_speak(prompt="Your turn to talk: "):
    while True:
        text = input(prompt)
        if is_valid_speech(text):
            return text.strip()
        print("Say something! You can't skip your turn.")


def human_pick_partner(players):
    options = [p for p in players if p != HUMAN_NAME]
    while True:
        choice = input(f"Pick a partner {options}: ").strip()
        # accept any capitalization, e.g. "charmer" -> "Charmer"
        for name in options:
            if choice.lower() == name.lower():
                choice = name
        if is_valid_partner(choice, players):
            return choice
        print("That's not someone you can pick, try again.")


def human_vote(pair_options, my_pair):
    """pair_options: list of pair numbers on the ballot. my_pair: your pair number."""
    allowed = [p for p in pair_options if p != my_pair]
    while True:
        choice = input(f"Vote for a pair {allowed}: ").strip()
        if is_valid_vote(choice, pair_options, my_pair):
            return int(choice)
        print("That's not a valid pair, try again.")


if __name__ == "__main__":
    # Quick test: python human.py
    players = ["You", "Charmer", "Villain", "Loyalist", "Observer", "Chaos"]
    print("You said:", human_speak())
    print("Partner:", human_pick_partner(players))
    print("Voted for pair:", human_vote([0, 1, 2], my_pair=0))