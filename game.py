import random

from agents import SHOW_NAMES, format_pairs, agent_intro, agent_speak
from host import host_open, host_announce_pairs
from human import human_speak


def show(name):
    return SHOW_NAMES.get(name, name)


def find_my_pair(name, pairs):
    for i, pair in enumerate(pairs):
        if name in pair:
            return i
    return None


def count_votes(votes):
    if not votes:
        raise ValueError("Cannot count votes: no votes provided.")

    tally = {}

    for pair_number in votes.values():
        tally[pair_number] = tally.get(pair_number, 0) + 1

    highest_count = max(tally.values())

    tied_pairs = [
        pair_number
        for pair_number, count in tally.items()
        if count == highest_count
    ]

    return random.choice(tied_pairs)


def eliminate_pair(state, pair_number):
    eliminated_pair = state["pairs"].pop(pair_number)

    state["players"] = [
        name
        for name in state["players"]
        if name not in eliminated_pair
    ]

    state["eliminated"].extend(eliminated_pair)

    return eliminated_pair


def run_talk_phase(state):
    state["phase"] = "talk"
    print("\nCurrent phase:", state["phase"])

    for name in state["players"]:
        if name == "You":
            line = human_speak("Your turn to talk: ")
        else:
            line = agent_speak(
                name,
                state["transcript"],
                state["pairs"],
            )

        message = f"{show(name)}: {line}"
        state["transcript"].append(message)
        print(message)


game = {
    "phase": "opening",
    "players": [
        "You",
        "Charmer",
        "Villain",
        "Loyalist",
        "Observer",
        "Chaos Agent",
    ],
    "pairs": [],
    "transcript": [],
    "confessionals": {},
    "eliminated": [],
}


def run_game():
    # Open the show.
    print("Current phase:", game["phase"])

    opening = host_open(game["players"])
    message = f"Caesar: {opening}"
    game["transcript"].append(message)
    print(message)

    # Introduce each contestant.
    game["phase"] = "intro"
    print("\nCurrent phase:", game["phase"])

    for name in game["players"]:
        if name == "You":
            line = human_speak("Introduce yourself: ")
        else:
            line = agent_intro(name)

        message = f"{show(name)}: {line}"
        game["transcript"].append(message)
        print(message)

    # Move to the pairing phase.
    game["phase"] = "pairing"
    print("\nCurrent phase:", game["phase"])

    # Shuffle a copy of the player list.
    shuffled_players = game["players"].copy()
    random.shuffle(shuffled_players)

    # Create pairs from adjacent players.
    for i in range(0, len(shuffled_players), 2):
        pair = (shuffled_players[i], shuffled_players[i + 1])
        game["pairs"].append(pair)

    # Announce and display the official pairs.
    announcement = host_announce_pairs(game["pairs"])
    message = f"Caesar: {announcement}"
    game["transcript"].append(message)
    print(message)

    print("\nPairs:")
    print(format_pairs(game["pairs"]))

    # Let each contestant speak once.
    run_talk_phase(game)


if __name__ == "__main__":
    run_game()