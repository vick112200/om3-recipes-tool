# -*- coding: utf-8 -*-
"""第 90 轮：**把"蓝牙口令"这条最后的路铺到手指能点到的地方**（相机显示蓝牙已连接之后）

需求方 2026-09-29：**「相机显示蓝牙已连接」** —— 说明 ① 那条链相机认（相机侧也认为连上了）。
剩下唯一的已知变量是**口令认证**：官方 `BlePowOnActivity.x2()` 连蓝牙时就带 `str.blePass`，
`oishare/e$d.run` 在 `e$e`（電源ON）**之前**先发 `0x0C02` 口令认证；而我们日志一直是"蓝牙口令：没存"。

以前只有「蓝牙工具」页里那个 `blePassIn` 输入框能填口令 —— 用户在「连接相机」页点时摸不到。
本轮把口令铺到控制台上：

1. 控制台加一个按钮 **`data-tv="cv-pass"`：① 填蓝牙口令（相机屏幕上那串）**（**本轮唯一新增的 data-tv**）；
2. 点它 → 用我们自绘的 `om3Ask` 弹窗填（不用安卓原生 prompt）→ 记住（`localStorage: om3blepass`，和"蓝牙工具"页同一处）
   → **立刻按官方顺序重发**：`[口令认证 0x0C02] → 電源ON 0x0F01 → リモコンモード 0x1D01{0x02}`；
3. `0x1D01` 被拒（结果码 ≠0）时，提示语直接指向这个按钮；
4. 暴露 `window.__om3cvPassSet(v)`（探针用：验"有口令时第一条帧就是口令认证"）。

## 显式声明

- 涉及：`app/base.html`、`scripts/gen_r90.py`、`scripts/dv_r90.py`、本文档 + `HANDOVER.md` + `AGENTS.md` + `OPEN-ITEMS.md`（`OI-19` 入口补这个按钮）+ `TEST-camera.md`。
- 不涉及：**Java 不改**；订阅三连/应答解码/`0x1D01` 序列都不动；不加权限。
- **新增 data-tv：恰好 1 个 —— `cv-pass`**（探针断言"新集合 == 老集合 ∪ {cv-pass}"，多一个少一个都红）；**新增 id：无**。

用法：python scripts/gen_r90.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r90：'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


@step('P1 控制台加「填蓝牙口令」按钮（本轮唯一新增 data-tv）')
def p1_btn(html):
    old = """      <button type="button" class="bigsm" data-tv="cv-notseen">相机没反应（屏幕没变）</button>
    </div>"""
    new = """      <button type="button" class="bigsm" data-tv="cv-notseen">相机没反应（屏幕没变）</button>
    </div>
    <!-- STEPS_MARK：官方在发 電源ON 之前**先做口令认证**（`e$d.run` → `0x0C02`）；
         官方连蓝牙时也是带着 `str.blePass` 连的（`BlePowOnActivity.x2`）。
         以前只有「蓝牙工具」页那个输入框能填口令 —— 这里做一个能一眼看见、一按就进去的入口。 -->
    <div class="cvbtns" style="margin:2px 0 2px">
      <button type="button" class="bigsm" data-tv="cv-pass">① 填蓝牙口令（相机屏幕那串）</button>
    </div>"""
    assert html.count(old) == 1, '回答键那一行没找到'
    return html.replace(old, new, 1)


@step('P2 口令：自绘弹窗 → 记住 → 立刻按官方顺序重发')
def p2_handler(html):
    old = """    cvBind('cv-wake', function(){ camCvWake(); });"""
    new = """    cvBind('cv-wake', function(){ camCvWake(); });
    /* STEPS_MARK：口令（相机屏幕 MENU → Wi-Fi/蓝牙 → 连接到智能手机 上那串「パスコード」） */
    window.__om3cvPassSet = function(v){
      v = String(v || '').trim();
      if(!v){ camCvSay('没填口令 —— 口令就在相机屏幕上（MENU → Wi-Fi/蓝牙 → 连接到智能手机）', 'warn'); return; }
      try{ blePassSet(v); }catch(e){ om3err(e, "cv-pass-set"); }
      camCvSay('已记住蓝牙口令（' + v.length + ' 位）→ 现在按官方顺序重发：口令认证 → 電源ON → リモコンモード', 'ok');
      try{ if(window.__om3cvOnFrame) { /* 计时钩子留着 */ } }catch(e0){}
      camCvWake();
    };
    cvBind('cv-pass', function(){
      var cur = '';
      try{ cur = blePassGet(); }catch(e){ cur = ''; }
      if(!window.__om3ask){
        camCvSay('这个版本的弹窗不能用 → 到「蓝牙工具」页里那个「相机蓝牙口令」框里填', 'warn'); return;
      }
      camCvSay('填口令：相机屏幕 MENU → Wi-Fi/蓝牙 → 连接到智能手机 上显示的那串（填一次就记住）');
      window.__om3ask({
        title: '相机蓝牙口令',
        body: '相机屏幕：MENU → Wi-Fi/蓝牙 → 连接到智能手机，屏幕上那串「パスコード」（4 位数字）。\\n'
            + '官方在发「電源ON」之前**先做口令认证**；没有口令时相机会拒绝后面的命令。\\n'
            + '填一次就记住（也可以扫相机二维码自动填）。',
        fields: [ { label: '蓝牙口令', value: cur } ],
        okText: '记住并重发'
      }).then(function(v){ window.__om3cvPassSet(v); });
    });"""
    assert html.count(old) == 1, 'cvBind(cv-wake) 那段没找到'
    return html.replace(old, new, 1)


@step('P3 0x1D01 被拒时，提示语指向这个按钮')
def p3_hint(html):
    old = """            + (_okCode ? ' → 相机应该开始进 Wi-Fi 传输态了' : ' → 需要的是口令认证（相机屏幕「蓝牙配对」那串，或扫二维码自动填）'),"""
    new = """            + (_okCode ? ' → 相机应该开始进 Wi-Fi 传输态了'
                       : ' → 需要的是口令认证：点控制台上「① 填蓝牙口令（相机屏幕那串）」（或扫相机二维码自动填）'),"""
    assert html.count(old) == 1, '0x1D01 判定那句话没找到'
    return html.replace(old, new, 1)


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r90] 已经是目标状态 —— 不重复改。')
        return 0
    changed = []
    cur = html
    try:
        for label, fn in STEPS:
            before = cur
            cur = fn(cur)
            if cur == before:
                raise AssertionError('这一步什么都没改：' + label)
            changed.append(label)
    except (AssertionError, ValueError) as e:
        print('[r90] ✗ %s —— **不写盘**' % e)
        return 1
    cur = cur.replace('STEPS_MARK', MARK)
    assert MARK in cur
    if cur.count('data-tv="cv-pass"') != 1:
        print('[r90] ✗ 结构自检：cv-pass 按钮不是 1 处 —— **不写盘**')
        return 1
    if cur.count('window.__om3cvPassSet = function(v){') != 1:
        print('[r90] ✗ 结构自检：__om3cvPassSet 不是 1 处 —— **不写盘**')
        return 1
    dh = len(cur.encode('utf-8')) - len(html.encode('utf-8'))
    if not (0 < dh < 6000):
        print('[r90] ✗ 页面体积不对（%+d 字节）—— **不写盘**' % dh)
        return 1
    if '--check' in sys.argv:
        print('[r90] --check：%d 步都能跑通（未写盘）' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(cur)
    print('[r90] ✓ 页面 %d 步：加「填蓝牙口令」按钮 → 记住 → 按官方顺序重发' % len(changed))
    print('[r90] 页面净增 %d 字节' % dh)
    return 0


if __name__ == '__main__':
    sys.exit(main())
