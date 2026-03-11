"""
deluluisnotthesolulu: Screenshot Ingestion Pipeline
Drop chat screenshots into screenshots/ folder, run this script to parse and ingest.
Supports: iMessage, Instagram DMs, WhatsApp, Snapchat, any chat app.
Uses minicpm-v vision model via Ollama for OCR + layout understanding.
"""

import sys
import io
import os
import json
import base64
import glob
import shutil
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime, timedelta

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mixed_signals.db")
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
PROCESSED_DIR = os.path.join(SCREENSHOT_DIR, "processed")
OLLAMA_URL = "http://localhost:11434/api/generate"
VISION_MODEL = "minicpm-v:8b"

EXTRACT_PROMPT = """You are an OCR tool. Read this Instagram DM screenshot EXACTLY as shown. Do NOT make up or invent any messages. Only transcribe text you can actually see in the image.

In Instagram DMs:
- Messages on the RIGHT side (bright/cyan colored bubbles) are sent by "me"
- Messages on the LEFT side (darker bubbles, often with a small profile picture) are sent by "her"

For each visible message bubble, transcribe the EXACT text. Output one message per line, top to bottom:
me: exact message text
her: exact message text

Rules:
- ONLY transcribe text you can actually SEE in the bubbles. Do NOT generate or guess messages.
- If you can only see 5 messages, output exactly 5 lines. Do NOT pad with extra messages.
- Copy the exact wording, spelling, slang, and emojis from the screenshot.
- Skip shared reels/posts/videos -just write [reel] instead.
- Skip emoji reactions between messages.
- Do NOT include "Delivered", "Read", "Seen", or typing indicators.
- Ignore contact names, headers, and UI elements at the top.
- If unsure about a word, write [unclear] instead of guessing."""


def ensure_dirs():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)


def ensure_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        sender TEXT NOT NULL CHECK(sender IN ('me', 'her')),
        message_text TEXT NOT NULL,
        vibe_score REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS daily_vibes (
        date TEXT PRIMARY KEY,
        vibe_score REAL NOT NULL,
        msg_count INTEGER,
        her_msg_count INTEGER,
        my_msg_count INTEGER,
        she_initiated INTEGER,
        avg_her_response_min REAL,
        her_avg_len REAL,
        my_avg_len REAL,
        commentary TEXT
    )""")
    conn.commit()
    conn.close()


def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def call_llava(image_path):
    """Send image to LLaVA via Ollama and get extracted messages."""
    img_b64 = image_to_base64(image_path)

    payload = json.dumps({
        "model": VISION_MODEL,
        "prompt": EXTRACT_PROMPT,
        "images": [img_b64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2000},
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        resp = urllib.request.urlopen(req, timeout=300)
        result = json.loads(resp.read().decode())
        return result.get("response", "")
    except urllib.error.URLError:
        print("  [ERROR] Cannot reach Ollama. Make sure its running: ollama serve")
        print("  [ERROR] And that you have minicpm-v:8b: ollama pull minicpm-v:8b")
        return None
    except Exception as e:
        print("  [ERROR] Vision model call failed: {}".format(e))
        return None


def parse_messages(llm_output):
    """Parse LLM output into list of (sender, text, time_str_or_None) tuples."""
    import re
    messages = []
    for line in llm_output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        # Try to extract optional timestamp prefix like "2:34 PM" or "9:41 AM"
        time_str = None
        time_match = re.match(r'^(\d{1,2}:\d{2}\s*[APap][Mm])\s+', line)
        if time_match:
            time_str = time_match.group(1).strip()
            line = line[time_match.end():]

        # Also try "Yesterday 2:34 PM" or "Today 9:41 AM" style
        if not time_match:
            time_match2 = re.match(r'^(?:yesterday|today|tomorrow)?\s*(\d{1,2}:\d{2}\s*[APap][Mm])\s+', line, re.IGNORECASE)
            if time_match2:
                time_str = time_match2.group(1).strip()
                line = line[time_match2.end():]

        if line.lower().startswith("me:"):
            text = line[3:].strip()
            if text and _is_valid_message(text):
                messages.append(("me", text, time_str))
        elif line.lower().startswith("her:"):
            text = line[4:].strip()
            if text and _is_valid_message(text):
                messages.append(("her", text, time_str))
    return messages


# Junk patterns to filter out from OCR output
_JUNK = {
    "[unclear]", "[photo]", "[image]", "[sticker]", "[voice message]",
    "[reel]", "[post]", "[video]", "[gif]", "[link]",
    "replied to you", "replied to your story", "you replied",
    "sent an attachment", "liked a message", "reacted to your message",
    "typing...", "delivered", "read", "seen", "active now",
}

def _is_valid_message(text):
    """Filter out OCR junk: UI artifacts, reel usernames, reactions, etc."""
    t = text.lower().strip()
    # Exact match junk
    if t in _JUNK:
        return False
    # Starts with known junk
    if t.startswith("replied to"):
        return False
    # Looks like an Instagram username (word_word or word.word, no spaces)
    if not " " in t and ("_" in t or "." in t) and len(t) < 30:
        return False
    # Pure emoji-only messages shorter than 3 chars (reactions, not real msgs)
    import re
    stripped = re.sub(r'[\U00010000-\U0010ffff]', '', t, flags=re.UNICODE).strip()
    if not stripped and len(t) <= 4:
        return False
    return True


def get_screenshot_date(filepath):
    """Try to determine the date of the screenshot from filename or metadata."""
    basename = os.path.basename(filepath)

    # Try common date patterns in filenames
    import re
    # Pattern: 2026-03-10 or 20260310
    match = re.search(r"(\d{4})-?(\d{2})-?(\d{2})", basename)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    # Fall back to file modification time
    mtime = os.path.getmtime(filepath)
    return datetime.fromtimestamp(mtime)


def insert_messages(messages, base_date):
    """Insert parsed messages into the database.
    Uses real timestamps from screenshots when available.
    Falls back to sequential ordering with unknown exact times.
    """
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Track last known time for fallback sequencing
    last_hour = 9
    last_min = 0
    msg_index = 0
    inserted = 0
    day_str = base_date.strftime("%Y-%m-%d")

    for sender, text, time_str in messages:
        # Try to use real timestamp from screenshot
        if time_str:
            try:
                import re
                m = re.match(r'(\d{1,2}):(\d{2})\s*([APap][Mm])', time_str)
                if m:
                    h = int(m.group(1))
                    mn = int(m.group(2))
                    ampm = m.group(3).upper()
                    if ampm == "PM" and h != 12:
                        h += 12
                    elif ampm == "AM" and h == 12:
                        h = 0
                    last_hour = h
                    last_min = mn
            except Exception:
                pass

        ts = "{} {:02d}:{:02d}:{:02d}".format(day_str, last_hour, last_min, msg_index % 60)

        # Check for duplicates (same sender + similar text within same day)
        existing = c.execute(
            "SELECT COUNT(*) FROM messages WHERE sender=? AND message_text=? AND timestamp LIKE ?",
            (sender, text, day_str + "%")
        ).fetchone()[0]

        if existing == 0:
            c.execute(
                "INSERT INTO messages (timestamp, sender, message_text, vibe_score) VALUES (?, ?, ?, NULL)",
                (ts, sender, text)
            )
            inserted += 1

        # If no real timestamp, advance by 1 minute for ordering purposes
        if not time_str:
            last_min += 1
            if last_min >= 60:
                last_min = 0
                last_hour += 1

        msg_index += 1

    conn.commit()
    conn.close()
    return inserted


def rescore():
    """Re-run the vibe scoring pipeline after ingestion."""
    try:
        # Import and run score_vibes logic
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "score_vibes",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "score_vibes.py")
        )
        sv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sv)
        sv.main()
    except Exception as e:
        print("  [WARN] Auto-rescore failed: {}".format(e))
        print("  Run manually: python3 score_vibes.py")


def reset_db():
    """Wipe all data and start fresh."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM messages")
    c.execute("DELETE FROM daily_vibes")
    conn.commit()
    count = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()
    print("  Database wiped. {} messages remaining.".format(count))


def main():
    print()
    print("+{0}+".format("=" * 60))
    print("| {0} |".format("deluluisnotthesolulu: SCREENSHOT INGESTION".center(58)))
    print("| {0} |".format("drop screenshots -> extract messages -> feed the db".center(58)))
    print("+{0}+".format("=" * 60))
    print()

    ensure_dirs()
    ensure_db()

    # Handle --reset flag
    if "--reset" in sys.argv:
        print("  [!] Resetting database...")
        reset_db()
        print("  Database is clean. Drop screenshots into:")
        print("  {}".format(SCREENSHOT_DIR))
        return

    # Find new screenshots
    extensions = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
    screenshots = []
    for ext in extensions:
        screenshots.extend(glob.glob(os.path.join(SCREENSHOT_DIR, ext)))

    # Filter out already-processed (in processed/ subdir)
    screenshots = [s for s in screenshots
                   if os.path.dirname(os.path.abspath(s)) != os.path.abspath(PROCESSED_DIR)]

    if not screenshots:
        print("  No new screenshots found.")
        print("  Drop chat screenshots into: {}".format(SCREENSHOT_DIR))
        print()
        print("  Supported: .png, .jpg, .jpeg")
        print("  Supported apps: iMessage, Instagram, WhatsApp, Snapchat, any chat app")
        print()
        print("  Usage:")
        print("    python3 ingest.py          # process new screenshots")
        print("    python3 ingest.py --reset   # wipe db and start fresh")
        return

    print("  Found {} new screenshot(s)".format(len(screenshots)))
    print()

    total_inserted = 0

    for i, filepath in enumerate(sorted(screenshots)):
        fname = os.path.basename(filepath)
        print("  [{}/{}] Processing: {}".format(i + 1, len(screenshots), fname))

        # Skip if file was already moved (e.g. from a previous partial run)
        if not os.path.exists(filepath):
            print("    [SKIP] file already processed or missing")
            continue

        # Extract messages via LLaVA
        sys.stdout.write("    sending to minicpm-v:8b...")
        sys.stdout.flush()
        raw_output = call_llava(filepath)

        if raw_output is None:
            print(" FAILED")
            continue

        print(" done")

        # Show raw output for debugging
        print("    --- raw LLaVA output ---")
        for rline in raw_output.strip().split("\n")[:8]:
            print("    | {}".format(rline.rstrip()[:80]))
        raw_lines = raw_output.strip().split("\n")
        if len(raw_lines) > 8:
            print("    | ... ({} more lines)".format(len(raw_lines) - 8))
        print("    ---")

        # Parse
        messages = parse_messages(raw_output)
        print("    extracted {} messages".format(len(messages)))

        if not messages:
            print("    [WARN] No messages found in screenshot. Skipping.")
            shutil.move(filepath, os.path.join(PROCESSED_DIR, fname))
            continue

        # Show preview
        for sender, text, ts in messages[:5]:
            ts_tag = " @{}".format(ts) if ts else ""
            print("      [{}]{} {}".format(sender, ts_tag, text[:60]))
        if len(messages) > 5:
            print("      ... and {} more".format(len(messages) - 5))

        # Get date
        base_date = get_screenshot_date(filepath)
        print("    date: {}".format(base_date.strftime("%Y-%m-%d")))

        # Insert
        inserted = insert_messages(messages, base_date)
        total_inserted += inserted
        print("    inserted {} new messages".format(inserted))

        # Move to processed
        shutil.move(filepath, os.path.join(PROCESSED_DIR, fname))
        print("    moved to processed/")
        print()

    print("+{0}+".format("-" * 60))
    print("  Total new messages ingested: {}".format(total_inserted))
    print("+{0}+".format("-" * 60))

    if total_inserted > 0:
        print()
        print("  Re-scoring vibes...")
        rescore()
        print()
        print("  Done! Run the dashboard to see updated data:")
        print("    python3 dashboard.py")
    print()


if __name__ == "__main__":
    main()
