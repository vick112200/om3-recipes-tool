import sys, re, html
p = sys.argv[1]
s = open(p, encoding='utf-8', errors='ignore').read()
s = re.sub(r'(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>', ' ', s)
s = re.sub(r'(?i)<br\s*/?>', '\n', s)
s = re.sub(r'(?i)</(p|div|li|tr|h[1-6]|td)>', '\n', s)
s = re.sub(r'<[^>]+>', ' ', s)
s = html.unescape(s)
s = re.sub(r'[ \t\xa0]+', ' ', s)
s = re.sub(r'\n\s*\n+', '\n', s)
print(s.strip())
