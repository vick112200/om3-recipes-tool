# -*- coding: utf-8 -*-
"""第 93 轮：**改名 om3 recipes tool** + **右上角打赏按钮（展示收款码）**（需求方 2026-09-29）

需求方原话：
> 「名字改一下，改成 om3 recipes tool。然后我想在右上角增加个按钮，一个打赏图标，
>   功能是展示我的收款码，然后可以选择捐献请我喝咖啡什么的，怎么做」

## 一、改名（om3 recipes tool）
- 页面：`<title>`、顶栏 `.tbname`、首页 `<h1>`、导出文件头、导出包 `app` 字段（共 5 处）
- Android 启动器名：`apk/res/values/strings.xml` 的 `app_name`
- 桌面产物名：`om3 recipes tool.apk`（发布/文档同步改）

## 二、打赏按钮（右上角 ☕ + 展示收款码）
- **按钮**：顶栏最右（`.tb` 里 tabs 之后）加一个 ☕，选择器用 **`data-tv="donate"`**（第 68 轮起的规矩：
  新控件一律 data-tv；**本轮唯一新增的 data-tv 就是它**，`id` 一个都不加）。
- **弹窗**：复用站内自绘弹窗 `om3Ask`（`#omask/#otitle/#obody/#ofields/#ook/#ocancel` 都是**已有 id**）：
  给 `om3Ask` 加两个能力 —— `opt.img`（在图里显示收款码 data URI）与 `opt.onlyOk`（只有一个"谢谢"按钮）。
- **收款码图片**：离线单文件 App，所以**内嵌 base64**（和手册里 3.8 MB 的样片同一个做法）：
  ```js
  var OM3_DONATE_IMG = '';   /* r93：打赏收款码（data:image/png;base64,…）—— 用 scripts/set_donate.py 填 */
  ```
  填图：`python scripts/set_donate.py 你的收款码.png`（幂等，会顺手校验大小）；没填时弹窗会如实说"收款码还没放进来"。

## 显式声明
- 涉及：`app/base.html`、`apk/res/values/strings.xml`、`scripts/gen_r93.py`、`scripts/set_donate.py`、
  `scripts/dv_r93.py`、本文档 + `HANDOVER.md` + `AGENTS.md` + `README.md`（产物名）+ `TEST-camera.md`。
- 不涉及：**Java 不改**；相机连接链、BLE、配方数据都不动；**新增 id：无**；
  **新增 data-tv：恰好 1 个 —— `donate`**（探针断言"新集合 == 老集合 ∪ {donate}"）。
- 收款码是**放在 APK 里**的（任何人解包都能看到）—— 这是需求方自己的收款码，属预期行为；不联网、不上传。

用法：python scripts/gen_r93.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
STRINGS = os.path.join(ROOT, 'apk', 'res', 'values', 'strings.xml')
MARK = 'r93：'
NEWNAME = 'om3 recipes tool'


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    strs = io.open(STRINGS, encoding='utf-8').read()
    if MARK in html:
        print('[r93] 已经是目标状态 —— 不重复改。')
        return 0
    changed = []
    try:
        # ---------- 1) 改名 ----------
        n = html.count('OM-3 色彩配方手册')
        if n < 5:
            raise AssertionError('页面里"OM-3 色彩配方手册"只有 %d 处（预期 ≥5）' % n)
        html = html.replace('OM-3 色彩配方手册', NEWNAME)
        changed.append('改名：页面 %d 处 → %s' % (n, NEWNAME))
        old_lab = '<string name="app_name">OM-3 色彩配方</string>'
        if strs.count(old_lab) != 1:
            raise AssertionError('strings.xml 里的 app_name 没找到')
        strs = strs.replace(old_lab, '<string name="app_name">%s</string>' % NEWNAME, 1)
        changed.append('改名：Android 启动器名 → %s' % NEWNAME)

        # ---------- 2) 顶栏打赏按钮 ----------
        anchor = """      <button type="button" data-p="T" id="tabTest" style="display:none">测试页</button>
    </span>"""
        if html.count(anchor) != 1:
            raise AssertionError('顶栏 tabs 的收尾没找到')
        html = html.replace(anchor, anchor + """
    <!-- r93：右上角打赏按钮（需求方 2026-09-29）—— 展示收款码，请作者喝杯咖啡。
         规矩：新控件只用 data-tv（不加 id），所以按钮就一个 data-tv="donate"。 -->
    <button type="button" class="donbtn" data-tv="donate" title="请我喝杯咖啡" aria-label="打赏">☕</button>""", 1)
        changed.append('顶栏加 ☕ 打赏按钮（data-tv="donate"）')

        # ---------- 3) 按钮样式 ----------
        css_anchor = '.tbname{font-size:13px;color:#8d8d8d;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}'
        if html.count(css_anchor) != 1:
            raise AssertionError('.tbname 的样式行没找到')
        html = html.replace(css_anchor, css_anchor + """
/* r93：右上角打赏按钮（收款码入口） */
.donbtn{flex:none;background:#232323;border:1px solid #3a3a3a;color:#e8c07a;border-radius:9px;
  padding:4px 9px;font-size:15px;line-height:1.25;cursor:pointer}
.donbtn:active{background:#2c3a34}
.om3qr{display:block;margin:8px auto 4px;width:232px;max-width:76vw;background:#fff;border-radius:10px;padding:7px}
.om3cap{font-size:12px;color:#9aa3b2;text-align:center;margin:0 0 4px}""", 1)
        changed.append('加 .donbtn / .om3qr 样式')

        # ---------- 4) om3Ask：支持图片 + 只有一个按钮 ----------
        old_body = "      $('obody').textContent = opt.body || '';"
        if html.count(old_body) != 1:
            raise AssertionError("om3Ask 里 obody 那行没找到")
        html = html.replace(old_body, old_body + """
      /* r93：打赏弹窗要显示收款码图片 → 支持 opt.img（data URI）；onlyOk = 只留"谢谢"一个按钮 */
      if(opt.onlyOk && $('ocancel')){ try{ $('ocancel').style.display = 'none'; }catch(e0){ } }""", 1)
        old_box = """      var box = $('ofields');
      box.innerHTML = '';"""
        if html.count(old_box) != 1:
            raise AssertionError('om3Ask 的 ofields 那两行没找到')
        html = html.replace(old_box, old_box + """
      if(opt.img){
        var _im = document.createElement('img');
        _im.className = 'om3qr'; _im.src = opt.img; _im.alt = opt.alt || '收款码';
        box.appendChild(_im);
      }
      if(opt.imgCaption){
        var _cp = document.createElement('div');
        _cp.className = 'om3cap'; _cp.textContent = opt.imgCaption;
        box.appendChild(_cp);
      }""", 1)
        changed.append('om3Ask 支持 opt.img / opt.onlyOk（复用已有 id，没加新 id）')

        # ---------- 5) 收款码常量 + 点击处理 ----------
        const_anchor = 'var OM3_BLE_NOTIFY = '
        if html.count(const_anchor) != 1:
            raise AssertionError('OM3_BLE_NOTIFY 常量没找到（用来定位插入点）')
        html = html.replace(const_anchor, """/* r93：打赏收款码（微信/支付宝收款码的 data URI）—— 空着时弹窗会如实说"还没放进来"。
   填图：python scripts/set_donate.py 收款码.png （幂等；会写回这一行） */
var OM3_DONATE_IMG = '';   /* r93:donate */
""" + const_anchor, 1)
        handler_anchor = "  window.__om3ask = om3Ask;"
        if html.count(handler_anchor) != 1:
            raise AssertionError('window.__om3ask 那行没找到')
        html = html.replace(handler_anchor, handler_anchor + """

  /* r93：右上角 ☕ 打赏 —— 展示收款码（内嵌图，不联网） */
  (function(){
    var b = document.querySelector('[data-tv="donate"]');
    if(!b || !window.__om3ask) return;
    b.addEventListener('click', function(){
      var img = '';
      try{ img = String(OM3_DONATE_IMG || ''); }catch(e){ img = ''; }
      var has = img.indexOf('data:image') === 0;
      window.__om3ask({
        title: '请我喝杯咖啡 ☕',
        onlyOk: true,
        okText: '谢谢',
        body: has
          ? '这个手册是免费做的、也没广告。如果它帮到了你，可以扫下面的码请我喝杯咖啡 —— 谢谢！'
          : '这个手册是免费做的、也没广告。如果它帮到了你，我谢谢你这份心意 —— 收款码还没放进来。',
        img: has ? img : '',
        imgCaption: has ? '微信 / 支付宝 扫码即可' : '',
      });
    });
  })();""", 1)
        changed.append('☕ 点击 → om3Ask 展示收款码（没图时如实说）')

        # ---------- 6) 自检 ----------
        if html.count('class="donbtn" data-tv="donate"') != 1:
            raise AssertionError('donate 按钮标签不是 1 处')          # JS 里还有一处选择器，属正常
        if "document.querySelector('[data-tv=\"donate\"]')" not in html:
            raise AssertionError('donate 的点击处理没接上')
        if html.count('var OM3_DONATE_IMG') != 1:
            raise AssertionError('OM3_DONATE_IMG 不是 1 处')
        if 'OM-3 色彩配方手册' in html or 'OM-3 色彩配方手册' in strs:
            raise AssertionError('还有旧名字')
        if '<title>%s</title>' % NEWNAME not in html:
            raise AssertionError('title 没改成新名字')
    except AssertionError as e:
        print('[r93] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r93] --check 通过（未写盘）：')
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(html)
    io.open(STRINGS, 'w', encoding='utf-8', newline='').write(strs)
    print('[r93] ✓ %d 步：' % len(changed))
    for c in changed:
        print('   · ' + c)
    return 0


if __name__ == '__main__':
    sys.exit(main())
