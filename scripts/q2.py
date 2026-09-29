import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
cur.execute("""SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name""")
t=[r[0] for r in cur.fetchall()]
print("ALL TABLES (%d):"%len(t))
print(t)
conn.close()
