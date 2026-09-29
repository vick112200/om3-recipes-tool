# -*- coding: utf-8 -*-
"""生成三张验收截图页：未连接 / 已连接 / 导入记录。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
BASE = open(TMP + r'\app\base.html', encoding='utf-8').read()
i = BASE.find('<body')
j = BASE.find('>', i) + 1
BASE = BASE[:j] + '<script>window.__OM3_APP__=1;</script>\n' + BASE[j:]

RECS = ("localStorage.setItem('om3cam',JSON.stringify({ssid:'OM-3-P-BJSA21721',pass:'8221759294751531'}));"
        "window.__om3impRecord({slug:'a',n:'Real',a:'Murder Pink'},'C1',1);"
        "window.__om3impRecord({slug:'b',n:'Kinda Portra',a:'Ian Will'},'current',1);"
        "window.__om3impRecord({slug:'b',n:'Kinda Portra',a:'Ian Will'},'C5',2);"
        "window.__om3impRecord({slug:'c',n:'Velvia 50',a:'VideoPic'},'C3',4);")

JOBS = [
    ('dv_c1.html', "window.__om3setConn(false);"),
    ('dv_c2.html', RECS + "window.__om3setConn(true);"),
    ('dv_c3.html', RECS + "window.__om3setConn(true);window.__camStep(4);"),
    ('dv_c4.html', "document.querySelector('.tabs.ver button[data-p=\"A\"]').click();"
                   "setTimeout(function(){window.__om3setConn(true);var b=document.querySelector('.om3imp');if(b)b.scrollIntoView({block:'center'});},300);"),
]
for name, extra in JOBS:
    js = ("<script>setTimeout(function(){document.getElementById('tabD').click();"
          "setTimeout(function(){" + extra + "},400);},1600);</script>")
    open(TMP + '\\' + name, 'w', encoding='utf-8', newline='').write(BASE.replace('</body>', js + '</body>', 1))
print('已生成 4 个截图页')
