import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
cur.execute("""SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND (table_name LIKE 'itsm%' OR table_name LIKE 'workflow%' OR table_name LIKE '%catalog%') ORDER BY table_name""")
print("TABLES:", [r[0] for r in cur.fetchall()])
conn.close()
