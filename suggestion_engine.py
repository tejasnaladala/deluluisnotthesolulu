"""
deluluisnotthesolulu: Text Suggestion Engine
Ghost-proof, vibe-optimized message drafts in your writing style.
"""

import sys
import io
import json
import urllib.request
import urllib.error
import sqlite3

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from data_engine import (
    get_recent_messages,
    get_vibe_trend,
    get_confidence_score,
)
import os
from pattern_detector import (
    word_impact_analysis,
    ghost_triggers,
    her_enthusiasm_triggers,
    time_of_day_sweet_spot,
    response_time_patterns,
)

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mixed_signals.db")
W = 68


def box_top(title=""):
    if title:
        pad = W - 4 - len(title)
        left = pad // 2
        right = pad - left
        return "+" + "=" * left + " " + title + " " + "=" * right + "+"
    return "+" + "=" * (W - 2) + "+"


def box_bot():
    return "+" + "=" * (W - 2) + "+"


def box_line(text=""):
    inner = W - 4
    return "| " + text.ljust(inner)[:inner] + " |"


def box_center(text):
    inner = W - 4
    return "| " + text.center(inner)[:inner] + " |"


def analyze_my_style():
    """Extract writing style stats from the user's messages."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT message_text FROM messages WHERE sender='me'")
    my_msgs = [r[0] for r in c.fetchall()]
    conn.close()

    if not my_msgs:
        return {}

    lengths = [len(m) for m in my_msgs]
    avg_len = sum(lengths) / len(lengths)

    # Question rate
    questions = sum(1 for m in my_msgs if "?" in m)
    q_rate = questions / len(my_msgs)

    # Exclamation rate
    excl = sum(1 for m in my_msgs if "!" in m)
    excl_rate = excl / len(my_msgs)

    # Common slang
    slang_counts = {}
    slang_words = ["fr", "tbh", "bro", "lmao", "lol", "ngl", "idk", "wyd",
                   "bet", "lowkey", "highkey", "ong", "smh", "bruh"]
    for word in slang_words:
        count = sum(1 for m in my_msgs if word in m.lower().split())
        if count > 0:
            slang_counts[word] = count

    # Common phrases
    phrase_counts = {}
    phrases = ["no worries", "sounds good", "all good", "for real",
               "thats crazy", "lmk", "wanna", "gonna", "gotta"]
    for phrase in phrases:
        count = sum(1 for m in my_msgs if phrase in m.lower())
        if count > 0:
            phrase_counts[phrase] = count

    # Greeting style
    greetings = {}
    for g in ["hey", "heyyy", "heyy", "yo", "sup", "good morning", "gm", "gn"]:
        count = sum(1 for m in my_msgs if m.lower().startswith(g))
        if count > 0:
            greetings[g] = count

    # Emoji check
    has_emoji = any(ord(ch) > 127 for m in my_msgs for ch in m)

    # Caps check
    all_caps = sum(1 for m in my_msgs if m.isupper() and len(m) > 2)

    return {
        "avg_length": round(avg_len, 1),
        "question_rate": round(q_rate * 100, 1),
        "excl_rate": round(excl_rate * 100, 1),
        "total_msgs": len(my_msgs),
        "slang": slang_counts,
        "phrases": phrase_counts,
        "greetings": greetings,
        "uses_emoji": has_emoji,
        "uses_caps": all_caps > 0,
    }


def build_system_prompt(style, word_data, ghost_data, enthus_data, resp_data):
    """Build the system prompt with style rules and pattern data."""

    # Style rules
    slang_list = ", ".join(style.get("slang", {}).keys()) or "none detected"
    phrase_list = ", ".join(style.get("phrases", {}).keys()) or "none detected"
    greeting_list = ", ".join(
        sorted(style.get("greetings", {}).keys(),
               key=lambda g: style["greetings"][g], reverse=True)
    ) or "hey"

    style_rules = (
        "STYLE RULES (you MUST follow these exactly):\n"
        "- Average message length: {avg} chars. Keep messages SHORT (15-30 chars ideal)\n"
        "- Tone: casual, direct, authentic. Never formal or try-hard\n"
        "- Slang this person uses naturally: {slang}\n"
        "- Common phrases: {phrases}\n"
        "- Greeting style: {greets}\n"
        "- Questions: {qrate}% of messages are questions. Mix them in naturally\n"
        "- NEVER use emoji. This person does not use emoji. Zero. None.\n"
        "- NEVER use all caps. Lowercase/normal case only\n"
        "- NEVER use ellipsis (...). Not their style\n"
        "- Punctuation is minimal. One ! max, usually none\n"
        "- No baby talk, no cutesy language, no uwu energy\n"
    ).format(
        avg=style.get("avg_length", 20),
        slang=slang_list,
        phrases=phrase_list,
        greets=greeting_list,
        qrate=style.get("question_rate", 15),
    )

    # Words that boost/kill vibe
    boosters = []
    killers = []
    for w in word_data:
        if w["delta"] > 0.05:
            boosters.append("'{}' ({:+.2f})".format(w["word"], w["delta"]))
        elif w["delta"] < -0.05:
            killers.append("'{}' ({:+.2f})".format(w["word"], w["delta"]))

    vibe_words = ""
    if boosters:
        vibe_words += "VIBE BOOSTERS (words that historically improve her response): "
        vibe_words += ", ".join(boosters[:5]) + "\n"
    if killers:
        vibe_words += "VIBE KILLERS (words that historically worsen her response): "
        vibe_words += ", ".join(killers[:5]) + "\n"

    # Ghost patterns to avoid
    ghost_summary = ""
    if isinstance(ghost_data, dict):
        gs = ghost_data.get("summary", "")
        if gs:
            ghost_summary = "GHOST TRIGGERS (patterns that led to no reply):\n{}\n".format(gs)
        instances = ghost_data.get("ghost_instances", [])[:3]
        if instances:
            ghost_summary += "Examples of messages that got ghosted:\n"
            for g in instances:
                ghost_summary += '  - "{}"\n'.format(
                    g.get("my_last_message", "?")[:60])

    # Enthusiasm triggers
    enthus_section = ""
    if enthus_data:
        enthus_section = "MESSAGES THAT GOT HER MOST EXCITED (learn from these):\n"
        for e in enthus_data[:5]:
            if isinstance(e, dict):
                enthus_section += '  - I said: "{}" -> She replied enthusiastically: "{}"\n'.format(
                    e.get("my_message", "?")[:50],
                    e.get("her_enthusiastic_reply", "?")[:50])

    # Response time intel
    resp_section = ""
    if resp_data:
        resp_section = "RESPONSE TIME DATA (what gets faster replies):\n"
        for cat, data in resp_data.items():
            if isinstance(data, dict):
                avg_t = data.get("avg_response_min", 0)
                n = data.get("sample_size", 0)
                resp_section += "  - {}: avg {:.0f}min reply ({} samples)\n".format(
                    cat.replace("_", " "), avg_t, n)

    system = (
        "You are a texting coach and ghostwriting expert. Your job is to draft "
        "text messages that sound EXACTLY like this person writes. You have deep "
        "knowledge of what works and what doesn't based on statistical analysis "
        "of their conversation history.\n\n"
        "{style_rules}\n"
        "{vibe_words}\n"
        "{ghost_summary}\n"
        "{enthus_section}\n"
        "{resp_section}\n"
        "OUTPUT FORMAT:\n"
        "For each suggestion, output EXACTLY this format:\n"
        "OPTION 1 (SAFE)\n"
        "Message: [the actual text message to send]\n"
        "Strategy: [1 sentence explaining why this works based on the data]\n"
        "Vibe confidence: [X]%\n\n"
        "OPTION 2 (BOLD)\n"
        "Message: [the actual text message to send]\n"
        "Strategy: [1 sentence explaining why this works]\n"
        "Vibe confidence: [X]%\n\n"
        "OPTION 3 (WILDCARD)\n"
        "Message: [the actual text message to send]\n"
        "Strategy: [1 sentence explaining the play here]\n"
        "Vibe confidence: [X]%\n\n"
        "IMPORTANT: Each message MUST be under 40 characters. Sound natural and "
        "casual. Reference the data when explaining strategy. Do not add emoji."
    ).format(
        style_rules=style_rules,
        vibe_words=vibe_words,
        ghost_summary=ghost_summary,
        enthus_section=enthus_section,
        resp_section=resp_section,
    )

    return system


def build_user_prompt(recent_msgs, trend, confidence, sweet):
    """Build the user prompt with conversation context."""

    # Format recent conversation
    convo_lines = []
    for m in recent_msgs:
        sender = "me" if m["sender"] == "me" else "her"
        convo_lines.append("[{}] {}: {}".format(
            m["timestamp"][11:16], sender, m["text"]))

    # Find her last message
    her_last = "..."
    for m in reversed(recent_msgs):
        if m["sender"] == "her":
            her_last = m["text"]
            break

    # Vibe context
    direction = trend.get("direction", "unknown")
    delta = trend.get("delta", 0)
    conf_score = confidence.get("score", 50)

    # Best time
    timing = ""
    if sweet:
        valid = [s for s in sweet if s.get("avg_vibe") is not None]
        if valid:
            best = max(valid, key=lambda s: s["avg_vibe"])
            timing = "Best time to text: {} (avg vibe {:.3f})".format(
                best["time_slot"], best["avg_vibe"])

    prompt = (
        "Here is our recent conversation:\n"
        "{convo}\n\n"
        "Current vibe trend: {dir} (delta: {delta:+.3f})\n"
        "Confidence she likes me: {conf:.0f}/100\n"
        "{timing}\n\n"
        "She last said: \"{her_last}\"\n\n"
        "Draft 3 reply options for me to send next. Make them sound exactly "
        "like how I text based on the conversation above."
    ).format(
        convo="\n".join(convo_lines),
        dir=direction,
        delta=delta,
        conf=conf_score,
        timing=timing,
        her_last=her_last,
    )

    return prompt, her_last


def call_ollama(system_prompt, user_prompt):
    """Stream a response from Ollama."""
    payload = json.dumps({
        "model": "qwen2.5:32b",
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": True,
        "options": {"temperature": 0.75, "num_predict": 500},
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=180)
    except (urllib.error.URLError, ConnectionError, OSError) as e:
        print("  [ERROR] Cant reach Ollama. Make sure its running:")
        print("    ollama serve")
        print("    (needs qwen2.5:32b model)")
        return ""
    result = []
    for line in resp:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            token = obj.get("response", "")
            result.append(token)
            sys.stdout.write(token)
            sys.stdout.flush()
        except json.JSONDecodeError:
            pass
        if obj.get("done"):
            break
    print()
    return "".join(result)


def main():
    print()
    print(box_top("TEXT SUGGESTION ENGINE"))
    print(box_center("ghost-proof, vibe-optimized drafts"))
    print(box_center("powered by delusion and data science"))
    print(box_bot())
    print()

    # Gather all data
    sys.stdout.write("  loading tactical data")
    sys.stdout.flush()

    style = analyze_my_style()
    sys.stdout.write(".")
    sys.stdout.flush()

    recent = get_recent_messages(20)
    sys.stdout.write(".")
    sys.stdout.flush()

    trend = get_vibe_trend()
    sys.stdout.write(".")
    sys.stdout.flush()

    confidence = get_confidence_score()
    sys.stdout.write(".")
    sys.stdout.flush()

    words = word_impact_analysis()
    sys.stdout.write(".")
    sys.stdout.flush()

    ghosts = ghost_triggers()
    sys.stdout.write(".")
    sys.stdout.flush()

    enthus = her_enthusiasm_triggers()
    sys.stdout.write(".")
    sys.stdout.flush()

    sweet = time_of_day_sweet_spot()
    sys.stdout.write(".")
    sys.stdout.flush()

    resp_times = response_time_patterns()
    print(" done.")
    print()

    # Show current situation
    direction = trend.get("direction", "unknown")
    delta = trend.get("delta", 0)
    conf_score = confidence.get("score", 50)

    her_last = "..."
    for m in reversed(recent):
        if m["sender"] == "her":
            her_last = m["text"]
            break

    print("  Current situation:")
    print('  She last said: "{}"'.format(her_last[:55]))
    print("  Vibe trend: {} ({:+.3f})  |  Confidence: {:.0f}/100".format(
        direction.upper(), delta, conf_score))
    print()

    # Style summary
    print("  Your style profile:")
    print("    avg msg length: {} chars  |  questions: {}%".format(
        style.get("avg_length", "?"), style.get("question_rate", "?")))
    slang = ", ".join(list(style.get("slang", {}).keys())[:6])
    print("    slang: {}  |  emoji: never".format(slang or "none"))
    print()

    # Build prompts
    system_prompt = build_system_prompt(style, words, ghosts, enthus, resp_times)
    user_prompt, _ = build_user_prompt(recent, trend, confidence, sweet)

    # Stream suggestions
    print(box_top("DRAFTING SUGGESTIONS"))
    print(box_center("<< streaming from qwen2.5:32b >>"))
    print(box_bot())
    print()

    call_ollama(system_prompt, user_prompt)
    print()

    # Timing advice
    if sweet:
        valid = [s for s in sweet if s.get("avg_vibe") is not None]
        if valid:
            best_slot = max(valid, key=lambda s: s["avg_vibe"])
            print("  timing advice: {} texts have best vibe ({:+.3f} avg)".format(
                best_slot["time_slot"], best_slot["avg_vibe"]))
            print()

    # Footer
    print(box_top())
    print(box_center("this is not financial advice. send at your own risk."))
    print(box_center("powered by love for juice wrld and a $600 mac mini"))
    print(box_bot())
    print()


if __name__ == "__main__":
    main()
