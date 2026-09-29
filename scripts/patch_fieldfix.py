# -*- coding: utf-8 -*-
"""【关键修复】推演时发现的真 bug：
slotKV 用了错误的配方字段名（rec.yellow/rec.highlights/...），而 app 里配方的真实字段是
rec.v[0..11]（12 色轮）/ rec.hi（高光）/ rec.mid（中间调）/ rec.sh（阴影）/ rec.eff（阴影补偿）
/ rec.shp（锐度）/ rec.con（对比）—— 用错字段会让 12 个色轮全部写成 0，
等于"把 C1 槽1 清空"而不是写入配方。必须修掉。
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()

OLD = """    var c = [rec.yellow, rec.orange, rec.orangeRed, rec.red, rec.magenta, rec.violet,
             rec.blue, rec.blueCyan, rec.cyan, rec.greenCyan, rec.green, rec.yellowGreen];
    var kv = {}, i;
    for(i = 0; i < 12; i++) kv['MODE_COLOR_CREATOR_2_VIVID_SET' + N + '_' + (i + 1)] = om3step(c[i]);
    kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET' + N]   = om3step(rec.highlights);
    kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_MIDDLE_SET' + N] = om3step(rec.midtones);
    kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_LOW_SET' + N]    = om3step(rec.shadows);
    kv['MODE_COLOR_CREATOR_2_SHADING_SET' + N]   = om3step(rec.shadingEffect);
    kv['MODE_COLOR_CREATOR_2_SHARP_SET' + N]     = om3sharp(rec.sharpness);
    kv['MODE_COLOR_CREATOR_2_CONTRAST_SET' + N]  = om3contrast(rec.contrast);
    return kv;"""
assert h.count(OLD) == 1, h.count(OLD)

NEW = """    /* 注意：app 里配方的真实字段是 v[0..11] / hi / mid / sh / eff / shp / con */
    if(!rec || !rec.v || rec.v.length < 12) throw new Error('这条配方没有色轮数据（v[]），已中止，未写入任何东西');
    var kv = {}, i;
    for(i = 0; i < 12; i++) kv['MODE_COLOR_CREATOR_2_VIVID_SET' + N + '_' + (i + 1)] = om3step(rec.v[i]);
    kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET' + N]   = om3step(rec.hi);
    kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_MIDDLE_SET' + N] = om3step(rec.mid);
    kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_LOW_SET' + N]    = om3step(rec.sh);
    kv['MODE_COLOR_CREATOR_2_SHADING_SET' + N]   = om3step(rec.eff);
    kv['MODE_COLOR_CREATOR_2_SHARP_SET' + N]     = om3sharp(rec.shp);
    kv['MODE_COLOR_CREATOR_2_CONTRAST_SET' + N]  = om3contrast(rec.con);
    return kv;"""
h = h.replace(OLD, NEW, 1)

# 色轮序号 → 颜色名，写日志时能对上（顺序若不对，一眼能看出来）
old_log = "    for(var i = 0; i < 12; i++) lg('　　 色轮 ' + (i + 1) + ' = ' + kv['MODE_COLOR_CREATOR_2_VIVID_SET' + slotN + '_' + (i + 1)]);"
if h.count(old_log) == 1:
    h = h.replace(old_log, """    var CN = ['黄','橙','橙红','红','洋红','紫','蓝','蓝青','青','绿青','绿','黄绿'];
    var cl = [];
    for(var i = 0; i < 12; i++) cl.push((i + 1) + CN[i] + '=' + kv['MODE_COLOR_CREATOR_2_VIVID_SET' + slotN + '_' + (i + 1)].replace('MODE_STEP_', ''));
    lg('　　 色轮（顺序：黄→橙→橙红→红→洋红→紫→蓝→蓝青→青→绿青→绿→黄绿）：' + cl.join(' '));""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('已修复字段名 bug（v/hi/mid/sh/eff/shp/con）+ 色轮顺序日志')
