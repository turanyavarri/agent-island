"""llm.py - the one helper everyone uses to talk to the AI.

Usage:
    from llm import ask_ai, ask_ai_json, parse_vote

    reply = ask_ai("You are Charmer on a reality show...", "Introduce yourself.")
"""

import json
import re
import time

from groq import Groq
from dotenv import load_dotenv

load_dotenv()  # reads GROQ_API_KEY from the .env file

# Check https://console.groq.com/docs/models if this ever stops working
MODEL = "openai/gpt-oss-20b"
client = Groq()


def ask_ai(instructions, question, max_tokens=1000):
    """Send one prompt to the AI and return its text reply.

    Retries once if the API call fails. If it fails twice, returns "..."
    so the game keeps going instead of crashing.
    """
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_completion_tokens=max_tokens,  # includes the model's thinking, so keep it roomy
                reasoning_effort="low",            # faster replies; plenty for game dialogue
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": question},
                ],
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as error:
            print(f"[ask_ai] attempt {attempt + 1} failed: {error}")
            time.sleep(1)
    return "..."


def parse_vote(text, valid_options):
    """Find 'VOTE: 2' in an AI reply. Returns the number, or None if missing/invalid."""
    match = re.search(r"VOTE:\s*(\d+)", text, re.IGNORECASE)
    if match and int(match.group(1)) in valid_options:
        return int(match.group(1))
    return None


def parse_json(text):
    """Pull the first {...} block out of an AI reply. Returns a dict, or None."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def ask_ai_json(instructions, question, max_tokens=1000):
    """Ask for a JSON answer. Retries once if the reply isn't valid JSON.

    Returns a dict, or None if both tries fail (caller decides the fallback).
    """
    instructions += "\nRespond with only a single JSON object, no other text."
    for _ in range(2):
        result = parse_json(ask_ai(instructions, question, max_tokens))
        if result is not None:
            return result
    return None


if __name__ == "__main__":
    # Quick test: python llm.py
    # REMEMBER: We want to give host a personality similar to Caeser Flickerman
    print(ask_ai("You are a dramatic reality TV host.", "Welcome the contestants in one sentence."))