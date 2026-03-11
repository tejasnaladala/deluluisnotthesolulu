import sqlite3
from datetime import datetime
from collections import defaultdict
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mixed_signals.db")

W = {
    "response_time": 0.25,
    "length_ratio": 0.20,
    "initiation": 0.15,
    "enthusiasm": 0.15,
    "engagement": 0.10,
    "ghost_penalty": 0.15,
}


def parse_ts(ts_str):
    return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")


def score_response_time(times):
    if not times:
        return 0.0
    avg = sum(times) / len(times)
    if avg < 5:
        return 1.0
    elif avg < 15:
        return 0.5
    elif avg < 30:
        return 0.0
    elif avg < 60:
        return -0.5
    else:
        return -1.0


def score_length_ratio(my, her):
    if not my or not her:
        return 0.0
    ma = sum(len(m) for m in my) / len(my)
    ha = sum(len(m) for m in her) / len(her)
    if ma == 0:
        return 0.0
    r = ha / ma
    if r > 1.2:
        return 1.0
    elif r > 0.8:
        return 0.5
    elif r > 0.5:
        return 0.0
    elif r > 0.3:
        return -0.5
    else:
        return -1.0


def score_initiation(msgs):
    if not msgs:
        return 0.0
    return 1.0 if msgs[0][1] == "her" else -0.3


def score_enthusiasm(her):
    if not her:
        return 0.0
    ec = 0
    for msg in her:
        hit = "!" in msg or ":)" in msg or "<3" in msg or ";)" in msg
        if not hit:
            for i in range(len(msg) - 2):
                if msg[i] == msg[i + 1] == msg[i + 2] and msg[i].isalpha():
                    hit = True
                    break
        if hit:
            ec += 1
    r = ec / len(her)
    if r > 0.5:
        return 1.0
    elif r > 0.3:
        return 0.5
    elif r > 0.1:
        return 0.0
    else:
        return -0.5


def score_engagement(her):
    if not her:
        return 0.0
    qc = sum(1 for m in her if "?" in m)
    yc = sum(1 for m in her if any(w in m.lower() for w in ["you", "your", "wbu", "hbu"]))
    s = (qc + yc) / len(her)
    if s > 0.5:
        return 1.0
    elif s > 0.3:
        return 0.5
    elif s > 0.1:
        return 0.0
    else:
        return -0.5


def score_ghost(my, her):
    if my and not her:
        return -1.0 * min(len(my), 3) / 3.0
    return 0.3


def compute_daily(msgs):
    my = [m[2] for m in msgs if m[1] == "me"]
    her = [m[2] for m in msgs if m[1] == "her"]
    times = []
    last = None
    for ts, sender, text in msgs:
        t = parse_ts(ts)
        if sender == "me":
            last = t
        elif sender == "her" and last:
            d = (t - last).total_seconds() / 60.0
            if d < 180:
                times.append(d)
            last = None
    sc = {
        "response_time": score_response_time(times),
        "length_ratio": score_length_ratio(my, her),
        "initiation": score_initiation(msgs),
        "enthusiasm": score_enthusiasm(her),
        "engagement": score_engagement(her),
        "ghost_penalty": score_ghost(my, her),
    }
    raw = sum(sc[k] * W[k] for k in W)
    return max(-1.0, min(1.0, raw)), sc, times, my, her


def vibe_label(s):
    if s > 0.7:
        return "shes planning the wedding"
    elif s > 0.4:
        return "strong signals king"
    elif s > 0.1:
        return "cautiously optimistic"
    elif s > -0.1:
        return "mid. literally mid."
    elif s > -0.4:
        return "down bad and she knows it"
    elif s > -0.7:
        return "youre a side character"
    else:
        return "absolutely cooked"


def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, timestamp, sender, message_text FROM messages ORDER BY timestamp")
    rows = c.fetchall()
    days = defaultdict(list)
    for mid, ts, sender, text in rows:
        days[ts[:10]].append((ts, sender, text, mid))

    results = []
    mscores = {}
    for day, dmsgs in sorted(days.items()):
        ordered = [(ts, s, t) for ts, s, t, _ in dmsgs]
        score, bd, rt, my, her = compute_daily(ordered)
        results.append((day, score, len(dmsgs), len(her), len(my), rt, my, her))
        for ts, s, t, mid in dmsgs:
            mscores[mid] = score

    for mid, sc in mscores.items():
        c.execute("UPDATE messages SET vibe_score = ? WHERE id = ?", (round(sc, 3), mid))

    c.execute("DELETE FROM daily_vibes")
    for day, score, total, hn, mn, rt, my, her in results:
        dmsgs = days[day]
        ordered = [(ts, s, t) for ts, s, t, _ in dmsgs]
        si = 1 if ordered[0][1] == "her" else 0
        ar = round(sum(rt) / len(rt), 1) if rt else None
        hal = round(sum(len(m) for m in her) / len(her), 1) if her else 0
        mal = round(sum(len(m) for m in my) / len(my), 1) if my else 0
        c.execute(
            "INSERT INTO daily_vibes VALUES (?,?,?,?,?,?,?,?,?,?)",
            (day, round(score, 3), total, hn, mn, si, ar, hal, mal, vibe_label(score)),
        )
    conn.commit()

    # Results
    print("=" * 55)
    print("   VIBE SCORING COMPLETE")
    print("=" * 55)
    asc = [s for _, s, *_ in results]
    avg = sum(asc) / len(asc)
    print(f"  Days scored:       {len(results)}")
    print(f"  Average vibe:      {avg:.3f} ({vibe_label(avg)})")
    print(f"  Best day score:    {max(asc):.3f}")
    print(f"  Worst day score:   {min(asc):.3f}")

    tiers = {
        "cooked (< -0.5)": 0,
        "rough (-0.5 to -0.1)": 0,
        "mid (-0.1 to 0.1)": 0,
        "decent (0.1 to 0.4)": 0,
        "fire (0.4 to 0.7)": 0,
        "wedding (> 0.7)": 0,
    }
    for s in asc:
        if s < -0.5:
            tiers["cooked (< -0.5)"] += 1
        elif s < -0.1:
            tiers["rough (-0.5 to -0.1)"] += 1
        elif s < 0.1:
            tiers["mid (-0.1 to 0.1)"] += 1
        elif s < 0.4:
            tiers["decent (0.1 to 0.4)"] += 1
        elif s < 0.7:
            tiers["fire (0.4 to 0.7)"] += 1
        else:
            tiers["wedding (> 0.7)"] += 1
    print()
    print("  Vibe Distribution:")
    for tier, cnt in tiers.items():
        print(f"    {tier:25s} {cnt:3d} {'#' * cnt}")

    sd = sorted(results, key=lambda x: x[1], reverse=True)
    br = [
        "bro she was basically writing your wedding vows this day",
        "if you didnt shoot your shot this day youre ngmi",
        "she gave you the green light, checkered flag, AND the key to the city",
    ]
    print()
    print("=" * 55)
    print("   TOP 3 BEST DAYS (she might actually like you)")
    print("=" * 55)
    for i, (day, sc, tot, hn, mn, rt, my, her) in enumerate(sd[:3]):
        ar = f"{sum(rt) / len(rt):.0f}min" if rt else "n/a"
        ordered = [(ts, s, t) for ts, s, t, _ in days[day]]
        wf = "HER" if ordered[0][1] == "her" else "you"
        print(f"\n  #{i + 1}  {day}  |  vibe: {sc:.3f}")
        print(f"      msgs: {tot} (you: {mn}, her: {hn})  |  her avg reply: {ar}")
        print(f"      initiated by: {wf}")
        hl = [m for m in her if len(m) > 15][:3]
        if hl:
            print(f"      her highlights: {hl}")
        print(f"      >> {br[i]}")

    wgr = [
        "you texted into the void and the void left you on read",
        "bro was talking to himself like a minecraft villager",
        "she saw your message, said nah, and continued her life",
    ]
    wdr = [
        "she responded like youre a coworker she tolerates",
        "her texts have the emotional warmth of a TOS agreement",
        "you got more enthusiasm from your last captcha",
    ]
    print()
    print("=" * 55)
    print("   TOP 3 WORST DAYS (certified cooked moments)")
    print("=" * 55)
    for i, (day, sc, tot, hn, mn, rt, my, her) in enumerate(sd[-3:][::-1]):
        ar = f"{sum(rt) / len(rt):.0f}min" if rt else "ghosted"
        print(f"\n  #{i + 1}  {day}  |  vibe: {sc:.3f}")
        print(f"      msgs: {tot} (you: {mn}, her: {hn})  |  her avg reply: {ar}")
        if her:
            print(f"      her entire vocabulary: {her}")
        else:
            print(f"      her messages: *crickets* (0 replies)")
        print(f"      your messages: {my}")
        roasts = wgr if not her else wdr
        print(f"      >> {roasts[i]}")
    conn.close()


if __name__ == "__main__":
    main()
