import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
def q(l,s,a=None):
    cur.execute(s,a or ()); print("### "+l); rows=cur.fetchall()
    if not rows: print("    <no rows>")
    for r in rows: print("   ",r)
    print()
q("wf_instances", "SELECT id,definition_version_id,subject_type,subject_id,status,initiated_by,initiator_name,started_at,finished_at,hooks_applied_at FROM wf_instances ORDER BY id")
q("wf_tasks cols", "SELECT column_name FROM information_schema.columns WHERE table_name='wf_tasks'")
q("wf_tasks", "SELECT id,instance_id,node_id,status,assignee_user_id,assignee_role_id,created_at FROM wf_tasks ORDER BY id")
q("role_bindings role 1", "SELECT * FROM role_bindings WHERE role_id=1")
conn.close()
