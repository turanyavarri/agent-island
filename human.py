"""human.py - the human player's turns.

Each turn has two parts:
  - a check function (is_valid_...) that only looks at the answer
  - an input function (human_...) that keeps asking until the answer passes

The check functions don't use input(), so the Streamlit version can reuse them later.

Names: the code uses role keys ("Villain"), but the player only ever SEES show
names ("Selena"), so roles stay hidden until the end screen.
"""

from agents import SHOW_NAMES

HUMAN_NAME = "You"

# Flip to True once ranked agent_vote() is pushed. Counter
# needs every ballot in a round to use the same format (all numbers or all lists).
RANKED_VOTES = True


def show_name(role):
    """Role key -> name the player sees. "You" stays "You"."""
    return SHOW_NAMES.get(role, role)


def role_from_show_name(typed, players):
    """What the player typed ("selena") -> role key ("Villain"), or None if no match.

    Only matches players in the list, and ignores capitals and extra spaces.
    """
    typed = typed.strip().lower()
    for role in players:
        if show_name(role).lower() == typed:
            return role
    return None


def format_pair(pair):
    a, b = pair
    return f"{show_name(a)} & {show_name(b)}"


# ---------- checks (no input() here) ----------

def is_valid_speech(text):
    return len(text.strip()) > 0


def is_valid_partner(choice, players):
    """choice is a role key. Must be a player still in the game, and not yourself."""
    return choice in players and choice != HUMAN_NAME


def is_valid_vote(choice, pair_options, my_pair):
    """Vote must be a pair number on the ballot, and not your own pair."""
    return choice.isdigit() and int(choice) in pair_options and int(choice) != my_pair

def parse_ranking(text):
    """ "2, 0" or "2 0" -> [2, 0]. Returns None if it isn't all numbers."""
    parts = text.replace(",", " ").split()
    if not parts or not all(p.isdigit() for p in parts):
        return None
    return [int(p) for p in parts]


def is_valid_ranking(ranking, pair_options, my_pair):
    """A ranking must list every pair on the ballot except yours, each exactly once."""
    allowed = [p for p in pair_options if p != my_pair]
    return (
        ranking is not None
        and len(ranking) == len(allowed)
        and set(ranking) == set(allowed)
    )

# ---------- turns (these ask you to type) ----------

def human_speak(prompt="Your turn to talk: "):
    while True:
        text = input(prompt)
        if is_valid_speech(text):
            return text.strip()
        print("Say something! You can't skip your turn.")


def human_pick_partner(players):
    """Shows show names, returns the role key, e.g. you type "Selena" -> returns "Villain"."""
    options = [p for p in players if p != HUMAN_NAME]
    names = ", ".join(show_name(p) for p in options)
    while True:
        typed = input(f"Pick a partner ({names}): ")
        choice = role_from_show_name(typed, options)
        if choice and is_valid_partner(choice, players):
            return choice
        print("That's not someone you can pick, try again.")


def human_vote(pair_options, my_pair, pairs=None):
    """pair_options: pair numbers on the ballot. my_pair: your pair number.
    pairs (optional): the pairs list, so the ballot can show who's in each pair.

    Returns a ranked list like [2, 0] (most-wanted-out first) when RANKED_VOTES
    is on, otherwise a single pair number.
    """
    allowed = [p for p in pair_options if p != my_pair]

    if pairs:
        print("Who should go home?")
        for p in allowed:
            print(f"  {p}: {format_pair(pairs[p])}")

    # Only one pair to vote for: no need to ask
    if len(allowed) == 1:
        print(f"Only one pair to vote for, so your vote goes to pair {allowed[0]}.")
        return [allowed[0]] if RANKED_VOTES else allowed[0]

    if not RANKED_VOTES:
        while True:
            choice = input(f"Vote for a pair {allowed}: ").strip()
            if is_valid_vote(choice, pair_options, my_pair):
                return int(choice)
            print("That's not a valid pair, try again.")

    while True:
        text = input(f"Rank the pairs, most wanted out first, e.g. {', '.join(map(str, allowed))}: ")
        ranking = parse_ranking(text)

        # Listed all but one? Fill in the last one for them.
        if ranking and len(ranking) == len(allowed) - 1:
            missing = [p for p in allowed if p not in ranking]
            if len(missing) == 1:
                ranking.append(missing[0])

        if is_valid_ranking(ranking, pair_options, my_pair):
            return ranking
        print(f"List each of these pairs once, in order: {allowed}. Try again.")


if __name__ == "__main__":
    # Quick test: python human.py (no API calls, no key needed)
    players = ["You", "Charmer", "Villain", "Loyalist", "Observer", "Chaos Agent"]
    pairs = [("You", "Charmer"), ("Villain", "Loyalist"), ("Observer", "Chaos Agent")]

    print("You said:", human_speak())
    partner = human_pick_partner(players)
    print(f"Partner: {show_name(partner)} (role key for the code: {partner})")
    print("Voted for pair:", human_vote([0, 1, 2], my_pair=0, pairs=pairs))