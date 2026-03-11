import sqlite3, random, json
from datetime import datetime, timedelta
import os

random.seed(42)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "msg_data.json")) as f:
    data = json.load(f)

# Convert lists back to tuples
def to_tuples(lst):
    return [[(s, t) for s, t in convo] for convo in lst]

F = to_tuples(data['F'])
D = to_tuples(data['D'])
L = to_tuples(data['L'])
S = to_tuples(data['S'])
N = to_tuples(data['N'])
H = to_tuples(data['H'])
G = to_tuples(data['G'])

msgs = []
start = datetime(2025, 11, 1, 8, 0, 0)
cur = start
end = start + timedelta(days=150)
pool = [('f', c) for c in F]*3 + [('d', c) for c in D]*3 + [('l', c) for c in L]*2 + [('n', c) for c in N]*4 + [('h', c) for c in H]*2 + [('g', c) for c in G]*1

while len(msgs) < 1500 and cur < end:
    nb = random.choices([1, 2, 3], weights=[0.4, 0.45, 0.15])[0]
    bt = cur.replace(hour=random.randint(8, 11), minute=random.randint(0, 59))
    for bi in range(nb):
        a, cv = random.choice(pool)
        if bi > 0:
            bt += timedelta(hours=random.randint(2, 5), minutes=random.randint(0, 59))
            if bt.hour > 23:
                break
        mt = bt
        for s, t in cv:
            if s == 'me':
                mt += timedelta(minutes=random.randint(0, 8), seconds=random.randint(0, 59))
            else:
                if a == 'd':
                    mt += timedelta(minutes=random.randint(15, 90), seconds=random.randint(0, 59))
                elif a == 'f':
                    mt += timedelta(minutes=random.randint(0, 5), seconds=random.randint(0, 59))
                else:
                    mt += timedelta(minutes=random.randint(1, 20), seconds=random.randint(0, 59))
            msgs.append((mt.strftime('%Y-%m-%d %H:%M:%S'), s, t))

    if random.random() < 0.08:
        st = cur.replace(hour=random.randint(1, 3), minute=random.randint(0, 59)) + timedelta(days=1)
        sb = random.choice(S)
        t2 = st
        for s, t in sb:
            t2 += timedelta(seconds=random.randint(5, 120))
            msgs.append((t2.strftime('%Y-%m-%d %H:%M:%S'), s, t))

    cur += timedelta(days=random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0])

msgs.sort(key=lambda x: x[0])

conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mixed_signals.db"))
c = conn.cursor()
c.execute('DELETE FROM messages')
c.executemany('INSERT INTO messages (timestamp, sender, message_text, vibe_score) VALUES (?, ?, ?, NULL)', msgs)
conn.commit()

# Stats
total = c.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
me_n = c.execute("SELECT COUNT(*) FROM messages WHERE sender='me'").fetchone()[0]
her_n = c.execute("SELECT COUNT(*) FROM messages WHERE sender='her'").fetchone()[0]
dr = c.execute('SELECT MIN(timestamp), MAX(timestamp) FROM messages').fetchone()
days = c.execute('SELECT COUNT(DISTINCT DATE(timestamp)) FROM messages').fetchone()[0]
dry_d = c.execute("SELECT COUNT(DISTINCT DATE(timestamp)) FROM messages WHERE message_text IN ('k','ok','cool','not really','busy','stuff','fine','nm')").fetchone()[0]
sp_d = c.execute("SELECT COUNT(DISTINCT DATE(timestamp)) FROM messages WHERE message_text LIKE '%spotify%'").fetchone()[0]
ghost_d = c.execute("SELECT COUNT(DISTINCT d) FROM (SELECT DATE(timestamp) as d FROM messages GROUP BY DATE(timestamp) HAVING COUNT(CASE WHEN sender='her' THEN 1 END) = 0)").fetchone()[0]

sep = '=' * 42
print(sep)
print('   mixed_signals.db SEEDED')
print(sep)
print(f'  Total messages:    {total}')
print(f'  From me:           {me_n} ({100*me_n//total}%)')
print(f'  From her:          {her_n} ({100*her_n//total}%)')
print(f'  Date range:        {dr[0][:10]} -> {dr[1][:10]}')
print(f'  Active days:       {days}')
print(f'  Days w/ dry vibes: {dry_d}')
print(f'  2am spotify drops: {sp_d}')
print(f'  Left on read days: {ghost_d}')
print(sep)

print()
print('--- SAMPLE: Flirty Day ---')
for r in c.execute("SELECT timestamp, sender, message_text FROM messages WHERE DATE(timestamp) = (SELECT DATE(timestamp) FROM messages WHERE message_text LIKE '%dream about you%' LIMIT 1) ORDER BY timestamp").fetchall():
    print(f'  [{r[0][11:16]}] {r[1]}: {r[2]}')

print()
print('--- SAMPLE: Dry Day ---')
for r in c.execute("SELECT timestamp, sender, message_text FROM messages WHERE DATE(timestamp) = (SELECT DATE(timestamp) FROM messages WHERE message_text = 'k' LIMIT 1) ORDER BY timestamp").fetchall():
    print(f'  [{r[0][11:16]}] {r[1]}: {r[2]}')

print()
print('--- SAMPLE: 2am Spotify Drop ---')
for r in c.execute("SELECT timestamp, sender, message_text FROM messages WHERE message_text LIKE '%spotify%' ORDER BY timestamp LIMIT 4").fetchall():
    print(f'  [{r[0][11:16]}] {r[1]}: {r[2]}')

print()
print('--- SAMPLE: Left on Read ---')
for r in c.execute("SELECT timestamp, sender, message_text FROM messages WHERE DATE(timestamp) IN (SELECT DATE(timestamp) FROM messages GROUP BY DATE(timestamp) HAVING COUNT(CASE WHEN sender='her' THEN 1 END) = 0) ORDER BY timestamp LIMIT 6").fetchall():
    print(f'  [{r[0][11:16]}] {r[1]}: {r[2]}')

conn.close()
