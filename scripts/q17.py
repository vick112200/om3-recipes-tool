import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
print("users cols:", [r[0] for r in cur.fetchall()])
cur.execute("SELECT id,username,status,(password_hash IS NOT NULL) AS has_pw FROM users WHERE id IN (1,13)")
for r in cur.fetchall(): print(r)
conn.close()
