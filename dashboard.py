"""
deluluisnotthesolulu Dashboard
Terminal dashboard: vibe graph, today's score, DEFCON level, LLM briefing.
"""

import sys
import io
import json
import time
import urllib.request
import urllib.error
import sqlite3

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from data_engine import (
    get_vibe_trend,
    get_daily_summary,
    get_confidence_score,
    get_correlation_highlights,
    get_recent_messages,
)
import os
from pattern_detector import (
    word_impact_analysis,
    ghost_triggers,
    response_time_patterns,
    her_enthusiasm_triggers,
    time_of_day_sweet_spot,
)

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mixed_signals.db")
W = 72


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


def mini_graph(dates, scores, width=60, height=12):
    if not dates:
        return []
    n = len(dates)
    mn = min(scores)
    mx = max(scores)
    if mx == mn:
        mx = mn + 1
    chart = [[" " for _ in range(width)] for _ in range(height)]
    for i, (d, s) in enumerate(zip(dates, scores)):
        x = int((i / max(n - 1, 1)) * (width - 1))
        y = int(((s - mn) / (mx - mn)) * (height - 1))
        y = height - 1 - y
        if s > 0.4:
            ch = "#"
        elif s > 0.0:
            ch = "+"
        elif s > -0.3:
            ch = "."
        else:
            ch = "v"
        chart[y][x] = ch
    if mn < 0 < mx:
        zy = int(((0 - mn) / (mx - mn)) * (height - 1))
        zy = height - 1 - zy
        if 0 <= zy < height:
            for x in range(width):
                if chart[zy][x] == " ":
                    chart[zy][x] = "-"
    lines = []
    for ri, row in enumerate(chart):
        sv = mx - (ri / (height - 1)) * (mx - mn)
        label = "{:+.1f}".format(sv)
        lines.append("  {:>5s} |{}|".format(label, "".join(row)))
    lines.append("        +" + "-" * width + "+")
    first = dates[0][5:]
    mid = dates[len(dates) // 2][5:]
    last = dates[-1][5:]
    pad = width - len(first) - len(mid) - len(last)
    lp = pad // 2
    rp = pad - lp
    lines.append("        " + first + " " * lp + mid + " " * rp + last)
    return lines


def defcon_level(confidence):
    if confidence >= 75:
        return 1, "DEFCON 1", "ALL CLEAR. shes basically yours. dont fumble."
    elif confidence >= 60:
        return 2, "DEFCON 2", "looking solid. stay the course king."
    elif confidence >= 45:
        return 3, "DEFCON 3", "mid alert. could go either way. tread carefully."
    elif confidence >= 30:
        return 4, "DEFCON 4", "danger zone. vibes are slipping. take action."
    else:
        return 5, "DEFCON 5", "COOKED. evacuate the situationship immediately."


def defcon_art(level):
    arts = {
        1: [
            "    [ * * * * * * * * * * ]    THREAT LEVEL: MINIMAL",
            "    ALL SYSTEMS NOMINAL. GREEN ACROSS THE BOARD.",
        ],
        2: [
            "    [ * * * * * * * * . . ]    THREAT LEVEL: LOW",
            "    STEADY AS SHE GOES. MAINTAIN CURRENT HEADING.",
        ],
        3: [
            "    [ * * * * * . . . . . ]    THREAT LEVEL: MODERATE",
            "    MIXED SIGNALS DETECTED. PROCEED WITH CAUTION.",
        ],
        4: [
            "    [ * * * . . . . . . . ]    THREAT LEVEL: HIGH",
            "    WARNING: VIBE DETERIORATION IN PROGRESS.",
        ],
        5: [
            "    [ * . . . . . . . . . ]    THREAT LEVEL: CRITICAL",
            "    MAYDAY MAYDAY. ALL HOPE ABANDON YE WHO TEXT HERE.",
        ],
    }
    return arts.get(level, arts[3])


def score_meter(score, width=40):
    pos = int(((score + 1) / 2) * (width - 1))
    pos = max(0, min(width - 1, pos))
    bar = []
    for i in range(width):
        val = -1 + (i / (width - 1)) * 2
        if val < -0.3:
            bar.append("v")
        elif val < 0.1:
            bar.append(".")
        elif val < 0.4:
            bar.append("+")
        else:
            bar.append("#")
    marker = [" "] * width
    marker[pos] = "^"
    return "".join(bar), "".join(marker)


def call_ollama_brief(prompt_text):
    system = (
        "You are deluluisnotthesolulu, a dramatic sports commentator who analyzes "
        "texting game tape. Give a BRIEF 4-5 sentence daily briefing covering: "
        "1) current vibe trend, 2) one key pattern to watch, 3) tactical advice for "
        "today. Use sports metaphors. Be funny and dramatic but concise. "
        "Do NOT use headers or numbered lists - just flowing commentary."
    )
    payload = json.dumps({
        "model": "qwen2.5:32b",
        "prompt": prompt_text,
        "system": system,
        "stream": True,
        "options": {"temperature": 0.8, "num_predict": 300},
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=120)
    except (urllib.error.URLError, ConnectionError, OSError):
        return "[LLM OFFLINE] Ollama not running. Start with: ollama serve"
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
    print(box_top("deluluisnotthesolulu"))
    print(box_center("tactical relationship intelligence system"))
    print(box_center("v1.0 | classified | for your eyes only"))
    print(box_bot())
    print()

    sys.stdout.write("  loading intelligence")
    sys.stdout.flush()
    trend = get_vibe_trend()
    sys.stdout.write(".")
    sys.stdout.flush()
    summary = get_daily_summary()
    sys.stdout.write(".")
    sys.stdout.flush()
    confidence = get_confidence_score()
    sys.stdout.write(".")
    sys.stdout.flush()
    correlations = get_correlation_highlights()
    sys.stdout.write(".")
    sys.stdout.flush()
    recent = get_recent_messages(20)
    sys.stdout.write(".")
    sys.stdout.flush()
    words = word_impact_analysis()
    sys.stdout.write(".")
    sys.stdout.flush()
    ghosts = ghost_triggers()
    sys.stdout.write(".")
    sys.stdout.flush()
    resp_times = response_time_patterns()
    sys.stdout.write(".")
    sys.stdout.flush()
    enthus = her_enthusiasm_triggers()
    sys.stdout.write(".")
    sys.stdout.flush()
    sweet = time_of_day_sweet_spot()
    print(" done.")
    print()

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT date, vibe_score FROM daily_vibes ORDER BY date")
    all_daily = c.fetchall()
    conn.close()
    all_dates = [r[0] for r in all_daily]
    all_scores = [r[1] for r in all_daily]

    # === VIBE TRAJECTORY ===
    print(box_top("VIBE TRAJECTORY"))
    graph_lines = mini_graph(all_dates, all_scores)
    inner = W - 4
    for gl in graph_lines:
        if len(gl) <= inner:
            print(box_line(gl))
        else:
            print(box_line(gl[:inner]))
    print(box_line())
    print(box_line("# fire(>0.4) + decent(>0) . mid(>-0.3) v cooked(<-0.3)"))
    print(box_bot())
    print()

    # === TODAY'S SCORE ===
    print(box_top("TODAYS SCORE"))
    today_date = summary.get("date", "???")
    today_score = summary.get("vibe_score", 0)
    today_msgs = summary.get("msg_count", 0)
    her_msgs = summary.get("her_msg_count", 0)
    my_msgs = summary.get("my_msg_count", 0)
    initiated = "HER" if summary.get("she_initiated") else "you"
    reply_time = summary.get("avg_her_response_min")
    reply_str = "{:.0f}min".format(reply_time) if reply_time else "n/a"
    commentary = summary.get("commentary", "")

    print(box_line("Date: {}  |  Vibe: {:+.3f}  |  {}".format(
        today_date, today_score, commentary)))
    print(box_line("Messages: {} (you: {}, her: {})  |  Started by: {}".format(
        today_msgs, my_msgs, her_msgs, initiated)))
    print(box_line("Her avg reply time: {}".format(reply_str)))
    print(box_line())

    bar, marker = score_meter(today_score)
    print(box_line("  cooked [{}] wedding".format(bar)))
    print(box_line("         {}".format(marker)))
    print(box_line())

    direction = trend.get("direction", "unknown")
    delta = trend.get("delta", 0)
    streak = trend.get("current_streak", 0)
    if delta > 0:
        arrow = ">>>"
    elif delta < 0:
        arrow = "<<<"
    else:
        arrow = "==="
    print(box_line("14-day trend: {} ({:+.3f}) {}  streak: {:+d} days".format(
        direction.upper(), delta, arrow, streak)))

    best = trend.get("best_recent_day", {})
    worst = trend.get("worst_recent_day", {})
    if best:
        print(box_line("  best recent:  {} ({:+.3f})".format(
            best.get("date", "?"), best.get("score", 0))))
    if worst:
        print(box_line("  worst recent: {} ({:+.3f})".format(
            worst.get("date", "?"), worst.get("score", 0))))
    print(box_bot())
    print()

    # === DEFCON ===
    conf_score = confidence.get("score", 50)
    level, label, desc = defcon_level(conf_score)
    art = defcon_art(level)

    print(box_top(label))
    print(box_center("Confidence: {:.1f} / 100".format(conf_score)))
    print(box_line())
    for a in art:
        print(box_line(a))
    print(box_line())
    print(box_center(desc))
    print(box_line())

    bd = confidence.get("breakdown", {})
    for k, v in bd.items():
        lbl = k.replace("_", " ").title()
        bar_w = 20
        filled = int((v / 100) * bar_w) if v else 0
        bstr = "#" * filled + "." * (bar_w - filled)
        print(box_line("  {:<25s} [{}] {:.0f}".format(lbl, bstr, v)))
    print(box_bot())
    print()

    # === AGENT BRIEFING ===
    print(box_top("AGENT BRIEFING"))
    print(box_center("<< streaming from qwen2.5:32b >>"))
    print(box_bot())
    print()

    sig_corrs = [x for x in correlations if x.get("significant")]
    top_words = words[:3] if words else []
    ghost_list = (ghosts.get("ghost_instances", [])[:3]
                  if isinstance(ghosts, dict) else [])

    parts = [
        "Vibe trend: {}, delta={:+.3f}, streak={:+d} days".format(
            direction, delta, streak),
        "Today: score={:+.3f}, msgs={}, initiated={}, reply={}".format(
            today_score, today_msgs, initiated, reply_str),
        "Confidence: {:.1f}/100".format(conf_score),
    ]
    for sc in sig_corrs:
        parts.append("Significant: {} r={:.3f} p={:.4f} - {}".format(
            sc["feature"], sc["r"], sc["p"], sc["interpretation"]))
    for tw in top_words:
        parts.append("Word '{}': vibe delta={:+.3f}".format(
            tw["word"], tw["delta"]))
    if ghost_list:
        msgs = [g.get("my_last_message", "?")[:40] for g in ghost_list[:3]]
        parts.append("Ghost triggers: {}".format(msgs))
    if sweet:
        valid = [s for s in sweet if s.get("avg_vibe") is not None]
        if valid:
            best_slot = max(valid, key=lambda s: s["avg_vibe"])
            parts.append("Best time to text: {} (avg vibe {:.3f})".format(
                best_slot["time_slot"], best_slot["avg_vibe"]))
    if recent:
        for m in recent[-5:]:
            parts.append("[{}]: {}".format(m["sender"], m["text"][:60]))

    prompt_text = ("Here is today's data briefing packet:\n"
                   + "\n".join(parts)
                   + "\n\nGive me today's briefing, coach.")

    briefing = call_ollama_brief(prompt_text)
    print()

    # === FOOTER ===
    print(box_top())
    print(box_center("powered by love for juice wrld and a $600 mac mini"))
    print(box_bot())
    print()


if __name__ == "__main__":
    main()
