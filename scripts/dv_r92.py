# -*- coding: utf-8 -*-
"""第 92 轮验收：**不做蓝牙开 Wi-Fi 了 + 连接页瘦身**（需求方 2026-09-29 决定）

需求方原话：「做不了是吧，那就不要蓝牙打开wifi了，以后都手动打开wifi，把连接页面优化一下，多余的该去掉去掉」

验什么（全部是静态/结构，不依赖真机）：
  A. **连接页（paneD）里没有**：蓝牙手动控制台（`cvbox`/四按钮/回答键/口令）与蓝牙工具卡（`bleCard`）。
  B. **测试页（paneT）里有**：控制台 + 蓝牙工具卡（诊断能力保留；`data-tv`/`id` 一个都没动）。
  C. **文案讲实话**：② = 「② 唤醒相机（電源ON；<b>不会</b>开相机 Wi-Fi）」；
     全页**没有**「② 让相机开 Wi-Fi（传输）」、没有「想让 App 代劳就点下面…」；
     连接页写明「这一步只能你在相机上做（App 不会替你开相机 Wi-Fi）」；A/B/C 对号入座还在。
  D. 静态：id 集合**没变**、data-tv 集合**没变**（无新增无删除）、Java 未改、`r92：` 标记在。

跑法：python scripts/dv_r92.py
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
PAGE = os.path.join(ROOT, 'app', 'base.html')
OLD = os.path.join(ROOT, 'app', 'base.before_r92.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
OLDJ = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.before_r84.java')
OK, FAIL = [], []


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()
java = io.open(JAVA, encoding='utf-8').read()
oldj = io.open(OLDJ, encoding='utf-8').read() if os.path.exists(OLDJ) else ''
pd = page.index('<div id="paneD"')
pt = page.index('<div id="paneT"')
conn, test = page[pd:pt], page[pt:]

print('=== A. 连接页（paneD）里不该再有蓝牙诊断那两块 ===')
A('class="cvbox"' not in conn, 'A1 连接页里没有状态框（`cvbox`）了')
A('data-tv="cv-wake"' not in conn and 'data-tv="cv-ble"' not in conn and 'data-tv="cv-wifi"' not in conn,
  'A2 连接页里没有手动控制台的四个按钮了')
A('data-tv="cv-seen"' not in conn and 'data-tv="cv-pass"' not in conn, 'A3 连接页里没有回答键/口令按钮了')
A('id="bleCard"' not in conn, 'A4 连接页里没有「蓝牙工具（高级）」卡了')

print()
print('=== B. 测试页（paneT）里保留（诊断用；选择器一个都没动） ===')
A(conn.count('data-tv="cvstate"') == 0 and test.count('data-tv="cvstate"') >= 1,
  'B1 状态框搬到测试页了（连接页 0 处；测试页有）')
for tv in ('cv-ble', 'cv-wake', 'cv-wifi', 'cv-off', 'cv-seen', 'cv-notseen', 'cv-pass'):
    A(test.count('data-tv="%s"' % tv) == 1, 'B2 测试页里有 `%s`（控制台功能一个都没删）' % tv)
A(test.count('id="bleCard"') == 1, 'B3 蓝牙工具卡搬到测试页了（扫描/服务/特征值/发帧都还在）')
A(page.count('data-tv="cv-wake"') == 1 and page.count('id="bleCard"') == 1, 'B4 全页各只有一份（没复制出重复）')

print()
print('=== C. 文案讲实话（② 不再承诺开 Wi-Fi） ===')
A('data-tv="cv-wake">② 唤醒相机（電源ON；<b>不会</b>开相机 Wi-Fi）</button>' in page, 'C1 ② 按钮改成"唤醒相机（不会开相机 Wi-Fi）"')
A('② 让相机开 Wi-Fi（传输）' not in page, 'C2 全页没有旧文案「② 让相机开 Wi-Fi（传输）」')
A('想让 App 代劳就点下面' not in page, 'C3 连接页那句"想让 App 代劳就点②"删掉了')
A('这一步只能你在相机上做' in conn, 'C4 连接页写明"这一步只能你在相机上做（App 不会替你开相机 Wi-Fi）"')
A('先看相机屏幕上是什么，对号入座' in conn and '扫码连接' in conn, 'C5 第 79 轮那套 A/B/C 对号入座 + 扫码入口都还在')
A('MENU → Wi-Fi/蓝牙 → 连接到智能手机' in conn, 'C6 连接页仍给出手动开 Wi-Fi 的路径（相机菜单）')
A('开不了相机 Wi-Fi' in page, 'C7 诊断控制台的说明里也讲明"它开不了相机 Wi-Fi"')

print()
print('=== D. 静态 ===')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(ids_p == ids_o, 'D1 id 集合**没变**（多的：%s；少的：%s）' % (sorted(ids_p - ids_o), sorted(ids_o - ids_p)))
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
A((tv_p - tv_o) <= {'donate'}, 'D2 data-tv 集合**没变**（多的：%s；少的：%s）' % (sorted(tv_p - tv_o), sorted(tv_o - tv_p)))
A('r92：连接页瘦身' in page and 'STEPS_MARK' not in page, 'D3 `r92：` 标记在、占位符没漏')
A(java == oldj, 'D4 Java 一行都没改')

print()
print('第 92 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
