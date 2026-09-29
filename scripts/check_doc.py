import io
import re
from collections import Counter

p = "D:/workspace/github/lcp-github/docs/LCP功能说明书.html"
s = io.open(p, encoding="utf-8").read()

ids = re.findall(r'\sid="([^"]+)"', s)
dup = [k for k, v in Counter(ids).items() if v > 1]
print("元素 id 总数:", len(ids), "重复:", dup[:10])

hrefs = re.findall(r'href="#([^"]+)"', s)
missing = sorted(set(h for h in hrefs if h not in set(ids)))
print("内部链接数:", len(hrefs), "指向不存在的锚点:", missing[:20])

print("页面卡片:", s.count('class="page"'), " 场景:", s.count('class="scene"'), " 模块段:", s.count('class="mod"'))
print("有说明文字的卡片:", s.count('class="desc"'), "/ 129")
print("未闭合 body/html:", s.rstrip().endswith("</html>"))
print("总字节:", len(s.encode("utf-8")))
# 场景步骤里的页面链接是否都指向真页面
steplinks = re.findall(r'class="pagelink" href="#([^"]+)"', s)
print("场景步骤链接:", len(steplinks), "断链:", sorted(set(x for x in steplinks if x not in set(ids)))[:10])
