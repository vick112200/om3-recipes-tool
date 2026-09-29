import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
def q(l,s,a=None):
    cur.execute(s,a or ()); print("### "+l); rows=cur.fetchall()
    if not rows: print("    <no rows>")
    for r in rows: print("   ",r)
    print()
q("wf_tasks", "SELECT id,instance_id,node,attempt,quorum,assignee,status,created_at,opened_at,closed_at FROM wf_tasks ORDER BY id")
q("wf_tasks for inst 9,19", "SELECT id,instance_id,node,assignee,status FROM wf_tasks WHERE instance_id IN (9,19)")
q("wf_events cols", "SELECT column_name FROM information_schema.columns WHERE table_name='wf_events'")
q("wf_events inst 9,19", "SELECT id,instance_id,seq,type,node,actor_id,actor_name,payload,created_at FROM wf_events WHERE instance_id IN (9,19) ORDER BY instance_id,seq")
conn.close()
