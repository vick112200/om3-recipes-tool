import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
def q(l,s,a=None):
    cur.execute(s,a or ()); print("### "+l); rows=cur.fetchall()
    if not rows: print("    <no rows>")
    for r in rows: print("   ",r)
    print()
q("user 13 status", "SELECT id,username,status,email FROM users WHERE id IN (1,13)")
q("ops_scripts detail", "SELECT id,name,scope,workspace_id,namespace_id,language FROM ops_scripts")
q("hosts 243 detail", "SELECT id,name,workspace_id,status FROM hosts WHERE id=243")
conn.close()
