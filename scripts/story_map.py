import io
import re

p = "D:/workspace/github/lcp-github/docs/端到端回归测试总纲.md"
lines = io.open(p, encoding="utf-8").read().splitlines()
starts = [(i, l) for i, l in enumerate(lines) if re.match(r"^## \d", l) or l.startswith("## 附录")]
for idx, (i, l) in enumerate(starts):
    end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
    body = lines[i:end]
    if "故事" not in l:
        continue
    routes = []
    for bl in body:
        for m in re.finditer(r"`(/(?:[a-z][\w-]*)(?:/[\w{}:-]+)*)`", bl):
            r = m.group(1)
            if r.count("/") >= 2 and "api" not in r.split("/")[1]:
                routes.append(r)
    seen, uniq = set(), []
    for r in routes:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    subs = " | ".join(re.sub(r"^#{3,4}\s*", "", b) for b in body if re.match(r"^#{3,4} ", b))
    print("### " + l)
    print("   子步骤: " + subs[:700])
    print("   涉及路由: " + ", ".join(uniq[:40]))
    print()
