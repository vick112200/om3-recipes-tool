import io
import json
import re

pages = json.load(io.open("C:/Users/82302/AppData/Local/Temp/lcp-pages.json", encoding="utf-8"))["pages"]
md = io.open("D:/workspace/github/lcp-github/docs/端到端回归测试总纲.md", encoding="utf-8").read()
summ = {}
for line in md.splitlines():
    m = re.match(r"^\|\s*([^|]+?)\s*\|\s*(.+?)\s*\|\s*(?:✅|◐|❌)", line)
    if m:
        summ.setdefault(m.group(1), m.group(2))
missing = [(p["module"], p["resource"], p["name"]) for p in pages if p["name"] not in summ]
print(len(missing), "pages without desc")
for mod, res, name in missing:
    print("%s/%s = %s" % (mod, res, name))
