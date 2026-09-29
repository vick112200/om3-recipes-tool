import re, html, os, json, glob

def strip_tags(x):
    x = re.sub(r'<!--.*?-->', '', x, flags=re.S)
    x = re.sub(r'<[^>]+>', '', x)
    return html.unescape(x).strip()

rows = []
for f in sorted(glob.glob('C:/Users/82302/AppData/Local/Temp/html/*.html')):
    slug = os.path.basename(f)[:-5]
    s = open(f, encoding='utf-8').read()
    r = {'slug': slug}

    m = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S)
    r['name'] = strip_tags(m.group(1)) if m else slug

    # type badges
    badges = re.findall(r'rounded-full[^>]*>(?:<[^>]+>)*([^<]{2,40})</span>', s)
    badges = [strip_tags(b) for b in badges]
    r['badges'] = badges

    # author: span right after h1 block
    m = re.search(r'</h1>.*?text-muted-foreground[^>]*>\s*<span>([^<]+)</span>', s, re.S)
    r['author'] = html.unescape(m.group(1)).strip() if m else ''

    flat = re.sub(r'<!--.*?-->', '', s, flags=re.S)

    # white balance: block between the WB graph heading and the settings sliders
    i = flat.find('recipe-wb-adjust')
    seg = flat[i:] if i >= 0 else ''
    j = seg.find('Shading Effect')
    if j > 0:
        seg = seg[:j]
    t = strip_tags(seg)
    mk = re.search(r'(\d{3,5})K', t)
    r['kelvin'] = int(mk.group(1)) if mk else None
    r['wb_mode'] = re.sub(r'([ABGM])\.\s*\d+', ' ', t).strip()
    offs = re.findall(r'([ABGM])\.\s*(\d+)', t)
    r['wb1_axis'] = offs[0][0] if len(offs) > 0 else None
    r['wb1_val'] = int(offs[0][1]) if len(offs) > 0 else None
    r['wb2_axis'] = offs[1][0] if len(offs) > 1 else None
    r['wb2_val'] = int(offs[1][1]) if len(offs) > 1 else None

    m = re.search(r'>(Creative Color|Basic Color|Creative Mono|Basic Mono)<', flat)
    r['type'] = m.group(1) if m else ''

    for label, key in [('Shading Effect', 'shading'), ('Sharpness', 'sharpness'),
                       ('Contrast', 'contrast'), ('Exposure Comp', 'exposure')]:
        m = re.search(label + r':\s*(<[^>]*>)*\s*([-+]?[\d.]+)', flat)
        r[key] = m.group(2) if m else None

    m = re.search(r'Sh:\s*([-+]?\d+)\s*<', flat) or re.search(r'Sh:\s*([-+]?\d+)', flat)
    r['sh'] = m.group(1) if m else None
    m = re.search(r'Mid:\s*([-+]?\d+)', flat); r['mid'] = m.group(1) if m else None
    m = re.search(r'Hi:\s*([-+]?\d+)', flat); r['hi'] = m.group(1) if m else None

    rows.append(r)

# merge .oes
for r in rows:
    p = 'C:/Users/82302/AppData/Local/Temp/oes/%s.oes' % r['slug']
    r['oes'] = None
    if os.path.exists(p):
        x = open(p, encoding='utf-8').read()
        d = {}
        for tag in ['WhiteBalance', 'ToneControl', 'ColorCreater2', 'Contrast', 'Sharpness', 'ExposureBias', 'Monotone', 'ColorFilter', 'Gradation', 'RawEditMode']:
            m = re.search(r'<%s\b([^/>]*)/>' % tag, x)
            if m:
                d[tag] = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        r['oes'] = d
        r['oes_tags'] = re.findall(r'<(\w+)\s', x)

json.dump(rows, open('C:/Users/82302/AppData/Local/Temp/recipes.json', 'w'), indent=1)
print(len(rows), 'recipes')
for r in rows[:3]:
    print(json.dumps(r, ensure_ascii=False)[:600])
print('--- oes tags seen ---')
import collections
c = collections.Counter()
for r in rows:
    c.update(set(r.get('oes_tags') or []))
print(c)
print('--- badges ---')
c2 = collections.Counter()
for r in rows:
    c2[tuple(r['badges'])] += 1
for k, v in c2.most_common(20):
    print(v, k)
