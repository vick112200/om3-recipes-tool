import psycopg2, json
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='roles'")
print("roles cols:", [r[0] for r in cur.fetchall()])
cur.execute("SELECT id,name,scope,workspace_id,display_name FROM roles WHERE id IN (1,1007,1006,1010,987)")
print("roles detail:", cur.fetchall())
cur.execute("SELECT graph FROM wf_definition_versions WHERE definition_id=2")
g = cur.fetchone()[0]
print(json.dumps(g, ensure_ascii=False, indent=1)[:4000])
conn.close()
