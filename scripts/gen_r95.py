# -*- coding: utf-8 -*-
"""第 95 轮：**打赏改成"去 GitHub 点个 Star"**（需求方 2026-09-29）

需求方原话：
> 「另外把捐献打赏改成去github点星星可以不，如果没有git账号的人是不是没法star」

答复（已写进弹窗文案）：**Star 必须登录 GitHub 账号**，没账号的人点进去只会看到登录页，
所以 Star 只能算"精神支持"，替代不了扫码打赏；文案里如实补一句「没有 GitHub 账号？把它分享给
同样拍胶片的朋友，一样是支持」。打赏那套机制（收款码内嵌 + `set_donate.py`）**继续留着**，
哪天想恢复，改回 data-tv + 把图填上就行。

## 改动

**Java（`MainActivity.java`）**：WebView 此前**完全没有外链处理**（离线 App 不需要），
而页面是从 `https://om3.local/index.html` 加载的 —— 所以加 `shouldOverrideUrlLoading`：
**只把 http(s) 且 host 不是 `om3.local` 的地址交给系统浏览器**，其余照旧在 App 内加载。

**页面（`app/base.html`）**
1. 顶栏右上角：☕ 打赏 → **⭐ 点 Star**，并**取消隐藏**（`data-tv`: `donate` → `star`，
   这是本轮**唯一**的 data-tv 变化）。
2. `om3Ask` 支持 `cancelText`（原来只能改确定键文字）。弹窗：确定「去 GitHub 点 Star」/ 取消「以后再说」。
3. ⭐ 的点击处理放在 **`</body>` 前的独立 `<script>`**（⚠️ 关键：`om3Ask` 那套在
   `if(!window.__OM3_APP__) return;` 的 **App 专用 IIFE** 里 —— 放进去浏览器里就是死按钮）。
   - App 里：`om3Ask` 弹窗 → `window.om3OpenUrl(url)` → `location.href`
     → 原生 `shouldOverrideUrlLoading` 转系统浏览器（App 不跳走）；
   - 浏览器里：没有 `om3Ask` 就退化成原生 `confirm()` → `window.open(url,'_blank')`。
4. 收款码那行 `OM3_DONATE_IMG` 保留 + 注释说明"现在改成点 Star；想恢复打赏见 set_donate.py"。

## 显式声明
- 涉及：`app/base.html`、`apk/java/com/om3/handbook/MainActivity.java`、`scripts/gen_r95.py`、
  `scripts/dv_r95.py`、`dv_r93/dv_r94`（口径：donate → star）、`SPEC-round95.md` + `HANDOVER.md`
  + `AGENTS.md` + `README.md`（加一行"点个 Star"）。
- 不涉及：配方数据、BLE、相机连接链、导出/导入、打赏机制代码（留着）；**不加权限**
  （`Intent.ACTION_VIEW` 起系统浏览器不需要权限）。
- 集合：**新增 data-tv：`star`**；**删除 data-tv：`donate`**（唯一变化，探针按表断言）；新增 id：无。

用法：python scripts/gen_r95.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
MARK = 'r95：'
GH = 'https://github.com/vick112200/om3-recipes-tool'

STAR_JS = ("<script>\n"
           "/* r95：右上角 ⭐「去 GitHub 点个 Star」。\n"
           "   ⚠️ 必须放在这里 —— **不能**塞进上面那个\"仅 App\"的 IIFE 里（它开头就是\n"
           "   `if(!window.__OM3_APP__) return;`，塞进去的话浏览器里点 ⭐ 毫无反应 = 死按钮）。\n"
           "   App 里：站内弹窗 om3Ask；浏览器里：没有 om3Ask 就用原生 confirm 兜底。 */\n"
           "(function(){\n"
           "  window.om3OpenUrl = function(url){\n"
           "    try{\n"
           "      if(window.__OM3_APP__){\n"
           "        location.href = url;              /* 原生 shouldOverrideUrlLoading → 系统浏览器 */\n"
           "      } else {\n"
           "        var w = window.open(url, '_blank');\n"
           "        if(!w) location.href = url;       /* 弹窗被拦就退化成跳转 */\n"
           "      }\n"
           "      return true;\n"
           "    }catch(e){\n"
           "      try{ if(window.OM3Native && OM3Native.openUrl) OM3Native.openUrl(url); }catch(e2){ }\n"
           "      return false;\n"
           "    }\n"
           "  };\n"
           "  var b = document.querySelector('[data-tv=\"star\"]');\n"
           "  if(!b) return;\n"
           "  var TITLE = '给这个手册点个 Star ⭐';\n"
           "  var BODY = '这个手册是免费做的、也没有广告。如果它帮到了你，去 GitHub 点个 Star 就是最好的支持"
           " —— 也能让更多拍胶片的人搜到它。（没有 GitHub 账号？把它分享给同样拍胶片的朋友，一样是支持。）';\n"
           "  var URL = '" + GH + "';\n"
           "  b.addEventListener('click', function(){\n"
           "    if(window.__om3ask){\n"
           "      window.__om3ask({ title: TITLE, body: BODY, okText: '去 GitHub 点 Star', cancelText: '以后再说' })\n"
           "        .then(function(ok){ if(ok) window.om3OpenUrl(URL); });\n"
           "      return;\n"
           "    }\n"
           "    if(window.confirm(TITLE + '\\n\\n' + BODY)) window.om3OpenUrl(URL);\n"
           "  });\n"
           "})();\n"
           "</script>\n")

J_ANCHOR = """                return null;
            }
"""
J_NEW = J_ANCHOR + """
            /* r95：页面里的外链（去 GitHub 点 Star）交给系统浏览器打开。
               注意：App 自己的页面是从 https://om3.local/ 加载的，必须放行，
               否则点任何链接都会把 App 自己甩到浏览器里。 */
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                try {
                    Uri u = req.getUrl();
                    if (u != null) {
                        String s = u.toString();
                        String host = u.getHost();
                        if ((s.startsWith("http://") || s.startsWith("https://"))
                                && (host == null || !"om3.local".equals(host))) {
                            startActivity(new Intent(Intent.ACTION_VIEW, u));
                            return true;      /* 已交给系统浏览器，App 内不跳转 */
                        }
                    }
                } catch (Throwable t) { }
                return false;                 /* om3.local / file:// 等：照旧在 App 内加载 */
            }
"""


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    java = io.open(JAVA, encoding='utf-8').read()
    if MARK in html:
        print('[r95] 已经是目标状态 —— 不重复改。')
        return 0
    steps = []
    try:
        # ---------- Java ----------
        if 'shouldOverrideUrlLoading' in java:
            raise AssertionError('Java 里已经有 shouldOverrideUrlLoading 了')
        if java.count(J_ANCHOR) != 1:
            raise AssertionError('Java 里 shouldInterceptRequest 的收尾没找到（%d 处）' % java.count(J_ANCHOR))
        java = java.replace(J_ANCHOR, J_NEW, 1)
        steps.append('Java：shouldOverrideUrlLoading（外链→系统浏览器；om3.local 放行）')

        # ---------- 按钮 ☕ → ⭐（并取消隐藏）----------
        b_old = ('    <button type="button" class="donbtn" data-tv="donate" style="display:none" '
                 'title="请我喝杯咖啡" aria-label="打赏">☕</button>')
        if html.count(b_old) != 1:
            raise AssertionError('打赏按钮那一行没找到（%d 处）' % html.count(b_old))
        html = html.replace(b_old, '    <button type="button" class="donbtn" data-tv="star" '
                                   'title="喜欢就点个 Star" aria-label="去 GitHub 点 Star">⭐</button>', 1)
        steps.append('页面：顶栏按钮 → ⭐（data-tv: donate → star，且不再隐藏）')

        # 注释里的旧说法
        for a, b in (('所以按钮就一个 data-tv="donate"。 -->', '所以按钮就一个 data-tv="star"。 -->'),
                     ('<!-- r93：右上角打赏按钮（需求方 2026-09-29）—— 展示收款码，请作者喝杯咖啡。',
                      '<!-- r93/r94：这里原来是打赏按钮（展示收款码），第 95 轮改成「点 Star」。'),
                     ('<!-- r94：**先隐藏**（需求方 2026-09-29「不用嵌二维码，这个功能先隐藏，后面再做」）。',
                      '<!-- r94：上一轮把它隐藏过（现在又拿出来了，但换成点 Star）。'),
                     ('         想开：① 去掉下面那个 style="display:none"；② python scripts/set_donate.py 收款码.png；③ 出包。 -->',
                      '         想恢复打赏：把 data-tv 改回 donate + python scripts/set_donate.py 收款码.png。 -->')):
            if html.count(a) == 1:
                html = html.replace(a, b, 1)

        # ---------- om3Ask 支持 cancelText ----------
        k_anchor = "      ok.textContent = opt.okText || '确定';"
        if html.count(k_anchor) != 1:
            raise AssertionError('om3Ask 里 ok.textContent 那行没找到')
        html = html.replace(k_anchor, k_anchor +
                            "\n      if(cancel) cancel.textContent = opt.cancelText || '取消';   /* r95 */", 1)
        steps.append('页面：om3Ask 支持 cancelText')

        # ---------- 删掉 App-only IIFE 里的 r93 处理，改放 </body> 前的独立脚本 ----------
        h_start = html.index("  /* r93：右上角 ☕ 打赏 —— 展示收款码（内嵌图，不联网） */")
        h_end = html.index("  })();", h_start) + len("  })();")
        html = html[:h_start] + "  /* r95：⭐ 的点击处理挪到页面末尾那个独立脚本里了（浏览器里也能用） */" + html[h_end:]
        if html.count('</body>') != 1:
            raise AssertionError('</body> 不是一处')
        html = html.replace('</body>', STAR_JS + '</body>', 1)
        steps.append('页面：⭐ 处理放进独立脚本（App 用 om3Ask，浏览器用 confirm 兜底）')

        # ---------- 收款码那行的注释 ----------
        d_old = ('/* r93：打赏收款码（微信/支付宝收款码的 data URI）—— 空着时弹窗会如实说"还没放进来"。\n'
                 '   填图：python scripts/set_donate.py 收款码.png （幂等；会写回这一行） */')
        if html.count(d_old) != 1:
            raise AssertionError('OM3_DONATE_IMG 的注释没找到')
        html = html.replace(d_old, '/* r93 的打赏收款码：r95 起右上角改成"去 GitHub 点 Star"，这一行暂时没用上。\n'
                                  '   想恢复打赏：python scripts/set_donate.py 收款码.png （幂等；会写回这一行） */', 1)

        # ---------- 自检 ----------
        checks = [
            ('data-tv="star"' in html and 'data-tv="donate"' not in html, 'data-tv 没换成 star'),
            (html.count('class="donbtn" data-tv="star"') == 1, 'star 按钮不是一处'),
            (html.count('window.om3OpenUrl = function') == 1, 'om3OpenUrl 不是一处'),
            (html.count("querySelector('[data-tv=\"star\"]')") == 1, '⭐ 的点击处理不是一处'),
            (GH in html, 'GitHub 地址没写上'),
            ('window.confirm(TITLE' in html, '浏览器兜底（confirm）没写上'),
            ('if(cancel) cancel.textContent = opt.cancelText' in html, 'cancelText 没支持'),
            (java.count('shouldOverrideUrlLoading') == 1, 'Java 里 shouldOverrideUrlLoading 不是 1 处'),
            ('"om3.local".equals(host)' in java, 'Java 没放行 om3.local（会把 App 自己甩出去）'),
        ]
        bad = [m for ok, m in checks if not ok]
        if bad:
            raise AssertionError('；'.join(bad))
    except (AssertionError, ValueError) as e:
        print('[r95] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r95] --check 通过（未写盘）：')
        for s in steps:
            print('   · ' + s)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(html)
    io.open(JAVA, 'w', encoding='utf-8', newline='').write(java)
    print('[r95] ✓ %d 步：' % len(steps))
    for s in steps:
        print('   · ' + s)
    return 0


if __name__ == '__main__':
    sys.exit(main())
