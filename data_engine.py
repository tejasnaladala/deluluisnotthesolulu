"""
data_engine.py -deluluisnotthesolulu data analysis module.

Reads from a SQLite database of text message history and daily vibe scores,
and exposes functions that return structured dicts/lists for downstream
consumption (dashboards, CLI reports, etc.).
"""

import sqlite3
import math
import datetime
from collections import defaultdict
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mixed_signals.db")


def _conn():
    """Return a new database connection with row-factory enabled."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


# ---------------------------------------------------------------------------
# 1. Vibe trend
# ---------------------------------------------------------------------------

def get_vibe_trend(days=14):
    """Compare the most recent *days* of daily_vibes to the previous *days*.

    Returns a dict with:
        recent_avg, previous_avg, delta, direction,
        current_streak, best_recent_day, worst_recent_day
    """
    con = _conn()
    cur = con.cursor()

    # Grab the most recent 2*days rows ordered by date descending
    cur.execute(
        "SELECT date, vibe_score FROM daily_vibes ORDER BY date DESC LIMIT ?",
        (days * 2,),
    )
    rows = cur.fetchall()
    con.close()

    recent_rows = rows[:days]        # most recent chunk
    previous_rows = rows[days:days * 2]  # chunk before that

    # Averages
    recent_avg = sum(r["vibe_score"] for r in recent_rows) / len(recent_rows) if recent_rows else 0.0
    previous_avg = sum(r["vibe_score"] for r in previous_rows) / len(previous_rows) if previous_rows else 0.0
    delta = recent_avg - previous_avg

    # Direction
    if delta > 0.05:
        direction = "heating up"
    elif delta < -0.05:
        direction = "cooling down"
    else:
        direction = "flatline"

    # Current streak -consecutive days (from most recent) with score above
    # or below zero.  Sign of streak indicates positive (+) or negative (-).
    streak = 0
    if recent_rows:
        first_sign = 1 if recent_rows[0]["vibe_score"] >= 0 else -1
        for r in recent_rows:
            if (r["vibe_score"] >= 0 and first_sign == 1) or (r["vibe_score"] < 0 and first_sign == -1):
                streak += 1
            else:
                break
        streak *= first_sign

    # Best / worst recent day
    best = max(recent_rows, key=lambda r: r["vibe_score"]) if recent_rows else None
    worst = min(recent_rows, key=lambda r: r["vibe_score"]) if recent_rows else None

    return {
        "recent_avg": round(recent_avg, 4),
        "previous_avg": round(previous_avg, 4),
        "delta": round(delta, 4),
        "direction": direction,
        "current_streak": streak,
        "best_recent_day": {
            "date": best["date"],
            "score": best["vibe_score"],
        } if best else None,
        "worst_recent_day": {
            "date": worst["date"],
            "score": worst["vibe_score"],
        } if worst else None,
    }


# ---------------------------------------------------------------------------
# 2. Daily summary
# ---------------------------------------------------------------------------

def get_daily_summary():
    """Return the most recent day's data from daily_vibes."""
    con = _conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM daily_vibes ORDER BY date DESC LIMIT 1")
    row = cur.fetchone()
    con.close()

    if row is None:
        return {}

    return {
        "date": row["date"],
        "vibe_score": row["vibe_score"],
        "msg_count": row["msg_count"],
        "her_msg_count": row["her_msg_count"],
        "my_msg_count": row["my_msg_count"],
        "she_initiated": bool(row["she_initiated"]),
        "avg_her_response_min": row["avg_her_response_min"],
        "commentary": row["commentary"],
    }


# ---------------------------------------------------------------------------
# 3. Confidence score
# ---------------------------------------------------------------------------

def _map_range(value, in_lo, in_hi, out_lo=0.0, out_hi=100.0):
    """Linearly map *value* from [in_lo, in_hi] to [out_lo, out_hi], clamped."""
    if in_hi == in_lo:
        return (out_lo + out_hi) / 2.0
    t = (value - in_lo) / (in_hi - in_lo)
    t = max(0.0, min(1.0, t))
    return out_lo + t * (out_hi - out_lo)


def get_confidence_score():
    """Compute a 0-100 'she likes you' confidence score.

    Weighted composite of five components (see breakdown).
    Returns dict with: score, breakdown, verdict.
    """
    con = _conn()
    cur = con.cursor()

    cur.execute("SELECT * FROM daily_vibes ORDER BY date ASC")
    all_days = cur.fetchall()
    con.close()

    if not all_days:
        return {"score": 0, "breakdown": {}, "verdict": "no data"}

    total = len(all_days)

    # --- Component 1: overall avg vibe (weight 25%) ---
    overall_avg = sum(d["vibe_score"] for d in all_days) / total
    comp_vibe = _map_range(overall_avg, -1.0, 1.0, 0.0, 100.0)

    # --- Component 2: good/bad day ratio (weight 20%) ---
    good_days = sum(1 for d in all_days if d["vibe_score"] > 0.1)
    bad_days = sum(1 for d in all_days if d["vibe_score"] < -0.1)
    if good_days + bad_days == 0:
        comp_ratio = 50.0
    else:
        comp_ratio = (good_days / (good_days + bad_days)) * 100.0

    # --- Component 3: she-initiated % (weight 20%) ---
    initiated = sum(1 for d in all_days if d["she_initiated"])
    comp_initiated = (initiated / total) * 100.0

    # --- Component 4: response time (weight 15%) ---
    response_times = [d["avg_her_response_min"] for d in all_days if d["avg_her_response_min"] is not None]
    if response_times:
        avg_resp = sum(response_times) / len(response_times)
        # Under 5 min → 100, over 120 min → 0
        comp_response = _map_range(avg_resp, 120.0, 5.0, 0.0, 100.0)
    else:
        comp_response = 50.0

    # --- Component 5: recent trajectory (weight 20%) ---
    recent_14 = all_days[-14:] if len(all_days) >= 14 else all_days
    recent_avg = sum(d["vibe_score"] for d in recent_14) / len(recent_14)
    trajectory_delta = recent_avg - overall_avg
    # Map trajectory delta: -0.5 → 0, +0.5 → 100, centre at 50
    comp_trajectory = _map_range(trajectory_delta, -0.5, 0.5, 0.0, 100.0)

    # --- Weighted total ---
    score = (
        comp_vibe * 0.25
        + comp_ratio * 0.20
        + comp_initiated * 0.20
        + comp_response * 0.15
        + comp_trajectory * 0.20
    )
    score = max(0.0, min(100.0, score))

    # Verdict
    if score >= 80:
        verdict = "she's into you, king"
    elif score >= 60:
        verdict = "looking good but don't get cocky"
    elif score >= 40:
        verdict = "mixed signals -proceed with caution"
    elif score >= 20:
        verdict = "not great, chief"
    else:
        verdict = "bro, move on"

    return {
        "score": round(score, 2),
        "breakdown": {
            "overall_avg_vibe": round(comp_vibe, 2),
            "good_bad_ratio": round(comp_ratio, 2),
            "she_initiated_pct": round(comp_initiated, 2),
            "response_time": round(comp_response, 2),
            "recent_trajectory": round(comp_trajectory, 2),
        },
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# 4. Correlation highlights (pure-Python Pearson r + t-test p-value)
# ---------------------------------------------------------------------------

def _pearson_r(xs, ys):
    """Return (r, p) for two equal-length sequences.

    Uses the Pearson correlation coefficient and approximates the two-tailed
    p-value via the t-distribution using a rational approximation.
    """
    n = len(xs)
    if n < 3:
        return 0.0, 1.0

    mx = sum(xs) / n
    my = sum(ys) / n

    sx = [x - mx for x in xs]
    sy = [y - my for y in ys]

    num = sum(a * b for a, b in zip(sx, sy))
    den_x = math.sqrt(sum(a * a for a in sx))
    den_y = math.sqrt(sum(b * b for b in sy))

    if den_x == 0 or den_y == 0:
        return 0.0, 1.0

    r = num / (den_x * den_y)
    r = max(-1.0, min(1.0, r))

    # t-statistic
    if abs(r) >= 1.0:
        return r, 0.0

    t_stat = r * math.sqrt((n - 2) / (1 - r * r))
    df = n - 2

    # Approximate two-tailed p-value using the regularised incomplete beta
    # function.  For large df this is close enough.
    p = _t_to_p(abs(t_stat), df)
    return r, p


def _t_to_p(t, df):
    """Two-tailed p-value from t-statistic and degrees of freedom."""
    if df > 100:
        return 2.0 * _normal_cdf(-abs(t))
    x = df / (df + t * t)
    return _reg_inc_beta(df / 2.0, 0.5, x)


def _normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _reg_inc_beta(a, b, x):
    """Regularized incomplete beta function via continued fraction."""
    if x < 0 or x > 1:
        return 0.0
    if x == 0 or x == 1:
        return x
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1.0 - x) * b - lbeta) / a
    f, c = 1.0, 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    f = d
    for i in range(1, 200):
        m = i
        num = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        d = 1.0 + num * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + num / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d
        f *= d * c
        num = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        if abs(d) < 1e-30: d = 1e-30
        c = 1.0 + num / c
        if abs(c) < 1e-30: c = 1e-30
        d = 1.0 / d
        delta = d * c
        f *= delta
        if abs(delta - 1.0) < 1e-8:
            break
    return front * f


def get_correlation_highlights():
    """Compute Pearson r and p-values for several features vs daily vibe score.

    Features derived from the messages + daily_vibes tables:
        day_of_week, avg_hour, gap_since_last, my_msg_length, double_texts

    Returns a list of dicts with: feature, r, p, significant, interpretation.
    """
    con = _conn()
    cur = con.cursor()

    # -- Pull daily_vibes --
    cur.execute("SELECT date, vibe_score FROM daily_vibes ORDER BY date ASC")
    vibes_rows = cur.fetchall()
    vibe_by_date = {r["date"]: r["vibe_score"] for r in vibes_rows}

    # -- Pull messages --
    cur.execute("SELECT timestamp, sender, message_text FROM messages ORDER BY timestamp ASC")
    msgs = cur.fetchall()
    con.close()

    # Group messages by date
    msgs_by_date = defaultdict(list)
    for m in msgs:
        ts = m["timestamp"]
        # Extract date part (first 10 chars  YYYY-MM-DD)
        d = ts[:10]
        msgs_by_date[d].append(m)

    # Build per-day feature vectors for dates that appear in both tables
    dates_sorted = sorted(vibe_by_date.keys())

    day_of_week_vals = []
    avg_hour_vals = []
    gap_since_last_vals = []
    my_msg_length_vals = []
    double_texts_vals = []
    vibe_vals_dow = []
    vibe_vals_hour = []
    vibe_vals_gap = []
    vibe_vals_len = []
    vibe_vals_dt = []

    prev_date = None
    for d in dates_sorted:
        vibe = vibe_by_date[d]
        day_msgs = msgs_by_date.get(d, [])

        # day_of_week: 0=Monday .. 6=Sunday
        try:
            dt = datetime.date.fromisoformat(d)
            dow = dt.weekday()
        except Exception:
            dow = 0
        day_of_week_vals.append(float(dow))
        vibe_vals_dow.append(vibe)

        # avg_hour -average hour of messages that day
        hours = []
        for m in day_msgs:
            try:
                t = datetime.datetime.fromisoformat(m["timestamp"])
                hours.append(t.hour + t.minute / 60.0)
            except Exception:
                pass
        if hours:
            avg_hour_vals.append(sum(hours) / len(hours))
            vibe_vals_hour.append(vibe)

        # gap_since_last -days since previous daily_vibes entry
        if prev_date is not None:
            try:
                gap = (datetime.date.fromisoformat(d) - datetime.date.fromisoformat(prev_date)).days
            except Exception:
                gap = 1
            gap_since_last_vals.append(float(gap))
            vibe_vals_gap.append(vibe)
        prev_date = d

        # my_msg_length -average length of my messages that day
        my_lens = [len(m["message_text"]) for m in day_msgs if m["sender"] == "me" and m["message_text"]]
        if my_lens:
            my_msg_length_vals.append(sum(my_lens) / len(my_lens))
            vibe_vals_len.append(vibe)

        # double_texts -consecutive messages from 'me' without a reply
        double = 0
        consecutive_me = 0
        for m in day_msgs:
            if m["sender"] == "me":
                consecutive_me += 1
                if consecutive_me >= 2:
                    double += 1
            else:
                consecutive_me = 0
        double_texts_vals.append(float(double))
        vibe_vals_dt.append(vibe)

    # Compute correlations
    features = [
        ("day_of_week", day_of_week_vals, vibe_vals_dow),
        ("avg_hour", avg_hour_vals, vibe_vals_hour),
        ("gap_since_last", gap_since_last_vals, vibe_vals_gap),
        ("my_msg_length", my_msg_length_vals, vibe_vals_len),
        ("double_texts", double_texts_vals, vibe_vals_dt),
    ]

    results = []
    for name, xs, ys in features:
        r, p = _pearson_r(xs, ys)

        significant = p < 0.05

        # Human-readable interpretation
        if not significant:
            interp = "no significant relationship detected"
        elif abs(r) < 0.2:
            interp = "negligible correlation"
        elif r > 0:
            strength = "moderate" if abs(r) < 0.5 else "strong"
            interp = f"{strength} positive -more {name.replace('_', ' ')} tends to mean better vibes"
        else:
            strength = "moderate" if abs(r) > -0.5 else "strong"
            strength = "moderate" if abs(r) < 0.5 else "strong"
            interp = f"{strength} negative -more {name.replace('_', ' ')} tends to mean worse vibes"

        results.append({
            "feature": name,
            "r": round(r, 4),
            "p": round(p, 6),
            "significant": significant,
            "interpretation": interp,
        })

    return results


# ---------------------------------------------------------------------------
# 5. Recent messages
# ---------------------------------------------------------------------------

def get_recent_messages(n=50):
    """Return the last *n* messages as a list of dicts."""
    con = _conn()
    cur = con.cursor()
    cur.execute(
        "SELECT timestamp, sender, message_text FROM messages ORDER BY timestamp DESC LIMIT ?",
        (n,),
    )
    rows = cur.fetchall()
    con.close()

    # Return in chronological order (oldest first)
    return [
        {
            "timestamp": r["timestamp"],
            "sender": r["sender"],
            "text": r["message_text"],
        }
        for r in reversed(rows)
    ]
