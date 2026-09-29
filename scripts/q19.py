import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
def q(l,s,a=None):
    cur.execute(s,a or ()); print("### "+l); rows=cur.fetchall()
    if not rows: print("    <no rows>")
    for r in rows: print("   ",r)
    print()
q("notification_prefs", "SELECT * FROM notification_prefs LIMIT 30")
q("notification_channels", "SELECT id,kind,enabled FROM notification_channels")
q("notifications count", "SELECT count(*) FROM notifications")
q("notification_outbox kinds", "SELECT kind,status,count(*) FROM notification_outbox GROUP BY kind,status ORDER BY kind")
conn.close()
