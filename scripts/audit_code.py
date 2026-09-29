# -*- coding: utf-8 -*-
"""全文件静态分析：找 bug 与不优雅之处"""
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
h = open(P, encoding='utf-8').read()

# 只分析 camera 模块那段脚本（app 主体逻辑）
i = h.find('/* ================= 导入相机（相机 Wi-Fi 直连） ================= */')
s = h.rfind('<script>', 0, i) + len('<script>')
e = h.find('</script>', s)
js = h[s:e]
print('主脚本长度: %.0f KB  总文件: %.0f KB' % (len(js) / 1024, len(h) / 1024))
print()

# 1) 重复定义（同名函数定义多次 = 后者覆盖前者，典型的补丁后遗症）
defs = re.findall(r'\n\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(', js)
dup_defs = [k for k, v in Counter(defs).items() if v > 1]
print('1) 重复定义的函数:', dup_defs if dup_defs else '无 ✓')

# 2) 定义了但从没被调用（死代码/漏接）
called = set(re.findall(r'([A-Za-z_$][\w$]*)\s*\(', js))
never = [d for d in set(defs) if d not in called and not d.startswith('__')]
print('2) 定义了但没人调用:', never if never else '无 ✓')

# 3) 空 catch（静默失败 —— 这是你最讨厌的失败模式）
empty_catch = len(re.findall(r'catch\s*\([^)]*\)\s*\{\s*\}', js))
swallow = len(re.findall(r'catch\s*\([^)]*\)\s*\{\s*(?:try\{[^}]*\}catch[^}]*\})?\s*\}', js))
print('3) 空 catch（完全吞掉错误）:', empty_catch, '个；带内层 try 的:', swallow, '个')

# 4) 重复绑定同一元素（多次 addEventListener → 一次点击跑多次，正是"切换不动/开关打架"的根源）
binds = Counter(re.findall(r"getElementById\('([^']+)'\)\.addEventListener", js))
multi = {k: v for k, v in binds.items() if v > 1}
print('4) 同一 id 被绑定多次:', multi if multi else '无 ✓')

# 5) document 级监听数量（全局委托越多越容易互相干扰）
docl = len(re.findall(r'document\.addEventListener', js))
winl = len(re.findall(r'window\.addEventListener', js))
print('5) document 级监听:', docl, '个；window 级:', winl, '个')

# 6) 定时器（重复/未清理）
iv = re.findall(r'setInterval\([^;]{0,60}', js)
print('6) setInterval 数量:', len(iv))
for x in iv:
    print('     ', x.strip()[:64])

# 7) 无保护的 DOM 直取（潜在 null 崩溃）
unguarded = re.findall(r"(?<!if\()(?<!\|\|\{\})getElementById\('([^']+)'\)\.\w+", js)
print('7) 直接取属性且无 null 保护的 id:', sorted(set(unguarded))[:14])

# 8) CSS：同一类出现多次 display 声明（.hide 冲突高发区）
rules = defaultdict(list)
for m in re.finditer(r'([^{}]+)\{([^}]*)\}', h[:i]):
    sel = m.group(1).strip().split(',')[0].strip()
    if 'display' in m.group(2):
        mm = re.search(r'display:\s*([^;!}]+)', m.group(2))
        if mm:                                  # 注释里带 display 时正则可能不匹配，别让自检脚本自己崩
            rules[sel].append(mm.group(1).strip())
conf = {k: v for k, v in rules.items() if len(set(v)) > 1}
print('8) 同一选择器出现多种 display:', list(conf.items())[:10])

# 9) 重复实现的同类逻辑（不优雅）
pairs = [('导入文件', 'mpImportAny'), ('导入文件(旧)', 'om3PickFile'), ('导入文件(更旧)', 'mpImportFile'),
         ('写入配方', 'writeRecipe'), ('写入(新)', 'writeSlotRecipe'), ('写入(通用)', 'writeRawKV'),
         ('写入(单槽)', 'mpWriteOne'), ('写入(档位)', 'om3WriteViaSlot'),
         ('预览', 'previewSlot'), ('预览入口', 'om3doPreview')]
print('9) 同功能函数并存（重复实现）:')
for name, fn in pairs:
    print('   %-14s %s(%s)' % (name, fn, '存在' if fn in js else '—'))

# 10) 可疑残留
print('10) 残留检查:')
for k, pat in [('注释掉的代码块', r'/\*\s*(?:TODO|FIXME|暂时|临时)'), ('TODO/FIXME', r'\b(TODO|FIXME|XXX)\b'),
               ('调试用 console.log', r'console\.log'), ('废弃弹窗 impMask', r'impMask'),
               ('旧任务条 om3banner', r'om3banner'), ('旧 foldbar', r'foldbar')]:
    print('   %-18s %d 处' % (k, len(re.findall(pat, h))))
