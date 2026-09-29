import psycopg2
conn = psycopg2.connect(host="172.26.136.55", port=30491, user="lcp", password="lcp", dbname="lcp-dev")
cur = conn.cursor()
def q(label, sql, args=None):
    cur.execute(sql, args or ())
    print("### "+label)
    for r in cur.fetchall(): print("   ", r)
    print()

q("itsm_catalog_items count", "SELECT count(*) FROM itsm_catalog_items")
q("itsm_catalog_items rows", "SELECT id,name,status,workflow_key,fulfillment_kind FROM itsm_catalog_items LIMIT 20")
q("itsm_tickets count", "SELECT count(*) FROM itsm_tickets")
q("wf_definitions", "SELECT id,key,name,status FROM wf_definitions ORDER BY id LIMIT 50")
q("wf_definition_versions", "SELECT id,definition_id,version,status FROM wf_definition_versions ORDER BY id LIMIT 50")
q("users", "SELECT id,username,display_name FROM users ORDER BY id LIMIT 30")
q("roles", "SELECT id,name,scope,is_builtin FROM roles ORDER BY id LIMIT 60")
conn.close()
