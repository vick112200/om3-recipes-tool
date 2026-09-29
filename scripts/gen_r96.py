# -*- coding: utf-8 -*-
"""第 96 轮：给「我的方案」加**改名入口**（需求方 2026-09-29）

需求方原话：
> 「我的方案中，已有的方案改不了名字，增加改名字的功能吧」

根因（无头实测，见 SPEC-round96.md §0）：
  · 详情页页脚那个 `id="mpEdit"`（改名 / 描述）**能改名**，但它在页面 **1871px** 处
    （手机视口 800px ⇒ 要往下滚约 1071px 才看得到）；
  · 列表页（我的配方 → 方案）**没有任何改名入口**。
  ⇒ 用户的感受就是"改不了名字"。

本轮只把入口补到看得见的地方（数据格式一个字段都不动）：

  1. **列表页**每条方案上加一个 `[data-mpren]` 按钮 → 直接改名，不用进详情、不用滚动；
     新函数 `mpRenameDialog(idx)`：只动 `name`；空名字拒绝并提示；允许重名但如实提示；
     提交时按 `id` 重新定位（弹窗开着时方案可能被删/被导入替换）。
  2. **详情页**那个「改名 / 描述」`#mpEdit` 从页脚**搬到第一屏**（和「← 返回列表」同一行）——
     **id 不变、弹窗不变**（还是方案名/档位/描述三个字段），老探针口径不受影响。

显式声明（详见 SPEC-round96.md §2）：
  · **新增 id：无**；**新增 data-tv：无**（新按钮用属性选择器 `[data-mpren]`）；
  · Java / 相机连接 / BLE / 导入导出格式**都不动**；不加权限、不联网。

用法：python scripts/gen_r96.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r96：'

# ---------- ① 列表项：末尾追加一行「✎ 改这个方案的名字」 ----------
L_OLD = ("        '<span class=\"' + mountCls(s) + '\" data-mount=\"' + idx + '\" "
         "title=\"点一下改「挂载状态」\">' + esc(mountTxt(s)) + '</span></div>';")

L_NEW = ("        '<span class=\"' + mountCls(s) + '\" data-mount=\"' + idx + '\" "
         "title=\"点一下改「挂载状态」\">' + esc(mountTxt(s)) + '</span></div>' +\n"
         "        /* r96：**列表上就能改名**（需求方 2026-09-29：「已有的方案改不了名字」）。\n"
         "           原来只有详情页**最底下**那个「改名 / 描述」—— 实测它在页面 1871px 处，\n"
         "           手机要往下滚 1000 多像素，列表页又没有任何入口，用起来就是\"改不了\"。\n"
         "           这个按钮自己 stopPropagation，不会顺带把详情页打开。 */\n"
         "        '<div class=\"r\" style=\"margin-top:6px\">' +\n"
         "          '<button type=\"button\" data-mpren=\"' + idx + '\" "
         "style=\"flex:none;padding:6px 13px;font-size:12px\">✎ 改这个方案的名字</button>' +\n"
         "          '<span style=\"flex:1;align-self:center;font-size:11.5px;color:#8d8d8d\">"
         "不用点进详情、也不用往下滚</span>' +\n"
         "        '</div>';")

# ---------- ② 列表项按钮的委托绑定 ----------
B_OLD = ("    /* 徽章点击 = 改状态（stopPropagation：别顺带把详情页打开） */\n"
         "    box.querySelectorAll('.mpmount[data-mount]').forEach(function(b){")

B_NEW = ("    /* r96：列表上那个「✎ 改这个方案的名字」→ 直接开改名弹窗\n"
         "       （stopPropagation：别顺带把详情页打开） */\n"
         "    box.querySelectorAll('.mpitem [data-mpren]').forEach(function(b){\n"
         "      b.addEventListener('click', function(ev){\n"
         "        try{ ev.stopPropagation(); }catch(x){ om3err(x, \"silent\"); }\n"
         "        mpRenameDialog(Number(b.getAttribute('data-mpren')));\n"
         "      });\n"
         "    });\n"
         "    /* 徽章点击 = 改状态（stopPropagation：别顺带把详情页打开） */\n"
         "    box.querySelectorAll('.mpmount[data-mount]').forEach(function(b){")

# ---------- ③ 新函数 mpRenameDialog ----------
F_OLD = "  /* 手动改「挂载状态」（UC-R17-02）：列表徽章和详情页「改状态」都走这里 */"

F_NEW = '''  /* r96：改**已有方案**的名字（需求方 2026-09-29：「已有的方案改不了名字，增加改名字的功能吧」）。
     入口有两处：列表页每条方案上（UC-R96-01）、详情页第一屏的「改名 / 描述」（UC-R96-03）。
     规则：① **只动 name 一个字段** —— id / slots / desc / from / 挂载状态全不动；
           ② 名字 trim 后为空 → **拒绝改名**（绝不把方案名改空），并提示；
           ③ 允许与别的方案重名，但弹窗里如实提示有几个同名；
           ④ 提交时**按 id 重新在库里定位**（弹窗开着时方案可能被删掉或被导入替换）。 */
  function mpRenameDialog(setIdx){
    var arr = setsAll(), s = arr[setIdx];
    if(!s){ log('方案不存在（可能刚被删了）', 'err'); return; }
    var old = String(s.name || '').trim();
    var dup = 0, i;
    if(old) for(i = 0; i < arr.length; i++){
      if(i === setIdx) continue;
      if(String((arr[i] && arr[i].name) || '').trim() === old) dup++;
    }
    om3Ask({
      title: '改名字：' + (old || '未命名方案'),
      body: '只改这一个方案的名字，不影响它 4 个槽位里的配方（槽位名在详情页里逐个改）。'
            + (dup ? ('注意：已经有 ' + dup + ' 个方案叫这个名字，改完还是重名。') : ''),
      fields: [ { label: '方案叫什么', value: s.name || '' } ],
      okText: '改名'
    }).then(function(r){
      if(r === null || r === false) return;                     /* 取消 → 什么都不改 */
      var nm = String(r || '').trim();
      if(!nm){ log('新名字是空的 → 名字没改（方案名不能是空的）', 'warn'); toastMsg('名字不能为空，没改'); return; }
      var a = setsAll(), k = -1;
      for(var z = 0; z < a.length; z++) if(a[z] && a[z].id === s.id){ k = z; break; }   /* 按 id 重新定位 */
      if(k < 0){
        log('方案已经不在了，改名没做', 'err'); toastMsg('方案已经不在了');
        try{ mpRender(); }catch(er){ om3err(er, "silent"); }
        return;
      }
      if(String(a[k].name || '').trim() === nm){ log('名字没变：' + nm); return; }
      a[k].name = nm;
      if(!setsSave(a)) return;
      log('✎ 方案改名：「' + (old || '未命名方案') + '」→「' + nm + '」（只改名字，槽位与挂载状态都没动）', 'ok');
      toastMsg('已改名为：' + nm);
      mpRender();
    });
  }
  window.__om3mpRename = mpRenameDialog;

''' + F_OLD

# ---------- ④ 详情页头部：加「改名 / 描述」（第一屏） ----------
H_OLD = ("    head.innerHTML = '<div class=\"r\" style=\"margin:0 0 8px\">"
         "<button type=\"button\" id=\"mpBack\" class=\"mpbtn\" style=\"flex:none;padding:7px 12px\">"
         "← 返回列表</button></div>' +")

H_NEW = ("      head.innerHTML = '<div class=\"r\" style=\"margin:0 0 8px\">' +\n"
         "        /* r96：「改名 / 描述」原来在详情页**最底下**（实测 1871px 处，手机要滚 1000+ 像素）\n"
         "           → 搬到第一屏，和「← 返回列表」同一行。**id 还是 mpEdit、弹窗还是那三个字段**，\n"
         "           老探针（dv_mpflow 找 #mpEdit、dv_model 数 3 个字段）口径都不变。 */\n"
         "        '<button type=\"button\" id=\"mpBack\" class=\"mpbtn\" style=\"flex:none;padding:7px 12px\">"
         "← 返回列表</button>' +\n"
         "        '<button type=\"button\" id=\"mpEdit\" class=\"mpbtn\" style=\"flex:none;padding:7px 12px\">"
         "✎ 改名 / 描述</button></div>' +")

# ---------- ⑤ 详情页页脚：把改名按钮撤掉（只剩导出 + 删除） ----------
P_OLD = ("      '<button type=\"button\" id=\"mpEdit\">改名 / 描述</button>' +\n")

P_NEW = ("      /* r96：「改名 / 描述」搬到上面第一屏了，这里只剩导出和删除 */\n")


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r96] 已经是目标状态 —— 不重复改。')
        return 0
    steps = []
    try:
        for name, old in (('① 列表项', L_OLD), ('② 委托绑定', B_OLD), ('③ 改名函数锚点', F_OLD),
                          ('④ 详情页头部', H_OLD), ('⑤ 详情页页脚', P_OLD)):
            n = html.count(old)
            if n != 1:
                raise AssertionError('%s 的锚点不是 1 处（%d 处）' % (name, n))
        html = html.replace(L_OLD, L_NEW, 1)
        steps.append('列表项：加「✎ 改这个方案的名字」按钮（[data-mpren]）')
        html = html.replace(B_OLD, B_NEW, 1)
        steps.append('列表项：按钮委托（stopPropagation → mpRenameDialog）')
        html = html.replace(F_OLD, F_NEW, 1)
        steps.append('新函数 mpRenameDialog（空名拒绝 / 重名提示 / 按 id 兜底 / 只动 name）')
        html = html.replace(H_OLD, H_NEW, 1)
        steps.append('详情页：head 第一行加 #mpEdit「✎ 改名 / 描述」')
        html = html.replace(P_OLD, P_NEW, 1)
        steps.append('详情页：页脚撤掉旧的 #mpEdit')

        checks = [
            ('data-mpren' in html, '列表按钮没写上'),
            (html.count('data-mpren') == 3, 'data-mpren 出现次数应为 3（渲染 1 + 委托 1 + 注释 1），实际 %d' % html.count('data-mpren')),
            (html.count("box.querySelectorAll('.mpitem [data-mpren]')") == 1, '列表按钮的委托不是 1 处'),
            (html.count('function mpRenameDialog(setIdx){') == 1, 'mpRenameDialog 不是 1 处'),
            (html.count('window.__om3mpRename = mpRenameDialog;') == 1, 'mpRenameDialog 没导出'),
            (html.count('mpRenameDialog(Number(b.getAttribute') == 1, '改名按钮没接到 mpRenameDialog'),
            (html.count('id="mpEdit"') == 1, 'id="mpEdit" 不是 1 处（旧的那处没撤干净？）'),
            ("'<button type=\"button\" id=\"mpEdit\" class=\"mpbtn\"" in html, '第一屏的 #mpEdit 没写成 mpbtn 样式'),
            ("'<button type=\"button\" id=\"mpEdit\">改名 / 描述</button>'" not in html, '页脚那个旧的 #mpEdit 还在'),
            (html.count('id="mpBack"') == 1, 'id="mpBack" 不是 1 处'),
            (html.count('id="mpExp"') == 1, 'id="mpExp" 不是 1 处'),
            (html.count('id="mpDel"') == 1, 'id="mpDel" 不是 1 处'),
            (html.count('id="mpNewSet"') == 1, 'id="mpNewSet" 不是 1 处'),
            ('✎ 改这个方案的名字' in html, '列表按钮文案没写上'),
            ('✎ 改名 / 描述' in html, '详情页按钮文案没写上'),
            ('名字不能为空，没改' in html, '空名字兜底没写上'),
            ('已经有 \' + dup + \' 个方案叫这个名字' in html, '重名提示没写上'),
        ]
        bad = [m for ok, m in checks if not ok]
        if bad:
            raise AssertionError('；'.join(bad))
    except (AssertionError, ValueError) as e:
        print('[r96] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r96] --check 通过（未写盘）：')
        for s in steps:
            print('   · ' + s)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(html)
    print('[r96] ✓ %d 步：' % len(steps))
    for s in steps:
        print('   · ' + s)
    return 0


if __name__ == '__main__':
    sys.exit(main())
