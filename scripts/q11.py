import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
def q(l,s,a=None):
    cur.execute(s,a or ()); print("### "+l); rows=cur.fetchall()
    if not rows: print("    <no rows>")
    for r in rows: print("   ",r)
    print()
q("tickets by type/status", "SELECT type,status,count(*) FROM itsm_tickets GROUP BY type,status ORDER BY type,status")
q("all tickets", "SELECT id,number,type,status,requester_id,assignee_id,assignee_role_id,catalog_item_id,resolution_code,fulfillment_job_id FROM itsm_tickets ORDER BY id")
q("wf_instances", "SELECT id,definition_key_placeholder FROM wf_instances LIMIT 1") if False else None
q("wf_instances cols", "SELECT column_name FROM information_schema.columns WHERE table_name='wf_instances'")
q("wf_instances", "SELECT id,definition_id,status,subject_type,subject_id FROM wf_instances ORDER BY id")
q("wf_tasks", "SELECT id,instance_id,node_id,status,assignee_user_id,assignee_role_id FROM wf_tasks ORDER BY id LIMIT 30")
conn.close()
