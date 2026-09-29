# -*- coding: utf-8 -*-
"""验收：搜索按页签分范围。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'

PROBE = '''<script>
function typeIn(el,v){el.value=v;el.dispatchEvent(new Event('input'));}
setTimeout(function(){
  var o=[];
  // --- 优化版页签 ---
  document.querySelector('.tabs button[data-p="B"]').click();
  setTimeout(function(){
    document.getElementById('tocbtn').click();
    setTimeout(function(){
      var q2=document.getElementById('toc2q'), r=document.getElementById('toc2res');
      typeIn(q2,'夜景');
      setTimeout(function(){
        var hs=[].slice.call(r.querySelectorAll('a')).map(function(a){return a.getAttribute('href');});
        o.push('[优化版] 搜"夜景" → '+hs.length+' 条，全是优化版='+hs.every(function(x){return x.charAt(1)==='o';})+' :: '+hs.join(','));
        typeIn(q2,'OMTC');
        setTimeout(function(){
          var hs2=[].slice.call(r.querySelectorAll('a')).map(function(a){return a.getAttribute('href');});
          o.push('[优化版] 搜"OMTC"（只有原版有）→ '+hs2.length+' 条，空提示='+(document.getElementById('noresult2').style.display==='block'));
          typeIn(q2,'Portra');
          setTimeout(function(){
            var hs3=[].slice.call(r.querySelectorAll('a')).map(function(a){return a.getAttribute('href');});
            o.push('[优化版] 搜"Portra" → '+hs3.length+' 条 :: '+hs3.join(','));
            // --- 原版页签 ---
            document.querySelector('.tabs button[data-p="A"]').click();
            setTimeout(function(){
              document.getElementById('tocbtn').click();
              var q=document.getElementById('tocq'), r1=document.getElementById('tocres');
              typeIn(q,'Q116');
              setTimeout(function(){
                var hs4=[].slice.call(r1.querySelectorAll('a')).map(function(a){return a.getAttribute('href');});
                o.push('[原版] 搜"Q116" → '+hs4.length+' 条，无优化版条目='+hs4.every(function(x){return x.charAt(1)!=='o';})+' :: '+hs4.join(','));
                typeIn(q,'夜间街头');
                setTimeout(function(){
                  var hs5=[].slice.call(r1.querySelectorAll('a')).map(function(a){return a.getAttribute('href');});
                  o.push('[原版] 搜"夜间街头" → '+hs5.length+' 条 :: '+hs5.join(','));
                  var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');
                  document.body.appendChild(d);
                },400);
              },400);
            },300);
          },400);
        },400);
      },500);
    },600);
  },800);
},2200);
</script>'''

h = open(BASE + r'\app\base.html', encoding='utf-8').read()
open(BASE + r'\dv_sc.html', 'w', encoding='utf-8', newline='').write(h.replace('</body>', PROBE + '</body>', 1))
print('已生成 dv_sc.html')
