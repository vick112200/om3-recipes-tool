# -*- coding: utf-8 -*-
"""「我的配方 · 方案」重做：
   · 列表只显示 名称 + 描述（干净）
   · 点开 → 详情页：标题/描述 + 各槽位列表（来源档位·槽位 / 项数 / 色轮）
   · 每个槽位可单独【写入相机】—— 用它自己的档位+槽位，无需再选
   · 详情页底部：整套写入 / 改名描述 / 分享 / 删除
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# 定位并整段替换旧 mpRender
i = h.find('  /* ---------- 界面：方案列表 ---------- */')
assert i > 0, 'mpRender 段没找到'
j = h.find('  /* ---------- 写入面板（选档位 + 槽位） ---------- */', i)
assert j > i, 'mpRender 段尾没找到'

NEW = r'''  /* ---------- 界面：方案列表（只有名称+描述） + 详情页（各槽位） ---------- */
  var mpCur = -1;   /* 当前打开的方案索引，-1 = 列表 */
  function mpRender(){
    var box = document.getElementById('mpList');
    if(!box) return;
    var a = setsAll();
    var c = document.getElementById('mpCount');
    if(c) c.textContent = a.length ? ('共 ' + a.length + ' 套') : '';
    box.innerHTML = '';
    if(mpCur >= 0 && a[mpCur]){ mpDetail(a[mpCur]); return; }
    if(!a.length){
      box.innerHTML = '<div class="mpempty">还没有方案。到「读取」页从相机读一份，或在配方卡上点「加入我的方案」。</div>';
      return;
    }
    a.forEach(function(s, idx){
      var used = 0; for(var q = 1; q <= 4; q++) if(s.slots && s.slots[q] && s.slots[q].used) used++;
      var d = document.createElement('div');
      d.className = 'mpitem';
      d.innerHTML = '<div class="t">' + (s.name || '未命名方案') + '</div>' +
        '<div class="s">' + (s.desc ? s.desc : (tierLabel(s.from || 'current') + ' · ' + used + ' 个槽位有内容')) + '</div>' +
        '<div class="s" style="opacity:.7">点开看各槽位 · 可单独导入相机</div>';
      d.addEventListener('click', function(){ mpCur = idx; mpRender(); });
      box.appendChild(d);
    });
  }

  /* 详情页：各槽位列表 + 单槽操作 */
  function mpDetail(s){
    var box = document.getElementById('mpList');
    if(!box) return;
    var srcTier = s.from || 'current';
    var head = document.createElement('div');
    head.className = 'mpitem';
    head.innerHTML = '<div class="r" style="margin:0 0 8px"><button type="button" id="mpBack" class="mpbtn" style="flex:none;padding:7px 12px">← 返回列表</button></div>' +
      '<div class="t">' + (s.name || '未命名方案') + '</div>' +
      '<div class="s">' + (s.desc || '（暂无描述）') + '</div>' +
      '<div class="s" style="opacity:.75">来源档位：' + tierLabel(srcTier) + '</div>';
    box.appendChild(head);

    for(var n = 1; n <= 4; n++){
      (function(n){
        var one = s.slots && s.slots[n];
        var row = document.createElement('div');
        row.className = 'mpitem';
        var info = one ? (one.used ? (one.used + ' 条色轴非默认') : '空/默认') : '空';
        var vivid = one && one.vivid ? one.vivid.join(',') : '';
        row.innerHTML = '<div class="t">槽 ' + n + '　<span style="font-weight:400;color:#9aa3a2;font-size:12.5px">' + tierLabel(srcTier) + ' · 槽' + n + '</span></div>' +
          '<div class="s">' + info + (vivid ? ('　色轮 [' + vivid + ']') : '') + '</div>' +
          (one ? '<div class="r">' +
            '<button type="button" data-w="' + n + '">写入相机（' + tierLabel(srcTier) + ' · 槽' + n + '）</button>' +
            '<button type="button" data-sh="' + n + '">分享这个槽</button>' +
            '<button type="button" data-oe="' + n + '">导出 .oes</button></div>' : '');
        box.appendChild(row);
      })(n);
    }

    var foot = document.createElement('div');
    foot.className = 'mpitem';
    foot.innerHTML = '<div class="r">' +
      '<button type="button" id="mpEdit">改名 / 描述</button>' +
      '<button type="button" id="mpExp">导出整套</button>' +
      '<button type="button" id="mpDel" class="mpbtn danger" style="flex:none">删除</button></div>';
    box.appendChild(foot);

    /* 交互 */
    var back = document.getElementById('mpBack');
    if(back) back.addEventListener('click', function(){ mpCur = -1; mpRender(); });
    box.querySelectorAll('button[data-w]').forEach(function(b){
      b.addEventListener('click', function(){ mpWriteOne(s, Number(b.getAttribute('data-w'))); });
    });
    box.querySelectorAll('button[data-sh]').forEach(function(b){
      b.addEventListener('click', function(){
        var n = Number(b.getAttribute('data-sh')), one = s.slots && s.slots[n];
        if(!one) return;
        var pack = { app: 'OM-3 色彩配方手册', kind: 'om3-colorprofile', version: 2, name: (s.name || '方案') + ' 槽' + n,
                     desc: (s.desc || '') + '（来源 ' + tierLabel(srcTier) + ' · 槽' + n + '）', from: srcTier, camera: s.camera || modelNow(),
                     slots: (function(){ var o = {1:null,2:null,3:null,4:null}; o[n] = one; return o; })() };
        om3Share((s.name || 'OM3') + '-槽' + n + '.json', JSON.stringify(pack, null, 1), 'text/plain');
      });
    });
    box.querySelectorAll('button[data-oe]').forEach(function(b){
      b.addEventListener('click', function(){
        var n = Number(b.getAttribute('data-oe')), one = s.slots && s.slots[n];
        if(!one) return;
        om3Download(oesName(one, (s.name || 'OM3方案') + '-槽' + n), oesBuild(one), 'text/xml');
        log('已导出 .oes：' + (s.name || '') + ' 槽' + n, 'ok');
      });
    });
    var be = document.getElementById('mpEdit');
    if(be) be.addEventListener('click', function(){
      var idx = mpCur;
      om3Ask({ title: '编辑方案', fields: [ { label: '方案名字', value: s.name || '' },
        { label: '描述（可选：作者 / 风格 / 备注）', value: s.desc || '', multiline: true } ], okText: '保存' }).then(function(r){
        if(!r) return;
        var a = setsAll(); a[idx].name = r[0] || s.name; a[idx].desc = r[1] || '';
        setsSave(a); mpRender(); log('已更新方案：' + a[idx].name, 'ok');
      });
    });
    var bx = document.getElementById('mpExp');
    if(bx) bx.addEventListener('click', function(){ mpExportOne(s); });
    var bd = document.getElementById('mpDel');
    if(bd) bd.addEventListener('click', function(){
      var idx = mpCur;
      om3Ask({ title: '删除方案', body: '删除「' + (s.name || '') + '」？不可撤销。', okText: '删除', danger: true }).then(function(okv){
        if(!okv) return;
        var a = setsAll(); a.splice(idx, 1); setsSave(a); mpCur = -1; mpRender(); log('已删除方案', 'ok');
      });
    });
  }

  /* 单个槽位 → 写入相机（用它自己的档位 + 槽位，无需再选） */
  function mpWriteOne(s, n){
    var one = s.slots && s.slots[n];
    if(!one || !one.raw || !Object.keys(one.raw).length){
      log('槽' + n + ' 没有可写入的键值数据（可能来自内置配方但未生成）', 'err'); toastMsg('这个槽没有数据'); return;
    }
    var tier = s.from || 'current';
    runTask('写入 ' + tierLabel(tier) + ' · 槽' + n, async function(){
      log('===== 写入方案「' + s.name + '」→ ' + tierLabel(tier) + ' · 槽' + n + '（' + Object.keys(one.raw).length + ' 项）');
      await readMySet(tier);                     /* 进维护模式 + 确认可达 */
      await writeRawKV(tier, n, one.raw);
      log('✅ 已下发。相机重启后到 ' + tierLabel(tier) + ' · 槽' + n + ' 查看', 'ok');
    });
  }
  window.__om3mpWriteOne = mpWriteOne;
  window.__om3mpDetail = function(i){ mpCur = i; mpRender(); };

'''
h = h[:i] + NEW + h[j:]
open(P, 'w', encoding='utf-8', newline='').write(h)
print('「我的配方」列表+详情页已重做（%+d 字节）' % (len(h) - n0))
