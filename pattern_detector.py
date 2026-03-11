import sqlite3
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mixed_signals.db")


def _connect():
    return sqlite3.connect(DB)


def word_impact_analysis():
    """For common words/phrases I use, compare average daily vibe on days
    I used that word vs days I didn't. Return sorted by abs(delta) desc."""

    words = [
        "haha", "lmao", "lol", "hahaha", "good morning", "gm", "wyd",
        "?", "!", "miss you", "tbh", "ngl", "fr", "bro", "dude",
    ]

    conn = _connect()
    cur = conn.cursor()

    # Get all my messages grouped by date with their text
    cur.execute("""
        SELECT DATE(timestamp) AS day, message_text
        FROM messages
        WHERE sender = 'me'
    """)
    my_messages_by_day = defaultdict(list)
    for day, text in cur.fetchall():
        my_messages_by_day[day].append(text.lower() if text else "")

    # Get all daily vibe scores
    cur.execute("SELECT date, vibe_score FROM daily_vibes")
    daily_vibes = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()

    all_days = set(daily_vibes.keys())
    results = []

    for word in words:
        # Find days where any of my messages contain this word
        days_used = set()
        for day, texts in my_messages_by_day.items():
            for text in texts:
                if word.lower() in text:
                    days_used.add(day)
                    break

        # Only include if used on at least 3 days
        if len(days_used) < 3:
            continue

        days_not_used = all_days - days_used

        # Only consider days that have vibe scores
        vibes_when_used = [daily_vibes[d] for d in days_used if d in daily_vibes]
        vibes_when_not = [daily_vibes[d] for d in days_not_used if d in daily_vibes]

        if not vibes_when_used or not vibes_when_not:
            continue

        avg_used = sum(vibes_when_used) / len(vibes_when_used)
        avg_not = sum(vibes_when_not) / len(vibes_when_not)
        delta = avg_used - avg_not

        if delta > 0.3:
            verdict = "positive_vibes"
        elif delta < -0.3:
            verdict = "kills_the_vibe"
        else:
            verdict = "no_significant_effect"

        results.append({
            "word": word,
            "days_used": len(days_used),
            "avg_vibe_when_used": round(avg_used, 4),
            "avg_vibe_when_not": round(avg_not, 4),
            "delta": round(delta, 4),
            "verdict": verdict,
        })

    results.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return results


def ghost_triggers():
    """Find days where I sent messages but she didn't reply at all.
    Return the last message I sent before each ghost, plus a summary."""

    conn = _connect()
    cur = conn.cursor()

    # Find ghost days: I messaged, she didn't reply
    cur.execute("""
        SELECT date, my_msg_count
        FROM daily_vibes
        WHERE her_msg_count = 0 AND my_msg_count > 0
    """)
    ghost_days = cur.fetchall()

    ghost_list = []
    all_last_messages = []

    for date, my_count in ghost_days:
        # Get my last message on that day
        cur.execute("""
            SELECT message_text
            FROM messages
            WHERE sender = 'me' AND DATE(timestamp) = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (date,))
        row = cur.fetchone()
        last_msg = row[0] if row else ""

        ghost_list.append({
            "date": date,
            "my_last_message": last_msg,
            "my_msg_count_that_day": my_count,
        })
        all_last_messages.append(last_msg.lower() if last_msg else "")

    conn.close()

    # Summarize common patterns in ghost-trigger messages
    patterns = {
        "questions": 0,
        "double_texts": 0,
        "short_messages": 0,
        "long_messages": 0,
        "contains_lol_lmao": 0,
        "good_morning_texts": 0,
        "late_night": 0,
    }

    for entry in ghost_list:
        msg = entry["my_last_message"].lower() if entry["my_last_message"] else ""
        if "?" in msg:
            patterns["questions"] += 1
        if entry["my_msg_count_that_day"] >= 3:
            patterns["double_texts"] += 1
        if len(msg) < 20:
            patterns["short_messages"] += 1
        if len(msg) >= 50:
            patterns["long_messages"] += 1
        if "lol" in msg or "lmao" in msg:
            patterns["contains_lol_lmao"] += 1
        if "good morning" in msg or "gm" in msg:
            patterns["good_morning_texts"] += 1

    # Find most common words across ghost-trigger messages
    word_counter = Counter()
    for msg in all_last_messages:
        tokens = re.findall(r"[a-z']+", msg)
        word_counter.update(tokens)

    # Remove very common stop words
    stop = {"i", "a", "the", "to", "and", "is", "it", "you", "me", "my",
            "in", "of", "that", "was", "for", "on", "so", "but", "do", "at",
            "be", "if", "or", "an", "am", "im", "ur", "u"}
    common_ghost_words = [
        w for w, _ in word_counter.most_common(20) if w not in stop
    ]

    summary = {
        "total_ghost_days": len(ghost_list),
        "pattern_counts": patterns,
        "common_words_in_ghost_messages": common_ghost_words[:10],
    }

    return {"ghost_instances": ghost_list, "summary": summary}


def response_time_patterns():
    """Analyze my message -> her next reply pairs. Categorize my messages
    by length and question vs statement. Return avg response times."""

    conn = _connect()
    cur = conn.cursor()

    # Get all messages in chronological order
    cur.execute("""
        SELECT timestamp, sender, message_text
        FROM messages
        ORDER BY timestamp ASC
    """)
    messages = cur.fetchall()
    conn.close()

    categories = {
        "short_question": [],
        "short_statement": [],
        "long_question": [],
        "long_statement": [],
    }

    # Walk through messages, find my message -> her next reply pairs
    i = 0
    while i < len(messages) - 1:
        ts, sender, text = messages[i]
        if sender == "me" and text:
            # Look for her next reply
            j = i + 1
            while j < len(messages):
                next_ts, next_sender, next_text = messages[j]
                if next_sender == "her":
                    # Calculate response time
                    try:
                        my_time = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                        her_time = datetime.strptime(next_ts, "%Y-%m-%d %H:%M:%S")
                        diff_min = (her_time - my_time).total_seconds() / 60.0
                    except (ValueError, TypeError):
                        break

                    # Only count reasonable response times (within 24 hours)
                    if diff_min < 0 or diff_min > 1440:
                        break

                    is_short = len(text) < 20
                    is_question = "?" in text

                    if is_short and is_question:
                        categories["short_question"].append(diff_min)
                    elif is_short and not is_question:
                        categories["short_statement"].append(diff_min)
                    elif not is_short and is_question:
                        categories["long_question"].append(diff_min)
                    else:
                        categories["long_statement"].append(diff_min)
                    break
                elif next_sender == "me":
                    # I double-texted, skip to next pair
                    break
                j += 1
        i += 1

    result = {}
    for cat, times in categories.items():
        if times:
            result[cat] = {
                "avg_response_min": round(sum(times) / len(times), 2),
                "median_response_min": round(sorted(times)[len(times) // 2], 2),
                "sample_size": len(times),
            }
        else:
            result[cat] = {
                "avg_response_min": None,
                "median_response_min": None,
                "sample_size": 0,
            }

    return result


def her_enthusiasm_triggers():
    """Find her most enthusiastic messages and what I said right before.
    Return top 10 of my messages that preceded her enthusiastic ones."""

    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT timestamp, sender, message_text
        FROM messages
        ORDER BY timestamp ASC
    """)
    messages = cur.fetchall()
    conn.close()

    # Pattern for repeated letters (e.g., "hiii", "yesss", "omggg")
    repeated_letters = re.compile(r"(.)\1{2,}")

    def is_enthusiastic(text):
        if not text:
            return False
        t = text.lower()
        indicators = 0
        if "!" in t:
            indicators += 1
        if ":)" in t:
            indicators += 1
        if "<3" in t:
            indicators += 1
        if ";)" in t:
            indicators += 1
        if repeated_letters.search(t):
            indicators += 1
        # Count multiple exclamation marks as extra enthusiasm
        if t.count("!") >= 2:
            indicators += 1
        return indicators >= 1

    triggers = []

    for i in range(1, len(messages)):
        ts, sender, text = messages[i]
        if sender == "her" and is_enthusiastic(text):
            # Look backwards for my most recent message
            for j in range(i - 1, -1, -1):
                prev_ts, prev_sender, prev_text = messages[j]
                if prev_sender == "me" and prev_text:
                    # Score enthusiasm level for ranking
                    enthusiasm_score = 0
                    t = text.lower()
                    enthusiasm_score += t.count("!")
                    if ":)" in t:
                        enthusiasm_score += 2
                    if "<3" in t:
                        enthusiasm_score += 3
                    if ";)" in t:
                        enthusiasm_score += 2
                    if repeated_letters.search(t):
                        enthusiasm_score += 2

                    triggers.append({
                        "my_message": prev_text,
                        "her_enthusiastic_reply": text,
                        "enthusiasm_score": enthusiasm_score,
                        "timestamp": ts,
                    })
                    break

    # Sort by enthusiasm score descending and take top 10
    triggers.sort(key=lambda x: x["enthusiasm_score"], reverse=True)
    return triggers[:10]


def time_of_day_sweet_spot():
    """Bucket messages by hour range and find which time slot has the
    best average daily vibe when most messages fall in that slot."""

    conn = _connect()
    cur = conn.cursor()

    # Get all messages with their hours
    cur.execute("""
        SELECT DATE(timestamp) AS day,
               CAST(STRFTIME('%H', timestamp) AS INTEGER) AS hour
        FROM messages
    """)
    rows = cur.fetchall()

    # Get daily vibes
    cur.execute("SELECT date, vibe_score FROM daily_vibes")
    daily_vibes = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()

    def get_slot(hour):
        if 6 <= hour <= 11:
            return "morning"
        elif 12 <= hour <= 17:
            return "afternoon"
        elif 18 <= hour <= 22:
            return "evening"
        else:
            return "late_night"

    # Count messages per slot per day
    day_slot_counts = defaultdict(lambda: defaultdict(int))
    slot_total_msgs = defaultdict(int)

    for day, hour in rows:
        slot = get_slot(hour)
        day_slot_counts[day][slot] += 1
        slot_total_msgs[slot] += 1

    # For each day, find the dominant time slot
    slot_vibes = defaultdict(list)

    for day, slot_counts in day_slot_counts.items():
        if day not in daily_vibes:
            continue
        # Find the slot with the most messages that day
        dominant_slot = max(slot_counts, key=slot_counts.get)
        slot_vibes[dominant_slot].append(daily_vibes[day])

    result = []
    for slot in ["morning", "afternoon", "evening", "late_night"]:
        vibes = slot_vibes.get(slot, [])
        avg_vibe = round(sum(vibes) / len(vibes), 4) if vibes else None
        result.append({
            "time_slot": slot,
            "avg_vibe": avg_vibe,
            "msg_count": slot_total_msgs.get(slot, 0),
            "days_dominant": len(vibes),
        })

    return result
