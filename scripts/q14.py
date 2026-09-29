import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
def q(l,s,a=None):
    cur.execute(s,a or ()); print("### "+l); rows=cur.fetchall()
    if not rows: print("    <no rows>")
    for r in rows: print("   ",r)
    print()
q("request tickets ws", "SELECT id,number,type,status,requester_id,workspace_id,catalog_item_id,assignee_role_id,source,title FROM itsm_tickets WHERE type='request' ORDER BY id")
q("all tickets ws", "SELECT id,number,workspace_id FROM itsm_tickets ORDER BY id")
conn.close()
