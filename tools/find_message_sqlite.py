import sqlite3, os, sys
needle = sys.argv[1] if len(sys.argv) > 1 else "1117924663"
db_path = os.path.join(os.getcwd(), 'poc.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", ", ".join(tables))
if 'messagelog' not in tables:
    print('messagelog table not found in', db_path)
    raise SystemExit(1)

q = ("SELECT id, correlation_id, status, message_type, kind, direction, endpoint_id, "
     "substr(payload,1,500) as payload_head, substr(ack_payload,1,1000) as ack_head "
     "FROM messagelog WHERE correlation_id = ? OR payload LIKE ? ORDER BY id DESC")
rows = list(cur.execute(q, (needle, f"%{needle}%")))
print(f"Found {len(rows)} messages matching {needle}\n")
for r in rows:
    print(dict(r))
    print("====\n")
