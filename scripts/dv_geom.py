# -*- coding: utf-8 -*-
"""量卡片布局的真实几何：色轮/左右两列各占多大、空白出现在哪（用数字说话）。

用法：python scripts/dv_geom.py [选择器] [宽]
默认：.card[id^=r-] 宽 412（手机）
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

sel = sys.argv[1] if len(sys.argv) > 1 else '.card[id^=r-]'
w = sys.argv[2] if len(sys.argv) > 2 else '412'
prejs = sys.argv[3] if len(sys.argv) > 3 else ''      # 可选的 pre-js，例如先点开某页签
print('[%s @ %spx 宽] pre-js=%s' % (sel, w, prejs or '无'))

head = ("<script>window.__OM3_APP__=1;</script>"
        "<script>setTimeout(function(){try{%s}catch(e){}},2000);</script>" % prejs)

t = []
t.append("setTimeout(function(){var o=[];")
t.append("var card=document.querySelector(%r);" % sel)
t.append("if(!card){o.push('找不到目标');}")
t.append("function R(e){if(!e)return '无';var r=e.getBoundingClientRect();"
         "return Math.round(r.left)+','+Math.round(r.top)+'  '+Math.round(r.width)+'x'+Math.round(r.height);}")
t.append("function cs(e,p){return e?getComputedStyle(e)[p]:'无';}")
t.append("if(card){")
t.append("  o.push('卡片        '+R(card));")
t.append("  /* 优化版槽位卡（.oslot）用 .osbody / .oswheel / .osinfo */")
t.append("  var ob=card.querySelector('.osbody');")
t.append("  if(ob){")
t.append("    var ow=card.querySelector('.oswheel'), oi=card.querySelector('.osinfo');")
t.append("    o.push('.osbody     display='+cs(ob,'display')+'  flex-direction='+cs(ob,'flexDirection')+'  '+R(ob));")
t.append("    o.push('.oswheel    '+R(ow));")
t.append("    o.push('.osinfo     '+R(oi));")
t.append("    if(ow&&ob){var br=ob.getBoundingClientRect(),wr0=ow.getBoundingClientRect();")
t.append("      o.push('色轮列下方空白='+Math.round(br.bottom-wr0.bottom)+'px（列宽 '+Math.round(wr0.width)+'px，槽位卡高 '+Math.round(br.height)+'px）');}")
t.append("  }")
t.append("  var body=card.querySelector('.cbody');")
t.append("  o.push('.cbody      有点='+!!body+'  display='+cs(body,'display')+'  flex-direction='+cs(body,'flexDirection')+'  '+R(body));")
t.append("  var L=card.querySelector('.cleft'), Rt=card.querySelector('.cright');")
t.append("  o.push('.cleft      有点='+!!L+'  width(css)='+cs(L,'width')+'  align-items='+cs(L,'alignItems')+'  '+R(L));")
t.append("  o.push('.cright     有点='+!!Rt+'  '+R(Rt));")
t.append("  var wl=card.querySelector('.wheel');")
t.append("  o.push('.wheel      '+R(wl)+'  (css '+cs(wl,'width')+')');")
t.append("  /* 色轮在它那一行里的左右空白 */")
t.append("  if(L&&wl){var lr=L.getBoundingClientRect(),wr=wl.getBoundingClientRect();")
t.append("    o.push('色轮左侧空白='+Math.round(wr.left-lr.left)+'px  右侧空白='+Math.round(lr.right-wr.right)+'px  居中='+((Math.abs((wr.left-lr.left)-(lr.right-wr.right))<=2)?'是':'否'));")
t.append("    o.push('色轮这一行高度='+Math.round(lr.height)+'px，色轮自己高='+Math.round(wr.height)+'px → 行内多余高度='+Math.round(lr.height-wr.height)+'px');")
t.append("  }")
t.append("  /* 色轮下方到下一块内容之间有没有大空白 */")
t.append("  if(wl&&Rt){var wr2=wl.getBoundingClientRect(),rr=Rt.getBoundingClientRect();")
t.append("    o.push('色轮底部→.cright 顶部间距='+Math.round(rr.top-wr2.bottom)+'px');}")
t.append("  o.push('  （注：.cright 在堆叠布局下应位于色轮下方）');")
t.append("  var vs=card.querySelectorAll('.vals,.vlegend,.shots,.cleft');")
t.append("  for(var i=0;i<vs.length;i++)o.push('  .'+vs[i].className.split(' ')[0]+'  '+R(vs[i]));")
t.append("}")
t.append("var d=document.createElement('pre');d.id='DBGOUT';d.textContent=o.join('\\n');document.body.appendChild(d);")
t.append("},2600);")
tail = '<script>' + ''.join(t) + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_geom.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\ogeom'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=%s,1400' % w,
                    '--virtual-time-budget=12000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=200)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print(dom[k:].split('>', 1)[1].split('</pre>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom)))
