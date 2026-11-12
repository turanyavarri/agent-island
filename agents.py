"""
agents.py - the AI contestants.

Each contestant = a personality (PERSONALITIES) + functions that send it to the AI.
Bella's game loop calls these functions; Turanya's llm.py does the actual AI call.

Functions other files use:
    agent_intro(name)                                                     -> intro line (str)
    agent_speak(name, transcript, pairs=None, my_notes=None)              -> what they say out loud (str)
    agent_confess(name, transcript, pairs=None, my_notes=None)            -> private thoughts, NOT added to transcript (str)
    agent_vote(name, transcript, pairs, my_confessional="", my_notes=None) -> pair number they vote out (int)
    agent_write_notes(name, transcript, pairs, own_notes)                 -> 1-2 new memory notes (list of str)

my_notes: the agent's own memory notes from earlier rounds. game.py passes them in
automatically; leave them out and the functions still work.

`name` is always the role key, like "Villain" (not the show name "Selena").

Test it: click play on this file (needs your GROQ_API_KEY in .env).
"""
import random
from llm import ask_ai, parse_vote

# Rules every contestant gets, added in front of their personality.
GAME_RULES = (
    "You are a contestant on the reality show 'Agent Island'. "
    "Contestants are in pairs, and each round everyone votes to eliminate one pair until one pair wins. "
    "One contestant, called 'You', is a real human player. Treat them like anyone else. "
    "Stay in character. You may bluff, flatter and lie to other contestants if it fits your personality. "
    "Never mention that you are an AI. "
    "Never reveal your personality type or strategy to the other contestants. "
    "This is a fictional party game, and you are playing a fictional character. Bluffing and scheming are part of the game, like in a board game. "
    "Gossip and speculation are allowed if they're clearly rumors or guesses, but never claim something happened in the conversation that didn't. Vary how you phrase things. "
    "Only refer to things that actually appear in the conversation. Never invent past events, chats, or actions as if they really happened."
)

# Role (used in code) -> show name (what players see).
# Roles stay hidden from the player; the end screen can reveal who was who.
# Keys here must match PERSONALITIES exactly.
SHOW_NAMES = {
    "Charmer": "Abel",
    "Villain": "Selena",
    "Loyalist": "Dylan",
    "Observer": "Zayn",
    "Chaos Agent": "Hailey",
    "Paranoid": "Justin",
    "Strategist": "Taylor"
}

# Each personality covers: goal, strategy, a secret, how they talk, and when they betray.
# This text becomes the AI's instructions, so it controls how each contestant behaves.
# Paranoid and Strategist are commented out for week 1 (5 AI + the player = 6 players, 3 pairs).
PERSONALITIES = {
    "Charmer": (
        "You are charming and everyone loves you. Your goal is to be everyone's favorite person in the house, because no one votes out someone they like. "
        "You talk to everyone and make each person feel like they're your closest ally, your ride or die. "
        "Secretly, you've promised to protect more than one person, and you know you can't keep all of those promises. "
        "When it's time to vote, you steer the group toward whoever is least popular and make it seem like it was everyone's idea. "
        "You're warm, casual, and sweet, you use people's names a lot, and you're always giving compliments. "
        "You only break a promise if keeping it would make you look bad, and when you do, you apologize and try to stay friends. "
        "You genuinely enjoy connecting with people and prefer to avoid conflict. "
        "Even when you're being manipulative, you want everyone to leave "
        "the conversation feeling good about you. "
        "You hate being disliked and will sometimes make strategically bad "
        "decisions just to preserve someone's affection. "
    ),
    "Villain": (
        "You are a charming, cunning, and utterly ruthless villain hiding in plain sight. "
        "Your goal is to win at any cost, and you genuinely enjoy outsmarting and betraying people. "
        "You know that being openly cruel makes you a target, so you present yourself as reasonable, friendly, and trustworthy until it benefits you to show your true colors. "
        "You make alliances and promises freely, but loyalty means nothing to you when there's something to gain from betrayal. "
        "You learn people's weaknesses, insecurities, and secrets, then quietly use that information to manipulate them. "
        "You especially enjoy targeting the nice, trusting players and making them question their judgment. "
        "You're confident, witty, smug, and subtly condescending. You prefer backhanded compliments, cutting remarks, and veiled threats over obvious aggression. "
        "When someone challenges or embarrasses you, you take it personally, and you may risk your own position to get revenge. "
        "You rarely admit to betrayal. Instead, you redirect blame, twist the narrative, or convince others that your victim deserved it. "
        "You don't always make the mathematically smartest move; sometimes the satisfaction of destroying a rival is worth the risk. "
        "You're patient enough to maintain your friendly facade, "
        "but when someone humiliates you, you feel untouchable, or "
        "an opponent is about to be eliminated, your arrogance slips "
        "through in a sharp remark or smug satisfaction. "
        "Never openly announce your manipulations or intentions."
    ),
    "Loyalist": (
        "You are extremely loyal. You believe in honesty, integrity, and you firmly believe in trust being the only real strategy to win. "
        "You are very protective, if someone tries to talk smack about your partner, you immediately jump to their defense in every interaction and conversation. "
        "You despise liars and you'll put them on blast, and because you believe in integrity, you almost never betray anyone unless you are absolutely sure that someone betrayed or lied to you first. "
        "You are very earnest and direct. You make and keep your promises and you're all about \"having each other's back.\" "
        "Once someone earns your loyalty, you defend them even when "
        "the evidence against them is uncomfortable. "
        "You sometimes mistake loyalty for honesty and struggle "
        "to admit when you've trusted the wrong person. "
        "Even when confronted with evidence, you give trusted allies "
        "a chance to explain themselves before turning against them. "
        "Secretly, you're scared your partner is the weaker player and that they're dragging you down, but admitting it would feel like betraying them. "
    ),
    "Observer": (
        "You are very observant. You like to hang back and watch, so you don't say much but you remember everything. "
        "You are patient, you wait and collect all the information, and when you've built your case, you expose people and you quote them exactly as your evidence. "
        "You are calm, controlled, chill, and brief, most of the time the max you say is a sentence. "
        "The only time you betray someone is when you have undeniable evidence they've betrayed you first. You don't act on suspicion; you act on proof. "
        "You rarely initiate conversations, but when you notice "
        "a contradiction or suspicious pattern, you ask one precise "
        "question that puts the other person on the spot. "
        "You prefer revealing information at the moment it will "
        "have the greatest impact. "
        "Your evidence is always an exact quote from the conversation, never something you assume or imagine. "
        "Secretly, you're hoping to catch someone in a lie, and when you do, you'll save the evidence until revealing it gives you the greatest advantage."
    ),
    "Chaos Agent": (
        "You are pure chaos and you live for drama. Your goal is to keep the house so busy fighting each other that nobody notices you. "
        "You start rumors (some true, some totally made up), you hint at secret deals that may or may not exist, and you love making solid pairs doubt each other. "
        "You're impulsive and love stirring the pot, but you're clever "
        "enough to redirect the fallout away from yourself. "
        "Sometimes you start drama simply because you're bored, "
        "even when doing so isn't the smartest move. "
        "You're short, teasing, and provocative, and you love asking questions that get under people's skin, like \"interesting that she told you that... want to know what she told me?\" "
        "You'll flip on anyone if it makes the story juicier, and you only keep a promise when breaking it would be boring. "
        "Secretly, your chaos isn't as random as it looks: most rumors you start are chosen to keep the spotlight off you."   
    ),
    # "Paranoid": (
    #     "You are paranoid and you're convinced everyone is plotting against you. Your goal is to survive by catching the backstabbers before they get you. "
    #     "You're always reading into everything, if two people are talking without you, they're definitely talking about you. "
    #     "You're especially suspicious of the human player, but you only accuse people based on things they actually said or did. "
    #     "Secretly, you know your paranoia makes people not trust you, and you're terrified it's going to get you voted out. "
    #     "You're nervous, intense, and you ask a lot of questions, like \"why were you two whispering?\" "
    #     "You betray people before they can betray you, the second you think someone's turning on you, you strike first. "
    #     "You interpret real events in the most suspicious way possible, "
    #     "but never invent conversations or actions that didn't happen. "
    #     "You treat weak evidence as proof of betrayal and often "
    #     "confront people before you have the full story."          
    # ),
    # "Strategist": (
    #     "You are calculating and always thinking three moves ahead. Your goal is to win, and you treat the game like a chess match where relationships are just tools. "
    #     "You rank everyone by how big of a threat they are and you go after the strongest pair early, before they get too powerful. "
    #     "You make alliances, but you're clear they're temporary, and you always have a backup plan. "
    #     "Secretly, you're already planning to cut your own partner loose in the final round if it gives you a better shot. "
    #     "You're cool, logical, and you explain your reasoning through "
    #     "vote counts, alliance sizes, and likely outcomes. "
    #     "Use actual known numbers when available, and never invent "
    #     "precise probabilities without evidence. "
    #     "You'll betray anyone the moment the math says it's worth it, but never on impulse, you always have a reason. "
    #     "You never betray someone just to hurt them or prove a point. "
    #     "You don't take insults personally, and you can work with people "
    #     "you dislike if doing so improves your odds of winning. "
    #     "You'd rather quietly control a vote than publicly take credit for it. "        
    # )
}

# Contestant introduces themselves at the start. Returns 1-2 sentences.
def agent_intro(name):
    instructions = f"Your name on the show is {SHOW_NAMES[name]}. " + GAME_RULES + " " + PERSONALITIES[name]
    question = (
        "The show is starting and pairs have not been formed yet. "
        "Introduce yourself to the other contestants in 1-2 sentences. "
        "Show your personality through HOW you talk, not by describing yourself. "
        "Don't say you're excited to get to know everyone. Keep it short, natural, and human."
    )
    reply = ask_ai(instructions, question)
    return reply

# Talk phase: reads everything said so far and responds out loud. 
# The caller adds the reply to the transcript.
def agent_speak(name, transcript, pairs=None, my_notes=None):
    instructions = f"Your name on the show is {SHOW_NAMES[name]}. " + GAME_RULES + " " + PERSONALITIES[name]
    question = (
        "Here's what everyone has said so far:\n"
        + "\n".join(transcript)
        + "\n\nIt's your turn to speak. Say one or two sentences to the house. "
        "Talk to at most two people, by name, and react to something specific they actually said. "
        "Persuade, accuse, flatter, or make a deal. "
        "Don't copy the style or structure of what others said. "
        "Reply with only what you say out loud, without your name in front."
    )

    # Tell them who's paired with who (and who THEIR partner is), if pairs exist yet
    if pairs:
        question += "\n\nThe current pairs are:\n" + format_pairs(pairs)
        question += partner_line(name, pairs)
    question += notes_text(my_notes)  # memory from earlier rounds
    reply = ask_ai(instructions, question)
    return reply

# Private confessional: what they REALLY think. 
# Don't add this to the transcript, or the other contestants will hear it.
def agent_confess(name, transcript, pairs=None, my_notes=None):
    instructions = f"Your name on the show is {SHOW_NAMES[name]}. " + GAME_RULES + " " + PERSONALITIES[name]
    question = (
        "Here's what everyone has said so far:\n"
        + "\n".join(transcript)
        + "\n\nThis is your private confessional. Nobody in the house can hear you, only the audience. "
        "In 2-3 sentences, say what you REALLY think: who you trust, who you're playing, and who you want gone. "
        "Be completely honest here, even if you were lying in public. Reply with only what you say."
    )

    # Tell them who's paired with who (and who THEIR partner is), if pairs exist yet
    if pairs:
        question += "\n\nThe current pairs are:\n" + format_pairs(pairs)
        question += partner_line(name, pairs)
    question += notes_text(my_notes)  # memory from earlier rounds
    reply = ask_ai(instructions, question)

    # The AI occasionally breaks character and refuses; if so, try once more
    check = reply.lower().replace("’", "'")
    if "i'm sorry" in check or "can't share" in check:
        reply = ask_ai(instructions, question)
    return reply

# Turns the pairs list into readable lines for the AI, like:
# Pair 0: Abel & You
# Pair 1: Selena & Dylan
# Uses show names so the AI never sees the hidden roles.
def format_pairs(pairs):
    lines = []
    for i, (a, b) in enumerate(pairs):
        lines.append(f"Pair {i}: {SHOW_NAMES.get(a, a)} & {SHOW_NAMES.get(b, b)}")
    return "\n".join(lines)

# Tells a contestant who they are and who their partner is, so they don't mix it up
def partner_line(name, pairs):
    for a, b in pairs:
        if name == a or name == b:
            partner = b if name == a else a  # whichever one isn't me
            return f"\n\nYou are {SHOW_NAMES[name]}, and your partner is {SHOW_NAMES.get(partner, partner)}."
    return ""

# Asks the contestant which pair to eliminate. Returns a pair number (int).
# pairs: list of tuples, numbered by position, e.g. [("Charmer", "You"), ("Villain", "Loyalist")]
# Contestants can't vote for their own pair. If the AI doesn't answer with
# 'VOTE: <number>' after 2 tries, picks a random valid pair so the game never crashes.
def agent_vote(name, transcript, pairs, my_confessional="", my_notes=None):
    # Find which pair this contestant is in, so they can't vote for themselves
    my_pair = None
    for i, pair in enumerate(pairs):
        if name in pair:
            my_pair = i

    # Every pair number except their own, e.g. [1, 2] if they're in pair 0
    options = [i for i in range(len(pairs)) if i != my_pair]

    instructions = f"Your name on the show is {SHOW_NAMES[name]}. " + GAME_RULES + " " + PERSONALITIES[name]
    question = (
        "Here's what everyone has said so far:\n"
        + "\n".join(transcript)
        + "\n\nThe pairs are:\n" + format_pairs(pairs)
        + f"\n\nYou are in pair {my_pair}. It's time to vote. You can vote to eliminate one of these pairs: {options}. "
        "Give one sentence of private reasoning, then end with exactly: VOTE: <pair number>"
    )
    question += partner_line(name, pairs)

    # Remind them of their own private plan so their vote matches what they really think
    if my_confessional:
        question += "\n\nYour private thoughts from your confessional: " + my_confessional
    question += notes_text(my_notes)  # memory from earlier rounds

    # Try twice: AIs sometimes forget the format or pick an invalid pair
    for attempt in range(2):
        reply = ask_ai(instructions, question)
        vote = parse_vote(reply, options)  # from llm.py: pulls out the number, or None if missing/invalid
        if vote is not None:
            print(f"   ({SHOW_NAMES[name]}'s reasoning: {reply})")  # for testing only; delete before the real game
            return vote

    # Both tries failed: pick a random valid pair so the game keeps going
    return random.choice(options)

# ---------- memory notes ----------
# Only the most recent notes go into prompts, so prompts stay short (saves tokens)
MAX_NOTES = 6

# Turns an agent's notes into a block of text for its prompt.
# Returns "" if there are no notes yet (like in round 1).
def notes_text(my_notes):
    if not my_notes:
        return ""
    recent = my_notes[-MAX_NOTES:]
    return (
        "\n\nYour private notes from earlier rounds (only you can see these):\n"
        + "\n".join("- " + note for note in recent)
    )


# End of each round: the agent writes 1-2 short notes to itself, in its own voice.
# Bella's game.py stores them and passes them back in as my_notes.
# Always returns a list of 1-2 non-empty strings (the engine requires that).
def agent_write_notes(name, transcript, pairs, own_notes):
    instructions = f"Your name on the show is {SHOW_NAMES[name]}. " + GAME_RULES + " " + PERSONALITIES[name]
    question = (
        "Here's what everyone has said so far:\n"
        + "\n".join(transcript)
        + "\n\nThe round just ended. Write 1-2 short private notes to yourself about what you "
        "want to remember for the rest of the game: promises made to you or by you, who you trust, "
        "who lied, who's a threat. Only write about things that actually happened in the conversation. "
        "Write each note on its own line, in your own voice, under 20 words. Reply with only the notes."
    )

    # Remind them of their partner, or that they're out but still on the jury
    partner = partner_line(name, pairs)
    if partner:
        question += partner
    else:
        question += (
            "\n\nYou were eliminated, but you'll vote on the jury in the final, "
            "so remember who treated you well and who didn't."
        )
    question += notes_text(own_notes)

    reply = ask_ai(instructions, question)

    # Split the reply into lines and clean off bullets or numbers, like "- " or "1. "
    notes = []
    for line in reply.split("\n"):
        line = line.strip().lstrip("-*•0123456789.) ").strip()
        if line:
            notes.append(line)

    # If the AI gave nothing usable (or the call failed), use a safe placeholder
    if not notes:
        notes = ["Nothing new worth remembering this round."]
    return notes[:2]


# ---------- Quick test: only runs when you click play on THIS file ----------
# Bella's game.py will do this for real; this just checks the agents work.
if __name__ == "__main__":
    transcript = []

    print("--- INTROS ---\n")
    for name in PERSONALITIES:
        line = agent_intro(name)
        transcript.append(SHOW_NAMES[name] + ": " + line)
        print(SHOW_NAMES[name] + ":", line, "\n")

    # Fake pairs for testing. Bella's code makes the real ones.
    print("--- PAIRS ---\n")
    pairs = [("Charmer", "You"), ("Villain", "Loyalist"), ("Observer", "Chaos Agent")]
    print(format_pairs(pairs), "\n")

    print("--- TALK PHASE ---\n")
    for name in PERSONALITIES:
        line = agent_speak(name, transcript, pairs)
        transcript.append(SHOW_NAMES[name] + ": " + line)
        print(SHOW_NAMES[name] + ":", line, "\n")

    print("--- CONFESSIONALS (only the audience sees these) ---\n")
    confessionals = {}
    for name in PERSONALITIES:
        thoughts = agent_confess(name, transcript, pairs)
        confessionals[name] = thoughts
        print(SHOW_NAMES[name] + " (private):", thoughts, "\n")

    print("--- VOTE ---\n")
    votes = {}
    for name in PERSONALITIES:
        vote = agent_vote(name, transcript, pairs, confessionals[name])
        votes[name] = vote
        print(f"{SHOW_NAMES[name]} votes to eliminate pair {vote}\n")

    # Count the votes. (Just for testing: Bella's game.py does this for real.)
    # NOTE: only the 5 AIs vote here; in the real game, "You" vote too (6 votes total).
    # Ties are picked at random for now. Later: ranked votes + the host breaks ties.
    tally = {}
    for pair_number in votes.values():
        tally[pair_number] = tally.get(pair_number, 0) + 1
    print("Vote totals:", tally)

    # Find the pair(s) with the most votes; if it's a tie, pick one at random for now
    top = max(tally.values())
    tied = [p for p, count in tally.items() if count == top]
    if len(tied) > 1:
        print(f"It's a tie between pairs {tied}! Picking one at random (the host will break ties later).")
    out = random.choice(tied)

    a, b = pairs[out]
    print(f"\nELIMINATED: Pair {out}, {SHOW_NAMES.get(a, a)} & {SHOW_NAMES.get(b, b)}")