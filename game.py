import random

game = {
    "phase": "intro",
    "players": ["You", "Charmer", "Villain", "Loyalist", "Observer", "Chaos Agent"],
    "pairs": [],
    "transcript": [],
    "confessionals": {},
    "eliminated": [],
}
print("Current phase:", game["phase"])

for name in game["players"]:
    line = f"{name}: Hi, I'm {name}!"
    game["transcript"].append(line)
    print(line)

print("Number of messages:", len(game["transcript"]))

game["phase"] = "pairing"
print("Current phase:", game["phase"])

shuffled_players = game["players"].copy()
random.shuffle(shuffled_players)
print("Shuffled players:", shuffled_players)

for i in range(0, len(shuffled_players), 2):
    pair = (shuffled_players[i], shuffled_players[i + 1])
    game["pairs"].append(pair)

print("Pairs:", game["pairs"])