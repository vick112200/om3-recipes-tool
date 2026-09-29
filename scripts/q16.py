import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
def q(l,s,a=None):
    cur.execute(s,a or ()); print("### "+l); rows=cur.fetchall()
    if not rows: print("    <no rows>")
    for r in rows: print("   ",r)
    print()
q("notes request tickets", "SELECT ticket_id,author_id,visibility,body,created_at FROM itsm_ticket_notes WHERE ticket_id IN (11,12,13,14,22,23,24,25) ORDER BY ticket_id,created_at")
q("wf_events service-request", "SELECT instance_id,seq,kind,node,actor_id,actor_name,payload FROM wf_events WHERE instance_id IN (7,8,9,17,18,19) ORDER BY instance_id,seq")
conn.close()
