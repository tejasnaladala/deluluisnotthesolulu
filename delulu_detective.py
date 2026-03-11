"""
deluluisnotthesolulu -Main Orchestrator
Analyzes texting patterns like game tape. Calls a local LLM via Ollama.
"""

import json
import sys
import time
import urllib.request
import urllib.error
import io

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from data_engine import (
    get_vibe_trend,
    get_daily_summary,
    get_confidence_score,
    get_correlation_highlights,
    get_recent_messages,
)
from pattern_detector import (
    word_impact_analysis,
    ghost_triggers,
    response_time_patterns,
    her_enthusiasm_triggers,
    time_of_day_sweet_spot,
)

# ---------------------------------------------------------------------------
# ASCII art & display helpers
# ---------------------------------------------------------------------------

HEADER = r"""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ██████╗ ███████╗██╗     ██╗   ██╗██╗     ██╗   ██╗            ║
║   ██╔══██╗██╔════╝██║     ██║   ██║██║     ██║   ██║            ║
║   ██║  ██║█████╗  ██║     ██║   ██║██║     ██║   ██║            ║
║   ██║  ██║██╔══╝  ██║     ██║   ██║██║     ██║   ██║            ║
║   ██████╔╝███████╗███████╗╚██████╔╝███████╗╚██████╔╝            ║
║   ╚═════╝ ╚══════╝╚══════╝ ╚═════╝ ╚══════╝ ╚═════╝            ║
║                                                                  ║
║   ██████╗ ███████╗████████╗███████╗ ██████╗████████╗██╗██╗   ██╗███████╗ ║
║   ██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝██║██║   ██║██╔════╝ ║
║   ██║  ██║█████╗     ██║   █████╗  ██║        ██║   ██║██║   ██║█████╗   ║
║   ██║  ██║██╔══╝     ██║   ██╔══╝  ██║        ██║   ██║╚██╗ ██╔╝██╔══╝   ║
║   ██████╔╝███████╗   ██║   ███████╗╚██████╗   ██║   ██║ ╚████╔╝ ███████╗ ║
║   ╚═════╝ ╚══════╝   ╚═╝   ╚══════╝ ╚═════╝   ╚═╝   ╚═╝  ╚═══╝  ╚══════╝ ║
║                                                                  ║
║          "past vibe performance is not indicative                ║
║                    of future results"                            ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""

DISCLAIMER = """
================================================================
DISCLAIMER: this is not financial advice. past vibe performance
is not indicative of future results. deluluisnotthesolulu is not
a licensed therapist, relationship counselor, or functioning adult.
================================================================
"""

SYSTEM_PROMPT = (
    "You are deluluisnotthesolulu -a legendary SPORTS COMMENTATOR who analyzes "
    "texting patterns the way ESPN analysts break down game tape. You are dramatic, "
    "funny, and incapable of speaking about relationships without using sports "
    "metaphors. Think Stephen A. Smith meets a relationship advice column.\n\n"
    "Your style rules:\n"
    "- Analyze every data point like it's a crucial play: fumbles, assists, "
    "three-pointers, slam dunks, red cards, penalty kicks, Hail Marys, etc.\n"
    "- Occasionally break into full play-by-play commentary mid-analysis.\n"
    "- Be genuinely funny. Roast the user when the data warrants it.\n"
    "- Despite the comedy, ALWAYS reference the REAL numbers and data provided. "
    "Do not make up statistics.\n\n"
    "Structure your analysis EXACTLY like this:\n\n"
    "## 1. THE VIBE REPORT\n"
    "Summarize the vibe trend data with full sports energy. Are we on a winning "
    "streak or in a rebuilding year? Give the play-by-play on momentum.\n\n"
    "## 2. PATTERN RECOGNITION\n"
    "Break down the flagged patterns (word impact, ghost triggers, response times, "
    "enthusiasm triggers, best texting times) with tactical implications. "
    "What plays are working? What's getting intercepted?\n\n"
    "## 3. CONFIDENCE METER\n"
    "Present the confidence score out of 100 with DRAMATIC commentary. "
    "Is this a championship-level connection or are we getting relegated?\n\n"
    "## 4. TACTICAL ADVISORY\n"
    "Give specific, actionable next-message advice based on ALL the data. "
    "What play should the user call next? When should they send it? "
    "What words should they use or avoid? Be concrete.\n\n"
    "Remember: be entertaining but ACCURATE. Every claim must trace back to "
    "the data in the briefing packet. And if the user is clearly delusional, "
    "it is your DUTY to call a timeout and deliver a reality check."
)


def loading_msg(text):
    """Print a dramatic loading line with a short pause."""
    print(f"  [*] {text}", flush=True)
    time.sleep(0.3)


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def gather_intel():
    """Call every data function and return a dict of results."""
    print("\n  ── gathering intelligence... ──\n")

    loading_msg("intercepting vibe frequencies...")
    vibe_trend = get_vibe_trend(days=14)

    loading_msg("decoding today's play-by-play...")
    daily_summary = get_daily_summary()

    loading_msg("calculating confidence rating...")
    confidence = get_confidence_score()

    loading_msg("running correlation matrix...")
    correlations = get_correlation_highlights()

    loading_msg("pulling recent transcripts...")
    recent_msgs = get_recent_messages(n=50)

    loading_msg("analyzing word impact on the field...")
    word_impact = word_impact_analysis()

    loading_msg("reviewing ghost tape...")
    ghosts = ghost_triggers()

    loading_msg("clocking her response times...")
    resp_times = response_time_patterns()

    loading_msg("identifying enthusiasm triggers...")
    enthusiasm = her_enthusiasm_triggers()

    loading_msg("mapping the sweet-spot schedule...")
    sweet_spot = time_of_day_sweet_spot()

    print("\n  ── intelligence gathered. building briefing packet... ──\n")

    return {
        "vibe_trend": vibe_trend,
        "daily_summary": daily_summary,
        "confidence": confidence,
        "correlations": correlations,
        "recent_msgs": recent_msgs,
        "word_impact": word_impact,
        "ghosts": ghosts,
        "resp_times": resp_times,
        "enthusiasm": enthusiasm,
        "sweet_spot": sweet_spot,
    }


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def build_prompt(data):
    """Format all collected data into a structured briefing packet for the LLM."""

    sections = []

    # --- Vibe Trend ---
    vt = data["vibe_trend"]
    sections.append(
        "=== CURRENT VIBE TREND DATA ===\n"
        f"Recent average (7d): {vt.get('recent_avg')}\n"
        f"Previous average (7d before that): {vt.get('previous_avg')}\n"
        f"Delta: {vt.get('delta')}\n"
        f"Direction: {vt.get('direction')}\n"
        f"Current streak: {vt.get('current_streak')}\n"
        f"Best recent day: {vt.get('best_recent_day')}\n"
        f"Worst recent day: {vt.get('worst_recent_day')}"
    )

    # --- Today's Summary ---
    ds = data["daily_summary"]
    sections.append(
        "=== TODAY'S SUMMARY ===\n"
        f"Date: {ds.get('date')}\n"
        f"Vibe score: {ds.get('vibe_score')}\n"
        f"Total messages: {ds.get('msg_count')}\n"
        f"Her messages: {ds.get('her_msg_count')}\n"
        f"My messages: {ds.get('my_msg_count')}\n"
        f"She initiated: {ds.get('she_initiated')}\n"
        f"Avg her response time (min): {ds.get('avg_her_response_min')}\n"
        f"Commentary: {ds.get('commentary')}"
    )

    # --- Confidence Breakdown ---
    conf = data["confidence"]
    breakdown_lines = "\n".join(
        f"  - {k}: {v}" for k, v in (conf.get("breakdown") or {}).items()
    )
    sections.append(
        "=== CONFIDENCE BREAKDOWN ===\n"
        f"Overall score: {conf.get('score')}/100\n"
        f"Verdict: {conf.get('verdict')}\n"
        f"Component scores:\n{breakdown_lines}"
    )

    # --- Statistical Correlations ---
    corrs = data["correlations"]
    corr_lines = []
    for c in (corrs or []):
        sig = "SIGNIFICANT" if c.get("significant") else "not significant"
        corr_lines.append(
            f"  - {c.get('feature')}: r={c.get('r')}, p={c.get('p')} ({sig}) "
            f"- {c.get('interpretation')}"
        )
    sections.append(
        "=== STATISTICAL CORRELATIONS ===\n" + "\n".join(corr_lines)
    )

    # --- Word Impact Analysis (top 5) ---
    wi = data["word_impact"]
    wi_top = (wi or [])[:5]
    wi_lines = []
    for w in wi_top:
        wi_lines.append(
            f"  - \"{w.get('word')}\": used {w.get('days_used')} days, "
            f"avg vibe when used={w.get('avg_vibe_when_used')}, "
            f"avg vibe when NOT used={w.get('avg_vibe_when_not')}, "
            f"delta={w.get('delta')}, verdict={w.get('verdict')}"
        )
    sections.append(
        "=== WORD IMPACT ANALYSIS (top 5) ===\n" + "\n".join(wi_lines)
    )

    # --- Ghost Trigger Analysis ---
    gh = data["ghosts"]
    gh_triggers = gh.get("ghost_instances") or gh.get("triggers") or []
    gh_lines = []
    for t in gh_triggers:
        gh_lines.append(
            f"  - Date: {t.get('date')}, my last msg: \"{t.get('my_last_message')}\", "
            f"my msg count that day: {t.get('my_msg_count_that_day')}"
        )
    sections.append(
        "=== GHOST TRIGGER ANALYSIS ===\n"
        f"Summary: {gh.get('summary')}\n"
        f"Trigger incidents:\n" + "\n".join(gh_lines)
    )

    # --- Response Time Patterns ---
    rt = data["resp_times"]
    rt_lines = []
    for category in rt.keys():
        val = rt.get(category)
        if val is not None:
            rt_lines.append(f"  - {category}: {val}")
    sections.append(
        "=== RESPONSE TIME PATTERNS (her avg response time) ===\n"
        + "\n".join(rt_lines)
    )

    # --- Enthusiasm Triggers ---
    enth = data["enthusiasm"]
    enth_lines = []
    for m in (enth or [])[:10]:
        if isinstance(m, dict):
            enth_lines.append(f"  - I said: \"{m.get('my_message')}\" -> She replied: \"{m.get('her_enthusiastic_reply')}\"")
        else:
            enth_lines.append(f"  - \"{m}\"")
    sections.append(
        "=== HER ENTHUSIASM TRIGGERS (my messages that preceded her excited replies) ===\n"
        + "\n".join(enth_lines)
    )

    # --- Best Time to Text ---
    ss = data["sweet_spot"]
    ss_lines = []
    for slot in (ss or []):
        ss_lines.append(
            f"  - {slot.get('time_slot')}: avg vibe={slot.get('avg_vibe')}, "
            f"msg count={slot.get('msg_count')}"
        )
    sections.append(
        "=== BEST TIME TO TEXT ===\n" + "\n".join(ss_lines)
    )

    # --- Recent Conversation (last 20) ---
    recent = (data["recent_msgs"] or [])[-20:]
    convo_lines = []
    for m in recent:
        convo_lines.append(
            f"  [{m.get('timestamp')}] {m.get('sender')}: {m.get('text')}"
        )
    sections.append(
        "=== RECENT CONVERSATION (last 20 messages) ===\n"
        + "\n".join(convo_lines)
    )

    prompt = (
        "Here is the full briefing packet. Analyze ALL of this data and deliver "
        "your scouting report.\n\n"
        + "\n\n".join(sections)
    )

    return prompt


# ---------------------------------------------------------------------------
# Ollama streaming call
# ---------------------------------------------------------------------------

def call_ollama(prompt):
    """Send the prompt to Ollama and stream the response to stdout."""

    payload = json.dumps({
        "model": "qwen2.5:32b",
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": True,
        "options": {"temperature": 0.8},
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                token = chunk.get("response", "")
                if token:
                    sys.stdout.write(token)
                    sys.stdout.flush()
                if chunk.get("done"):
                    break
    except urllib.error.URLError as exc:
        print(
            "\n  [ERROR] Could not connect to Ollama at localhost:11434.\n"
            f"  Reason: {exc.reason}\n\n"
            "  Make sure Ollama is running:\n"
            "    1. Install from https://ollama.com\n"
            "    2. Run:  ollama serve\n"
            "    3. Pull the model:  ollama pull qwen2.5:32b\n"
            "    4. Re-run this script.\n"
        )
        sys.exit(1)
    except ConnectionError as exc:
        print(
            "\n  [ERROR] Connection to Ollama lost.\n"
            f"  Details: {exc}\n"
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(HEADER)

    # Collect all the data
    data = gather_intel()

    # Build the mega-prompt
    prompt = build_prompt(data)

    print("  ── patching into deluluisnotthesolulu... ──\n")
    time.sleep(0.5)

    # Stream the LLM analysis
    call_ollama(prompt)

    # Sign off
    print("\n")
    print(DISCLAIMER)


if __name__ == "__main__":
    main()
