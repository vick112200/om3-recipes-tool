import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
def q(l,s,a=None):
    cur.execute(s,a or ()); print("### "+l); rows=cur.fetchall()
    if not rows: print("    <no rows>")
    for r in rows: print("   ",r)
    print()
q("notification_channels", "SELECT * FROM notification_channels")
q("notifications", "SELECT id,user_id,kind,channel,status,created_at FROM notifications ORDER BY id DESC LIMIT 20")
q("notification_outbox itsm", "SELECT id,kind,status,created_at FROM notification_outbox WHERE kind LIKE 'itsm%' ORDER BY id DESC LIMIT 20")
conn.close()
