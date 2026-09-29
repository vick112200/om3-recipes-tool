import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
cur.execute("SELECT id,username,left(password_hash,12) FROM users WHERE id IN (1,12,13,14,15,16)")
for r in cur.fetchall(): print(r)
conn.close()
