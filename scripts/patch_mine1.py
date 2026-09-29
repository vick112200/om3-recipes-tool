# -*- coding: utf-8 -*-
"""「我的配方」模块：
   · 方案库 om3sets：从相机读取某档位 → 存成一套方案（可多套、可切换、可改名/删除）
   · 写回相机：选档位 + 槽位（单槽 或 全部 4 槽）
   · 导出/导入文件（自带 kind 标记，可分享）
   · 档位管理 om3tiers：可增删改名（不是所有机器都有 5 个档位）
   界面：新增「我的配方」页签 paneE，卡片式布局
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- ① 顶部页签：加「我的配方」 ----------
old_tabs = '<button type="button" data-p="C">场景对比</button>'
assert h.count(old_tabs) == 1, h.count(old_tabs)
h = h.replace(old_tabs, old_tabs + '<button type="button" data-p="E">我的配方</button>', 1)

# ---------- ② 新面板 paneE + CSS ----------
k = h.find('</style>')
assert k > 0
h = h[:k] + """
/* ---------- 我的配方 ---------- */
.mpwrap{display:flex;flex-direction:column;gap:10px;margin-top:8px}
.mpcard{background:#161616;border:1px solid #262626;border-radius:12px;padding:12px}
.mpcard h3{margin:0 0 8px;font-size:14px;font-weight:600;color:#eee}
.mproll{display:flex;gap:8px;flex-wrap:wrap}
.mpbtn{flex:1;min-width:120px;padding:11px 10px;border-radius:10px;border:1px solid #333;background:#1e1e1e;color:#e8e8e8;font-size:13px}
.mpbtn.primary{background:#2b5cff;border-color:#2b5cff;color:#fff;font-weight:600}
.mpbtn.danger{color:#ff9a9a;border-color:#4a2a2a}
.mpitem{border:1px solid #2a2a2a;border-radius:10px;padding:10px;margin:8px 0;background:#1a1a1a}
.mpitem .t{font-size:14px;font-weight:600;color:#f0f0f0}
.mpitem .s{font-size:12px;color:#9a9a9a;margin-top:3px}
.mpitem .r{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.mpitem .r button{flex:1;min-width:80px;padding:8px;border-radius:8px;border:1px solid #333;background:#222;color:#ddd;font-size:12px}
.mpsel{display:flex;gap:8px;align-items:center;margin-top:8px;flex-wrap:wrap}
.mpsel select{padding:8px;border-radius:8px;border:1px solid #333;background:#1c1c1c;color:#eee;font-size:13px}
.mptier{display:flex;gap:6px;align-items:center;margin:6px 0}
.mptier input{flex:1;padding:8px;border-radius:8px;border:1px solid #333;background:#1c1c1c;color:#eee}
.mpempty{color:#8a8a8a;font-size:13px;padding:10px 2px}
""" + h[k:]

# 插到 paneD 之后（保证独立一页）
import re as _re
mD = _re.search(r'<div id="paneD"[^>]*>', h)
assert mD, 'paneD not found'
# 找到 paneD 的结尾：用 "</div>\s*<!--" 之后的第一个顶层收尾不可靠 → 直接追加到 body 末尾前
PANEL = '''
<!-- ============ 我的配方 ============ -->
<div id="paneE" class="pane hide">
  <h1>我的配方</h1>
  <div class="mpwrap">
    <div class="mpcard">
      <h3>① 从相机读取并保存</h3>
      <div class="mpsel">
        <span style="font-size:13px;color:#aaa">读取档位</span>
        <select id="mpReadTier"></select>
        <button type="button" id="mpRead" class="mpbtn primary" style="flex:none;padding:9px 14px">读取并保存为方案</button>
      </div>
    </div>
    <div class="mpcard">
      <h3>② 我的方案 <span id="mpCount" style="color:#888;font-weight:400"></span></h3>
      <div id="mpList"></div>
    </div>
    <div class="mpcard">
      <h3>③ 档位管理</h3>
      <div class="s" style="font-size:12px;color:#999;margin-bottom:6px">不是所有机器都有 5 个档位 —— 这里增删改名，读取/写入时用这份列表</div>
      <div id="mpTiers"></div>
      <div class="mproll" style="margin-top:8px">
        <button type="button" id="mpTierAdd" class="mpbtn">+ 添加档位</button>
        <button type="button" id="mpTierReset" class="mpbtn">恢复默认（OM-3）</button>
      </div>
    </div>
    <div class="mpcard">
      <h3>④ 文件</h3>
      <div class="mproll">
        <button type="button" id="mpExportAll" class="mpbtn">导出全部方案（文件）</button>
        <button type="button" id="mpImportFile" class="mpbtn">导入方案文件</button>
      </div>
      <div id="mpFileOut" class="camout" style="margin-top:8px">导出的文件可以分享给同样装了本 app 的人；对方导入后可选槽位填充。</div>
    </div>
  </div>
</div>
'''
mB = h.rfind('</body>')
assert mB > 0
h = h[:mB] + PANEL + h[mB:]

# 页签显隐：把 paneE 也纳入（patch 现有监听）
old_hide = "if (d4) d4.classList.toggle('hide', p !== 'D');"
if h.count(old_hide) == 1:
    h = h.replace(old_hide, old_hide + "\n      var e5 = document.getElementById('paneE');\n      if (e5) e5.classList.toggle('hide', p !== 'E');", 1)
else:
    # 兜底：给页签点击加一个独立监听
    old_paneD_hide = "c.classList.toggle('hide', p !== 'C');"
    assert h.count(old_paneD_hide) >= 1, 'pane hide hook not found'
    h = h.replace(old_paneD_hide, old_paneD_hide + "\n      var e5 = document.getElementById('paneE');\n      if (e5) e5.classList.toggle('hide', p !== 'E');", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('paneE + 页签 + 样式 已加（+%d 字节）' % (len(h) - n0))
