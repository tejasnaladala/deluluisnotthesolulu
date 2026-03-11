import sqlite3
import math
from datetime import datetime
from collections import defaultdict
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mixed_signals.db")


def pearson_r(x, y):
    n = len(x)
    if n < 3:
        return 0.0, 1.0
    mx = sum(x) / n
    my_ = sum(y) / n
    sx = math.sqrt(sum((xi - mx) ** 2 for xi in x) / (n - 1)) if n > 1 else 0
    sy = math.sqrt(sum((yi - my_) ** 2 for yi in y) / (n - 1)) if n > 1 else 0
    if sx == 0 or sy == 0:
        return 0.0, 1.0
    r = sum((xi - mx) * (yi - my_) for xi, yi in zip(x, y)) / ((n - 1) * sx * sy)
    r = max(-1.0, min(1.0, r))
    if abs(r) >= 1.0:
        return r, 0.0
    t_stat = r * math.sqrt((n - 2) / (1 - r * r))
    df = n - 2
    p = t_distribution_p(t_stat, df)
    return r, p


def t_distribution_p(t, df):
    x = df / (df + t * t)
    if df > 100:
        return 2.0 * normal_cdf(-abs(t))
    return regularized_incomplete_beta(df / 2.0, 0.5, x)


def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def regularized_incomplete_beta(a, b, x):
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


def sig_stars(p):
    if p < 0.001: return "***"
    elif p < 0.01: return "** "
    elif p < 0.05: return "*  "
    else: return "   "


def interpret(r, p, name):
    if p > 0.05:
        return "not statistically significant (cope harder)"
    direction = "positive" if r > 0 else "negative"
    strength = "weak" if abs(r) < 0.3 else "moderate" if abs(r) < 0.6 else "strong"
    intros = {
        "day_of_week": {"positive": "she likes you more on weekends", "negative": "weekday warrior energy"},
        "hour": {"positive": "late night you hits different", "negative": "morning texter. she likes early bird you"},
        "gap_since_last": {"positive": "absence makes the heart grow fonder", "negative": "out of sight out of mind"},
        "my_msg_length": {"positive": "she rewards your effort. essays WORKING", "negative": "youre trying too hard. less is more"},
        "double_text": {"positive": "double texting works?? chaotic but ok", "negative": "double texting = desperation. stop it."},
    }
    base = intros.get(name, {}).get(direction, direction + " correlation")
    return f"{strength} {direction} ({base})"


def compute_gap_hours(messages):
    day_last_my_msg = {}
    days_ordered = []
    current_day = None
    for ts_str, sender, text in messages:
        day = ts_str[:10]
        if day != current_day:
            days_ordered.append(day)
            current_day = day
        if sender == "me":
            day_last_my_msg[day] = ts_str
    gaps = {}
    prev_day = None
    for day in days_ordered:
        if prev_day and prev_day in day_last_my_msg:
            last_ts = datetime.strptime(day_last_my_msg[prev_day], "%Y-%m-%d %H:%M:%S")
            first_ts = None
            for ts_str, sender, text in messages:
                if ts_str[:10] == day:
                    first_ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    break
            if first_ts:
                gaps[day] = (first_ts - last_ts).total_seconds() / 3600.0
        prev_day = day
    return gaps


def count_double_texts(messages):
    day_doubles = defaultdict(int)
    consecutive_me = 0
    current_day = None
    for ts_str, sender, text in messages:
        day = ts_str[:10]
        if day != current_day:
            if consecutive_me >= 2 and current_day:
                day_doubles[current_day] += consecutive_me - 1
            consecutive_me = 0
            current_day = day
        if sender == "me":
            consecutive_me += 1
        else:
            if consecutive_me >= 2:
                day_doubles[day] += consecutive_me - 1
            consecutive_me = 0
    if consecutive_me >= 2 and current_day:
        day_doubles[current_day] += consecutive_me - 1
    return day_doubles


def ascii_chart(dates, scores, width=70, height=18):
    if not dates: return ""
    n = len(dates)
    min_s = min(scores)
    max_s = max(scores)
    if max_s == min_s: max_s = min_s + 1
    lines = [""]
    chart = [[" " for _ in range(width)] for _ in range(height)]
    for i, (date, score) in enumerate(zip(dates, scores)):
        x = int((i / max(n - 1, 1)) * (width - 1))
        y = int(((score - min_s) / (max_s - min_s)) * (height - 1))
        y = height - 1 - y
        if score > 0.4: char = "#"
        elif score > 0.0: char = "+"
        elif score > -0.3: char = "."
        else: char = "v"
        chart[y][x] = char
    zero_y = int(((0 - min_s) / (max_s - min_s)) * (height - 1))
    zero_y = height - 1 - zero_y
    if 0 <= zero_y < height:
        for x in range(width):
            if chart[zero_y][x] == " ": chart[zero_y][x] = "-"
    for row_idx, row in enumerate(chart):
        score_at_row = max_s - (row_idx / (height - 1)) * (max_s - min_s)
        label = f"{score_at_row:+.1f}"
        row_str = "".join(row)
        lines.append(f"  {label:>5s} |{row_str}|")
    lines.append(f"        +{chr(45) * width}+")
    first_date = dates[0][5:]
    mid_date = dates[len(dates) // 2][5:]
    last_date = dates[-1][5:]
    padding = width - len(first_date) - len(mid_date) - len(last_date)
    left_pad = padding // 2
    right_pad = padding - left_pad
    lines.append(f"        {first_date}{chr(32) * left_pad}{mid_date}{chr(32) * right_pad}{last_date}")
    lines.append("")
    lines.append("  Legend: # fire (>0.4)  + decent (>0)  . mid (>-0.3)  v cooked (<-0.3)")
    lines.append("         --- zero line (neutral vibes)")
    return chr(10).join(lines)


def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT date, vibe_score FROM daily_vibes ORDER BY date")
    daily = c.fetchall()
    dates = [r[0] for r in daily]
    scores = [r[1] for r in daily]
    c.execute("SELECT timestamp, sender, message_text FROM messages ORDER BY timestamp")
    all_msgs = c.fetchall()
    day_msgs = defaultdict(list)
    for ts, sender, text in all_msgs:
        day_msgs[ts[:10]].append((ts, sender, text))
    gaps = compute_gap_hours(all_msgs)
    doubles = count_double_texts(all_msgs)
    day_features = {}
    for day in dates:
        dt = datetime.strptime(day, "%Y-%m-%d")
        msgs = day_msgs[day]
        my_m = [m for m in msgs if m[1] == "me"]
        avg_hour = sum(datetime.strptime(m[0], "%Y-%m-%d %H:%M:%S").hour for m in msgs) / len(msgs) if msgs else 12
        my_avg_len = sum(len(m[2]) for m in my_m) / len(my_m) if my_m else 0
        day_features[day] = {
            "day_of_week": dt.weekday(),
            "hour": avg_hour,
            "gap_since_last": gaps.get(day, 24.0),
            "my_msg_length": my_avg_len,
            "double_text": doubles.get(day, 0),
        }
    feature_names = ["day_of_week", "hour", "gap_since_last", "my_msg_length", "double_text"]
    feature_labels = {
        "day_of_week": "Day of Week (0=Mon 6=Sun)",
        "hour": "Avg Hour of Day",
        "gap_since_last": "Hours Since Last Msg",
        "my_msg_length": "My Avg Message Length",
        "double_text": "Double/Triple Texts",
    }
    print("=" * 65)
    print("   CORRELATION ANALYSIS: Is She Into You?")
    print("   (statistically delusional edition)")
    print("=" * 65)
    print()
    hdr = f"  {'Feature':<28s} {'r':>7s} {'p-value':>10s} {'sig':>4s}"
    print(hdr)
    print(f"  {'-' * 28} {'-' * 7} {'-' * 10} {'-' * 4}")
    corr_results = []
    for feat in feature_names:
        x_vals, y_vals = [], []
        for day, score in zip(dates, scores):
            if day in day_features:
                x_vals.append(day_features[day][feat])
                y_vals.append(score)
        r, p = pearson_r(x_vals, y_vals)
        stars = sig_stars(p)
        corr_results.append((feat, r, p, stars))
        print(f"  {feature_labels[feat]:<28s} {r:+.4f} {p:>10.4f} {stars}")
    print()
    print("  Significance: *** p<0.001  ** p<0.01  * p<0.05")
    print()
    print("=" * 65)
    print("   WHAT THIS MEANS (the hard truth)")
    print("=" * 65)
    for feat, r, p, stars in corr_results:
        label = feature_labels[feat]
        interp = interpret(r, p, feat)
        print()
        print(f"  {label}")
        print(f"    r = {r:+.4f}, p = {p:.4f}")
        print(f"    verdict: {interp}")
    print()
    print("=" * 65)
    print("   VIBE BY DAY OF WEEK")
    print("=" * 65)
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow_scores = defaultdict(list)
    for day, score in zip(dates, scores):
        if day in day_features:
            dow_scores[day_features[day]["day_of_week"]].append(score)
    for i, name in enumerate(dow_names):
        if dow_scores[i]:
            avg = sum(dow_scores[i]) / len(dow_scores[i])
            n = len(dow_scores[i])
            bar_len = int((avg + 1) * 15)
            bar = "#" * max(bar_len, 0)
            dots = "." * 15
            print(f"  {name}  n={n:2d}  avg={avg:+.3f}  |{dots}|{bar}")
        else:
            print(f"  {name}  n= 0  avg=  n/a  |")
    print()
    print("=" * 65)
    print("   VIBE TRAJECTORY (raw daily scores)")
    print("=" * 65)
    print(ascii_chart(dates, scores))
    print()
    print("=" * 65)
    print("   7-DAY MOVING AVERAGE TREND")
    print("=" * 65)
    if len(scores) >= 7:
        ma, ma_dates = [], []
        for i in range(len(scores) - 6):
            window = scores[i:i + 7]
            ma.append(sum(window) / len(window))
            ma_dates.append(dates[i + 6])
        print(ascii_chart(ma_dates, ma))
        first_q = ma[:len(ma) // 4] if ma else [0]
        last_q = ma[-len(ma) // 4:] if ma else [0]
        early = sum(first_q) / len(first_q)
        late = sum(last_q) / len(last_q)
        delta = late - early
        if delta > 0.1: trend = "TRENDING UP. things are getting better king. dont fumble."
        elif delta < -0.1: trend = "TRENDING DOWN. the vibes are fading. do something."
        else: trend = "FLAT. consistent energy. no major progress either way."
        print()
        print(f"  Early avg: {early:+.3f}  |  Recent avg: {late:+.3f}  |  Delta: {delta:+.3f}")
        print(f"  >> {trend}")
    print()
    print("=" * 65)
    print("   FINAL STATISTICAL VERDICT")
    print("=" * 65)
    avg_all = sum(scores) / len(scores)
    pos_days = sum(1 for s in scores if s > 0.1)
    neg_days = sum(1 for s in scores if s < -0.1)
    ratio = pos_days / max(neg_days, 1)
    initiated = sum(1 for d in dates if day_msgs[d] and day_msgs[d][0][1] == "her")
    print(f"  Overall average vibe:  {avg_all:+.3f}")
    print(f"  Good days / bad days:  {pos_days} / {neg_days} (ratio: {ratio:.1f}x)")
    print(f"  Days she texted first: {initiated}")
    if avg_all > 0.3:
        print()
        print(f"  VERDICT: shes into you. the data doesnt lie. shoot your shot.")
    elif avg_all > 0.1:
        print()
        print(f"  VERDICT: theres something there but shes not all-in yet.")
        print(f"           youre in the evaluation phase. dont blow it.")
    elif avg_all > -0.1:
        print()
        print(f"  VERDICT: its a coin flip bro. the data is as confused as you are.")
    else:
        print()
        print(f"  VERDICT: the numbers say youre cooked. but hey, outliers exist.")
    conn.close()


if __name__ == "__main__":
    main()
