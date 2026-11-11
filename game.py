"""Agent Island's rule engine and terminal runner.

Run: python game.py
Importing this file does not initialize an AI client or start a game.
The default adapters use the team's existing functions unchanged.
Unimplemented team features are explicit None hooks.
"""

import io
import inspect
import random
from contextlib import redirect_stdout


HUMAN_NAME = "You"

DEFAULT_PLAYERS = [
    HUMAN_NAME,
    "Charmer",
    "Villain",
    "Loyalist",
    "Observer",
    "Chaos Agent",
]

NO_INPUT = object()


def future_hooks():
    """Engine-local placeholders, not existing teammate functions.

    Agree on these signatures with the team before connecting real AI:

    pair_pitch(pair, public_transcript) -> str

    jury_vote(
        name, public_transcript, pairs, own_confessional
    ) -> int

    break_tie(
        public_transcript, pairs, tied_pair_numbers, purpose
    ) -> dict

    Example tie-break result:
        {"pair_number": 0, "reason": "Public evidence..."}

    purpose is either "eliminate" or "win".

    write_notes(
        name, public_transcript, pairs, own_notes
    ) -> list[str]
    """
    return {
        "pair_pitch": None,
        "jury_vote": None,
        "break_tie": None,
        "write_notes": None,
    }


def load_services():
    """Load real AI dependencies only when starting a terminal game."""
    from agents import (
        PERSONALITIES,
        SHOW_NAMES,
        agent_intro,
        agent_speak,
        agent_confess,
        agent_vote,
    )
    from host import (
        host_open,
        host_announce_pairs,
        host_announce_elimination,
    )
    from human import human_speak, human_vote

    return {
        "names": SHOW_NAMES,
        "active_roles": set(PERSONALITIES),
        "intro": agent_intro,
        "speak": agent_speak,
        "confess": agent_confess,
        "vote": agent_vote,
        "host_open": host_open,
        "host_pairs": host_announce_pairs,
        "host_elimination": host_announce_elimination,
        "human_speak": human_speak,
        "human_vote": human_vote,
        **future_hooks(),
    }


def new_game(players=None):
    players = list(
        DEFAULT_PLAYERS if players is None else players
    )

    if len(players) < 4 or len(players) % 2:
        raise ValueError(
            "The game needs an even number of at least four players."
        )

    if any(
        not isinstance(name, str) or not name
        for name in players
    ):
        raise ValueError(
            "Every player needs a non-empty role key."
        )

    if (
        len(set(players)) != len(players)
        or players.count(HUMAN_NAME) != 1
    ):
        raise ValueError(
            "Players must be unique and include exactly one 'You'."
        )

    return {
        "phase": "opening",
        "round": 0,
        "cast": players[:],
        "players": players,
        "pairs": [],
        "transcript": [],
        "confessionals": {},
        "notes": {},
        "votes": {},
        "eliminated": [],
        "round_history": [],
        "final_pitches": {},
        "jury_votes": {},
        "winner": None,
        "scores": {},
        "turn_index": 0,
        "waiting_for": None,
        "blocked_reason": None,
        "events": [],
    }


def show(name, names):
    if name not in names and name != HUMAN_NAME:
        raise ValueError(
            "A contestant is missing a show-name mapping."
        )

    return names.get(name, name)


def format_pairs(pairs, names):
    return "\n".join(
        f"Pair {i}: {show(a, names)} & {show(b, names)}"
        for i, (a, b) in enumerate(pairs)
    )


def make_pairs(players):
    if (
        not players
        or len(players) % 2
        or len(set(players)) != len(players)
    ):
        raise ValueError(
            "Pairing needs a non-empty, unique, even-sized roster."
        )

    shuffled = list(players)
    random.shuffle(shuffled)

    return [
        (shuffled[i], shuffled[i + 1])
        for i in range(0, len(shuffled), 2)
    ]


def find_my_pair(name, pairs):
    return next(
        (
            i
            for i, pair in enumerate(pairs)
            if name in pair
        ),
        None,
    )


def eligible_pairs(state, name):
    own_pair = find_my_pair(name, state["pairs"])

    if own_pair is None:
        raise ValueError(
            "An active voter is missing from the pairs."
        )

    return [
        i
        for i in range(len(state["pairs"]))
        if i != own_pair
    ]


def validate_ballot(ballot, options):
    """Accept current single votes or future complete rankings."""
    if type(ballot) is int:
        if ballot not in options:
            raise ValueError(
                "Vote must target an eligible pair."
            )

        return ballot

    if isinstance(ballot, list):
        if (
            any(type(item) is not int for item in ballot)
            or len(ballot) != len(options)
            or len(set(ballot)) != len(ballot)
            or set(ballot) != set(options)
        ):
            raise ValueError(
                "A ranking must include each eligible pair exactly once."
            )

        return ballot[:]

    raise ValueError(
        "Vote must be a pair number or a complete ranking."
    )


def vote_result(votes, pair_count=None):
    if not votes:
        raise ValueError(
            "Cannot count votes: no votes provided."
        )

    ballots = list(votes.values())
    ranked = all(
        isinstance(ballot, list)
        for ballot in ballots
    )

    if not ranked and not all(
        type(ballot) is int
        for ballot in ballots
    ):
        raise ValueError(
            "All ballots must use the same voting format."
        )

    if ranked and any(not ballot for ballot in ballots):
        raise ValueError(
            "Ranked ballots cannot be empty."
        )

    if ranked:
        for ballot in ballots:
            if (
                any(
                    type(item) is not int or item < 0
                    for item in ballot
                )
                or len(set(ballot)) != len(ballot)
                or (
                    pair_count is not None
                    and any(
                        item >= pair_count
                        for item in ballot
                    )
                )
            ):
                raise ValueError(
                    "Ranked ballots contain invalid or duplicate pair numbers."
                )

    tally = (
        {}
        if pair_count is None
        else dict.fromkeys(range(pair_count), 0)
    )

    for ballot in ballots:
        choice = ballot[0] if ranked else ballot

        if type(choice) is not int or choice < 0:
            raise ValueError("Invalid pair number.")

        if pair_count is not None and choice not in tally:
            raise ValueError(
                "Vote targets a pair outside the ballot."
            )

        tally[choice] = tally.get(choice, 0) + 1

    highest = max(tally.values())

    tied = [
        number
        for number, count in tally.items()
        if count == highest
    ]

    second_counts = {}

    if ranked and len(tied) > 1:
        second_counts = dict.fromkeys(tied, 0)

        for ballot in ballots:
            if (
                len(ballot) > 1
                and ballot[1] in second_counts
            ):
                second_counts[ballot[1]] += 1

        highest_second = max(second_counts.values())

        tied = [
            number
            for number in tied
            if second_counts[number] == highest_second
        ]

    return {
        "totals": tally,
        "second_choices": second_counts,
        "tied": tied,
        "ranked": ranked,
    }


def count_votes(votes):
    result = vote_result(votes)

    if result["ranked"] and len(result["tied"]) > 1:
        raise ValueError(
            "A ranked-vote tie requires the host tie-break hook."
        )

    return random.choice(result["tied"])


def eliminate_pair(state, pair_number):
    if (
        type(pair_number) is not int
        or not 0 <= pair_number < len(state["pairs"])
    ):
        raise ValueError(
            "Invalid elimination pair number."
        )

    pair = state["pairs"][pair_number]

    if (
        len(pair) != 2
        or any(
            name not in state["players"]
            for name in pair
        )
    ):
        raise ValueError(
            "The selected pair is not an active pair."
        )

    state["players"] = [
        name
        for name in state["players"]
        if name not in pair
    ]

    state["pairs"].pop(pair_number)
    state["eliminated"].extend(pair)

    return pair


def checked_text(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError(
            "A turn must contain non-empty text."
        )

    return text.strip()


def public_line(state, speaker, text):
    text = checked_text(text)
    message = f"{speaker}: {text}"

    state["transcript"].append(message)
    state["events"].append(message)


def move_to(state, phase):
    state.update(
        phase=phase,
        turn_index=0,
        waiting_for=None,
        blocked_reason=None,
    )


def need_input(state, kind, value):
    if value is NO_INPUT:
        state["waiting_for"] = kind
        return True

    return False


def block(state, message):
    state["blocked_reason"] = message
    return state


def call_with_notes(callback, arguments, state, name):
    """Forward own notes only when the adapter supports my_notes."""
    if "my_notes" in inspect.signature(callback).parameters:
        return callback(
            *arguments,
            my_notes=state["notes"].get(name, [])[:],
        )

    return callback(*arguments)


def host_tie_break(state, services, result, purpose):
    callback = services.get("break_tie")

    if callback is None:
        block(
            state,
            "Waiting for a team-provided host tie-break adapter.",
        )
        return None

    decision = callback(
        state["transcript"][:],
        state["pairs"][:],
        result["tied"][:],
        purpose,
    )

    if (
        not isinstance(decision, dict)
        or type(decision.get("pair_number")) is not int
        or decision["pair_number"] not in result["tied"]
        or not isinstance(decision.get("reason"), str)
        or not decision["reason"].strip()
    ):
        raise ValueError(
            "Host tie-break must choose a tied pair and give a reason."
        )

    public_line(
        state,
        "Caesar",
        decision["reason"],
    )

    return decision["pair_number"]


def step(state, services, player_input=NO_INPUT):
    """Advance one action or wait for human input or a missing hook.

    A future UI can store state in session state.
    Render events as public messages.
    Never render the entire private state to an active player.
    """
    state["events"] = []
    state["blocked_reason"] = None

    names = services["names"]
    phase = state["phase"]

    if phase == "finished":
        return state

    if (
        player_input is not NO_INPUT
        and state["waiting_for"] is None
    ):
        raise ValueError(
            "The engine is not waiting for player input."
        )

    if phase == "opening":
        for name in state["cast"]:
            show(name, names)

            if (
                name != HUMAN_NAME
                and name not in services["active_roles"]
            ):
                raise ValueError(
                    "A selected AI personality is not enabled in agents.py."
                )

        public_line(
            state,
            "Caesar",
            services["host_open"](state["cast"][:]),
        )

        move_to(state, "intro")

    elif phase in (
        "intro",
        "talk",
        "confessionals",
        "vote",
    ):
        index = state["turn_index"]
        name = state["players"][index]

        kind = {
            "intro": "intro",
            "talk": "speak",
            "confessionals": "confess",
            "vote": "vote",
        }[phase]

        if (
            name == HUMAN_NAME
            and need_input(state, kind, player_input)
        ):
            return state

        if name == HUMAN_NAME:
            answer = player_input

        elif phase == "intro":
            answer = services["intro"](name)

        elif phase in ("talk", "confessionals"):
            callback = services[
                "speak" if phase == "talk" else "confess"
            ]

            answer = call_with_notes(
                callback,
                (
                    name,
                    state["transcript"][:],
                    state["pairs"][:],
                ),
                state,
                name,
            )

        else:
            # Keep the current agent_vote's private output hidden.
            captured = io.StringIO()

            with redirect_stdout(captured):
                answer = call_with_notes(
                    services["vote"],
                    (
                        name,
                        state["transcript"][:],
                        state["pairs"][:],
                        state["confessionals"].get(name, ""),
                    ),
                    state,
                    name,
                )

            if "[ask_ai]" in captured.getvalue():
                state["events"].append(
                    "AI vote encountered a retry or fallback."
                )

        if phase == "vote":
            state["votes"][name] = validate_ballot(
                answer,
                eligible_pairs(state, name),
            )

        elif phase == "confessionals":
            state["confessionals"][name] = checked_text(answer)

        else:
            public_line(
                state,
                show(name, names),
                answer,
            )

        state["waiting_for"] = None
        state["turn_index"] += 1

        if state["turn_index"] == len(state["players"]):
            next_phase = {
                "intro": "pairing",
                "talk": "confessionals",
                "confessionals": "vote",
                "vote": "elimination",
            }[phase]

            move_to(state, next_phase)

            if next_phase == "vote":
                state["votes"] = {}

                state["events"].append(
                    format_pairs(state["pairs"], names)
                )

    elif phase == "pairing":
        state["pairs"] = make_pairs(state["players"])

        public_line(
            state,
            "Caesar",
            services["host_pairs"](state["pairs"][:]),
        )

        state["events"].append(
            format_pairs(state["pairs"], names)
        )

        if len(state["pairs"]) > 2:
            state["round"] = 1
            move_to(state, "talk")
        else:
            move_to(state, "final_pitches")

    elif phase == "elimination":
        if set(state["votes"]) != set(state["players"]):
            raise ValueError(
                "Every active contestant must cast one ballot."
            )

        for name, ballot in state["votes"].items():
            validate_ballot(
                ballot,
                eligible_pairs(state, name),
            )

        result = vote_result(
            state["votes"],
            len(state["pairs"]),
        )

        if len(result["tied"]) > 1 and result["ranked"]:
            out = host_tie_break(
                state,
                services,
                result,
                "eliminate",
            )

            if out is None:
                return state
        else:
            out = random.choice(result["tied"])

        before = state["pairs"][:]
        pair = before[out]

        announcement = services["host_elimination"](
            pair,
            state["transcript"][:],
        )

        public_line(
            state,
            "Caesar",
            announcement,
        )

        state["events"].append(
            f"Vote totals: {result['totals']}"
        )

        if len(result["tied"]) > 1:
            state["events"].append(
                "Single-vote tie resolved randomly for this version."
            )

        eliminate_pair(state, out)

        official = (
            f"ELIMINATED: "
            f"{show(pair[0], names)} & {show(pair[1], names)}"
        )

        state["transcript"].append(
            f"Game: {official}"
        )
        state["events"].append(official)

        state["round_history"].append({
            "round": state["round"],
            "pairs": before,
            "votes": {
                name: (
                    ballot[:]
                    if isinstance(ballot, list)
                    else ballot
                )
                for name, ballot in state["votes"].items()
            },
            "confessionals": dict(state["confessionals"]),
            "totals": result["totals"],
            "eliminated": pair,
        })

        move_to(state, "round_end")

    elif phase == "round_end":
        callback = services.get("write_notes")

        if callback is not None:
            participants = [
                name
                for pair in state["round_history"][-1]["pairs"]
                for name in pair
            ]

            for name in participants:
                if name == HUMAN_NAME:
                    continue

                previous = state["notes"].get(name, [])

                notes = callback(
                    name,
                    state["transcript"][:],
                    state["pairs"][:],
                    previous[:],
                )

                if (
                    not isinstance(notes, list)
                    or not 1 <= len(notes) <= 2
                    or any(
                        not isinstance(note, str)
                        or not note.strip()
                        for note in notes
                    )
                ):
                    raise ValueError(
                        "Memory notes must be one or two non-empty strings."
                    )

                state["notes"][name] = previous + notes

        if len(state["pairs"]) == 2:
            state["events"].append(
                "FINALISTS:\n"
                + format_pairs(state["pairs"], names)
            )

            move_to(state, "final_pitches")
        else:
            state["round"] += 1
            move_to(state, "talk")

    elif phase == "final_pitches":
        pair_number = state["turn_index"]

        if (
            pair_number == 0
            and services.get("pair_pitch") is None
        ):
            return block(
                state,
                "Waiting for a team-provided finalist-pair pitch adapter.",
            )

        pair = state["pairs"][pair_number]

        if HUMAN_NAME in pair:
            if need_input(state, "pitch", player_input):
                return state

            text = checked_text(player_input)

        else:
            callback = services.get("pair_pitch")

            if callback is None:
                return block(
                    state,
                    "Waiting for a team-provided finalist-pair pitch adapter.",
                )

            text = checked_text(
                callback(
                    pair,
                    state["transcript"][:],
                )
            )

        state["final_pitches"][pair_number] = text

        label = (
            f"{show(pair[0], names)} & {show(pair[1], names)}"
        )

        public_line(state, label, text)

        state["waiting_for"] = None
        state["turn_index"] += 1

        if state["turn_index"] == 2:
            move_to(state, "jury_vote")

    elif phase == "jury_vote":
        if not state["eliminated"]:
            return block(
                state,
                "The jury final needs eliminated contestants.",
            )

        name = state["eliminated"][state["turn_index"]]

        if name == HUMAN_NAME:
            if need_input(state, "jury_vote", player_input):
                return state

            ballot = player_input

        else:
            callback = services.get("jury_vote")

            if callback is None:
                return block(
                    state,
                    "Waiting for a team-provided jury vote-to-win adapter.",
                )

            ballot = call_with_notes(
                callback,
                (
                    name,
                    state["transcript"][:],
                    state["pairs"][:],
                    state["confessionals"].get(name, ""),
                ),
                state,
                name,
            )

        if type(ballot) is not int or ballot not in (0, 1):
            raise ValueError(
                "A jury vote must select finalist pair 0 or 1 to win."
            )

        state["jury_votes"][name] = ballot
        state["waiting_for"] = None
        state["turn_index"] += 1

        if state["turn_index"] == len(state["eliminated"]):
            move_to(state, "final_result")

    elif phase == "final_result":
        totals = {
            number: list(state["jury_votes"].values()).count(number)
            for number in (0, 1)
        }

        tied = [
            number
            for number, count in totals.items()
            if count == max(totals.values())
        ]

        if len(tied) > 1:
            winner = host_tie_break(
                state,
                services,
                {"tied": tied},
                "win",
            )

            if winner is None:
                return state

        else:
            winner = tied[0]

        state["winner"] = state["pairs"][winner]
        pair = state["winner"]

        state["events"].append(
            f"Jury totals: {totals}"
        )

        public_line(
            state,
            "Game",
            (
                f"WINNERS: "
                f"{show(pair[0], names)} & {show(pair[1], names)}"
            ),
        )

        move_to(state, "finished")

    else:
        raise ValueError("Unknown game phase.")

    return state


def read_player_input(state, services):
    kind = state["waiting_for"]

    if kind == "jury_vote":
        print(
            "Jury vote: choose the pair you want to WIN."
        )
        print(
            format_pairs(
                state["pairs"],
                services["names"],
            )
        )

        while True:
            choice = services["human_speak"](
                "Vote for the winning pair [0, 1]: "
            ).strip()

            if choice in ("0", "1"):
                return int(choice)

            print("Please enter 0 or 1.")

    if kind == "vote":
        own_pair = find_my_pair(
            HUMAN_NAME,
            state["pairs"],
        )

        return services["human_vote"](
            list(range(len(state["pairs"]))),
            own_pair,
            pairs=state["pairs"][:],
        )

    prompts = {
        "intro": "Introduce yourself: ",
        "speak": "Your turn to talk: ",
        "confess": "Your private confessional: ",
        "pitch": "Make your finalist pair's pitch: ",
    }

    return services["human_speak"](
        prompts[kind]
    )


def run_game(services=None, players=None):
    services = (
        load_services()
        if services is None
        else services
    )

    state = new_game(players)
    previous_phase = None
    answer = NO_INPUT

    while state["phase"] != "finished":
        if state["phase"] != previous_phase:
            print(
                f"\nCurrent phase: {state['phase']} "
                f"(round {state['round']})"
            )

            previous_phase = state["phase"]

        step(state, services, answer)
        answer = NO_INPUT

        for event in state["events"]:
            print(event)

        if state["blocked_reason"]:
            print(
                "\nPAUSED:",
                state["blocked_reason"],
            )
            print(
                "The engine has not declared a winner."
            )
            return state

        if state["waiting_for"]:
            answer = read_player_input(
                state,
                services,
            )

    return state


if __name__ == "__main__":
    try:
        run_game()
    except KeyboardInterrupt:
        print("\nGame stopped by the player.")