# -*- coding: utf-8 -*-
"""第 63 轮：把 `base.html` 里那句**过时且说反**的 my-set 警告改成如实说明。

背景（证据都在工程内）：
  · 原文：`⚠ 实测：本机 OM-3 的 my-set 接口全部返回 520/1001（相机不开放这条通道），「读取并备份」在本机型上不会成功。`
  · 事实：`SPEC-round28.md` §187 原文 —— `get_mysetname?mode=current` → HTTP 520，
          括号里写着"**与写入无关**"；`HANDOVER.md` 第 29 轮也把这条列为"属正常，别再当 bug"。
  · 而且写入流程本身**必须先读**整份 my-set（`readMySet()`），所以"读取不会成功"不可能成立。
  · 需求方 2026-09-28：先"记着"，随后决定「改」。

规矩：幂等（重跑不重复改）+ 锚点必须命中恰好 1 次。

用法：python scripts/gen_r63.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')

M63 = '[r63]'
OLD = ('    <div class="camout" style="color:#d8b45a">⚠ 实测：本机 OM-3 的 my-set 接口全部返回 520/1001'
       '（相机不开放这条通道），「读取并备份」在本机型上不会成功。</div>')
NEW = ('    <!-- r63：这段原来写的是「my-set 接口全部不可用、读取并备份不会成功」——第 28 轮那次误判的遗留物；'
       '与实测不符（见 SPEC-round28.md §187「与写入无关」）→ 改成如实说明。'
       '注释里故意不再逐字写出旧文案，免得被当成结论复制回去。 -->\n'
       '    <div class="camout">提示：相机固件不认 <code>get_mysetname?mode=current</code> 这一个查询'
       '（日志里会看到它回 HTTP 520）—— 这只是那一条查询不支持，<b>不影响读取 / 备份 / 写入</b>。</div>')


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if NEW.split('\n')[-1] in html:
        print('%s 已经是目标状态 —— 不重复改。' % M63)
        return 0
    n = html.count(OLD)
    if n != 1:
        print('%s ✗ 锚点命中 %d 次（要求 1 次）—— 页面可能已被改过，先看一眼' % (M63, n))
        return 1
    if '--check' in sys.argv:
        print('%s --check：会替换这句（未写盘）：\n  %s' % (M63, OLD.strip()))
        return 0
    html = html.replace(OLD, NEW, 1)
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(html)
    print('%s ✓ 已把「my-set 接口全部 520/1001 / 读取并备份不会成功」改成如实说明' % M63)
    return 0


if __name__ == '__main__':
    sys.exit(main())
