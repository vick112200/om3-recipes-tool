# -*- coding: utf-8 -*-
"""验收：优化版搜索 + 场景对比双跳转。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'

SEARCH = '''<script>
setTimeout(function(){
  var o=[];
  document.querySelector('.tabs button[data-p="B"]').click();
  setTimeout(function(){
    document.getElementById('tocbtn').click();
    setTimeout(function(){
      o.push('B面板 toc2 open='+document.getElementById('toc2').classList.contains('open'));
      o.push('toc2 有搜索框='+(!!document.getElementById('toc2q'))+' 可见='+(document.getElementById('toc2q').offsetParent!==null));
      var q2=document.getElementById('toc2q');
      q2.value='夜景'; q2.dispatchEvent(new Event('input'));
      setTimeout(function(){
        var r=document.getElementById('toc2res');
        var links=r.querySelectorAll('a');
        var hrefs=[].slice.call(links).map(function(a){return a.getAttribute('href');});
        o.push('B面板搜"夜景" 结果='+links.length+' 其中优化版条目='+hrefs.filter(function(x){return x.charAt(1)==='o';}).length
               +' browse隐藏='+(document.getElementById('toc2browse').className==='hide'));
        o.push('首条='+(links[0]?links[0].querySelector('.rn').textContent+'@'+hrefs[0]:'无'));
        var tgt=null;
        for(var i=0;i<links.length;i++){if(hrefs[i].charAt(1)==='o'){tgt=links[i];break;}}
        if(tgt)tgt.click();
        setTimeout(function(){
          var id=tgt?tgt.getAttribute('href').slice(1):'';
          var el=document.getElementById(id);
          o.push('点优化版条目 '+id+' → 页签='+(document.querySelector('.tabs button.on')||{}).textContent
                 +' 高亮='+(el?el.className.indexOf('flashcard')>=0:'-')
                 +' 所在档位显示='+(el&&el.closest('.omode')?el.closest('.omode').style.display||'(默认)':'-'));
          document.querySelector('.tabs button[data-p="A"]').click();
          setTimeout(function(){
            document.getElementById('tocbtn').click();
            var q=document.getElementById('tocq'); q.value='Q116'; q.dispatchEvent(new Event('input'));
            setTimeout(function(){
              var r1=document.getElementById('tocres');
              var h1=[].slice.call(r1.querySelectorAll('a')).map(function(a){return a.getAttribute('href');});
              o.push('A面板搜"Q116" 结果='+h1.length+' 含优化版='+h1.filter(function(x){return x.charAt(1)==='o';}).length+' → '+h1.join(','));
              var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');
              document.body.appendChild(d);
            },400);
          },300);
        },700);
      },600);
    },600);
  },700);
},2200);
</script>'''

JUMP = '''<script>
setTimeout(function(){
  var o=[];
  document.querySelector('.tabs button[data-p="C"]').click();
  setTimeout(function(){
    var pg=document.getElementById('scpager');
    var s0=pg.querySelectorAll('.scslide')[0];
    o.push('第1张：原版按钮='+(!!s0.querySelector('.scjump'))+' 优化版按钮='+(!!s0.querySelector('.scjump2'))
           +' 提示='+(s0.querySelector('.scnoplan')?s0.querySelector('.scnoplan').textContent:'无'));
    var withOs=null;
    var all=pg.querySelectorAll('.scslide');
    for(var i=0;i<all.length;i++){if(all[i].querySelector('.scjump2')){withOs=all[i];break;}}
    if(withOs){
      var b=withOs.querySelector('.scjump2');
      o.push('找到带优化版按钮的：'+withOs.querySelector('.scname').textContent+' → '+b.textContent+'['+b.getAttribute('data-jump')+']');
      b.click();
      setTimeout(function(){
        var id=b.getAttribute('data-jump');
        var el=document.getElementById(id);
        o.push('跳转='+id+' 页签='+(document.querySelector('.tabs button.on')||{}).textContent
               +' 高亮='+(el?el.className.indexOf('flashcard')>=0:'-'));
        // 回对比页看全屏按钮
        document.querySelector('.tabs button[data-p="C"]').click();
        setTimeout(function(){
          pg.querySelectorAll('.scslide')[0].querySelector('img').click();
          setTimeout(function(){
            var bs=document.querySelectorAll('#lbbot .lbdetail');
            o.push('全屏按钮数='+bs.length+' 文案='+[].slice.call(bs).map(function(x){return x.textContent;}).join(' / ')
                   +' 提示='+(document.querySelector('.lbnoplan')?'有':'无'));
            document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}));
            var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');
            document.body.appendChild(d);
          },600);
        },500);
      },700);
    } else { o.push('本场没有带优化版按钮的条目'); }
  },900);
},2200);
</script>'''

h = open(BASE + r'\app\base.html', encoding='utf-8').read()
open(BASE + r'\dv_s1.html', 'w', encoding='utf-8', newline='').write(h.replace('</body>', SEARCH + '</body>', 1))
open(BASE + r'\dv_s2.html', 'w', encoding='utf-8', newline='').write(h.replace('</body>', JUMP + '</body>', 1))
print('已生成 dv_s1.html / dv_s2.html')
