# -*- coding: utf-8 -*-
"""配方「参数解读」文案生成器（专业口径）—— 供 gen_r51.py 调用。

口径（全部来自页面自己的资料 + 奥巴 COLOR 档的实际机制，不编作者原话）：
  · 12 色环（`#calib`）：1黄 2橙 3红 4品红 5紫 6蓝紫 7蓝 8浅蓝 9青 10绿 11黄绿 12嫩黄绿；
    v[i] 是**该色轴的饱和增减**（正=推浓 / 负=抽淡）
  · 色调曲线：hi/mid/sh = 高光/中间调/暗部；con = 对比；shp = 锐度；eff = 阴影补偿
  · 白平衡偏移 wba/wbg（A+ 琥珀偏暖 / B+ 蓝偏冷；G+ 绿 / M+ 品红，±7）；wbt 非空 = 固定色温
  · 关键机制：**色环管"哪个颜色浓"、曲线管"明暗反差"、白平衡管"整体冷暖"** ，三者互相独立；
    同一个 C 档里几个槽位可以各有各的白平衡偏移 —— 偏移得**自己在相机上拨**
"""
import io
import json
import sys

AX = ['黄', '橙', '红', '品红', '紫', '蓝紫', '蓝', '浅蓝', '青', '绿', '黄绿', '嫩黄绿']
WARM = [0, 1, 2, 3]
COOL = [4, 5, 6, 7]
GREEN = [8, 9, 10, 11]

# 色轴 → 摄影上的后果（推上去 / 收下来各一句）
UP = {
    '黄': '黄更亮更艳，秋叶、麦田、暖黄灯光更"响"；过量会让白墙发黄',
    '橙': '橙最讨巧：夕阳、肤色、木器都更有味道；推太多肤色偏橘',
    '红': '红更跳，红叶、红墙、口红更艳；同时会把红色主体从背景里拔出来',
    '品红': '粉紫更明显，晚霞带粉调，肤色往玫瑰走；拍人容易"梦幻"或"假"',
    '紫': '阴影与暮色偏紫，夜色更有电影感；大面积会让画面发闷',
    '蓝紫': '蓝紫更实，暮色与阴影偏紫蓝',
    '蓝': '天空与水面更蓝更沉，通透感上来',
    '浅蓝': '天空亮部更清透（对高光天空的层次帮助最大）',
    '青': '青更明显，雾气、水面、玻璃反光更冷',
    '绿': '植物更翠、更绿，草地与叶子更精神',
    '黄绿': '嫩叶与苔藓更亮，春绿更明显',
    '嫩黄绿': '最柔的那层黄绿更甜，嫩芽与阳光感更强',
}
DOWN = {
    '黄': '黄被抽淡，整体更冷静，金色秋叶会发闷',
    '橙': '橙退掉后肤色发白、夕阳发凉',
    '红': '红被收住——这是"高级感"的来源：红不再抢戏，肤色更稳',
    '品红': '粉紫退掉，肤色更中性，晚霞不那么"甜"',
    '紫': '紫退掉，暗部更干净',
    '蓝紫': '蓝紫退掉，暮色更中性',
    '蓝': '蓝被压，天空偏灰、不够沉',
    '浅蓝': '浅蓝被压，天空亮部不通透',
    '青': '青被收，雾气与水面的冷意减弱',
    '绿': '绿被抽走，植物偏土、发沉，不再翠',
    '黄绿': '黄绿收掉，新叶的甜亮感减弱',
    '嫩黄绿': '最柔的黄绿收掉，画面更"成人"、更克制',
}


def wbtxt(a, g):
    a = int(a or 0)
    g = int(g or 0)
    return ((('A+%d' % a) if a > 0 else ('B%d' % -a) if a < 0 else 'A0') + ' '
            + (('G+%d' % g) if g > 0 else ('M%d' % -g) if g < 0 else 'G0'))


def profile(r):
    v = list(r.get('v') or []) + [0] * 12
    w, c, gr = (sum(v[i] for i in WARM), sum(v[i] for i in COOL), sum(v[i] for i in GREEN))
    wba, wbg = int(r.get('wba') or 0), int(r.get('wbg') or 0)
    eff_w, eff_c = w + max(0, wba) * 3, c + max(0, -wba) * 3
    hi, mid, sh = int(r.get('hi') or 0), int(r.get('mid') or 0), int(r.get('sh') or 0)
    con, shp, eff = int(r.get('con') or 0), int(r.get('shp') or 0), int(r.get('eff') or 0)
    return {'v': v, 'w': w, 'c': c, 'g': gr, 'wba': wba, 'wbg': wbg, 'eff_w': eff_w,
            'eff_c': eff_c, 'hi': hi, 'mid': mid, 'sh': sh, 'con': con, 'shp': shp, 'eff': eff,
            'sat': sum(v), 'mono': (r.get('t') == 'MONO'), 'wbt': r.get('wbt'),
            'monoColor': (r.get('monoColor') or ''), 'grain': (r.get('grain') or ''),
            'hue': (r.get('hue') or ''), 'wb': (r.get('wb') or '')}


def sat_word(p):
    s = p['sat']
    return ('浓艳' if s >= 14 else '饱满' if s >= 7 else '微浓' if s >= 3 else
            '中性' if s >= -2 else '清淡' if s >= -8 else '寡淡')


def dir_word(p):
    d = p['eff_w'] - p['eff_c']
    return '明显偏暖' if d >= 8 else '偏暖' if d >= 4 else ('明显偏冷' if d <= -8 else '偏冷' if d <= -4 else '冷暖中性')


def con_word(p):
    if p['hi'] <= -3 and p['sh'] <= -3:
        return '硬朗'
    if p['con'] >= 2 or p['hi'] >= 2:
        return '硬朗'
    if p['con'] <= -1 or p['sh'] >= 2 or p['hi'] <= -1:
        return '平顺'
    return '中性'


def expo_advice(p):
    """曝光补偿方向（从色调曲线推）"""
    if p['sh'] <= -3:
        return '曝光补偿：暗部压得狠（Sh %+d）→ 亮部偏暗时 +0.3~0.7EV 把暗部捞回来' % p['sh']
    if p['mid'] >= 2:
        return '曝光补偿：中间调抬高（Mid %+d）→ 正常光线下可 −0.3EV 收一点，不然脸容易发白' % p['mid']
    if p['hi'] >= 2:
        return '曝光补偿：高光抬得多（Hi %+d）→ 亮部场景建议 −0.3~0.7EV' % p['hi']
    if p['sh'] >= 2:
        return '曝光补偿：暗部提了（Sh %+d）→ 按相机测光就行，欠一点也比过一点好' % p['sh']
    return '曝光补偿：按相机测光就行，不用刻意加减'


def trap(r, p):
    """最容易翻车的一点（挑参数里最尖锐的那条）"""
    d = p['eff_w'] - p['eff_c']
    if d >= 8:
        return '最容易翻车：暖上加暖 —— 暖光/钨丝灯里肤色发黄'
    if d <= -8:
        return '最容易翻车：冷调压场 —— 日落烛光会被抵消；近距离人像肤色偏青'
    if p['g'] >= 8:
        return '最容易翻车：绿推得多 —— 拍人肤色会带绿，别当人像卡用'
    if p['v'][3] >= 2:
        return '最容易翻车：品红偏多 —— 肤色往玫瑰走，拍人要么梦幻要么假'
    if sum(p['v']) >= 14:
        return '最容易翻车：饱和给得很足 —— 直出就很响，红色主体容易过'
    if sum(p['v']) <= -8:
        return '最容易翻车：颜色抽得多 —— 灰平天气（雾 / 阴天）会更没劲'
    if p['shp'] >= 2:
        return '最容易翻车：锐度推高 —— 弱光 / 高 ISO 会把噪点一起提出来'
    return '最容易翻车：反差靠中间调撑 —— 光比大的场面要靠曝光兜'


def order_advice(p):
    return '先动哪个：先色环（浓淡）→ 再曲线（明暗）→ 最后白平衡；别同时动两样'


def gen6(r):
    """→ dict(feel, key, tone, good, bad, tip)（每个都是纯文本，页面里再套 .row 结构）"""
    p = profile(r)
    if p['mono']:
        filt = p['monoColor'] or 'No Filter'
        fi = {'No Filter': '不做滤镜，各色按标称明度转灰',
              'Yellow Filter': '黄滤镜：压蓝、提黄绿 —— 天空与蓝更暗，云更有层次，肤色更干净',
              'Orange Filter': '橙滤镜：比黄更狠地压蓝，天空发暗、白云更突出',
              'Red Filter': '红滤镜：蓝几乎压到黑，天空最深、云最戏剧化，肤色偏暗',
              'Green Filter': '绿滤镜：突出植被的明暗差，肤色偏亮'}.get(filt, '滤镜会改变各色转灰的明度关系')
        feel = ('黑白底子，%s，反差%s。' % (fi, con_word(p)))
        key = ('黑白没有色相，只留下明暗：%s。彩色的差别在这里变成"哪块更亮"的差别 —— '
               '所以黑白配方的功夫全在明暗分布和滤镜上。' % fi)
        tone = ('色调曲线 高光 %+d / 中间调 %+d / 暗部 %+d，对比 %+d，阴影补偿 %+d，锐度 %+d。'
                % (p['hi'], p['mid'], p['sh'], p['con'], p['eff'], p['shp']))
        good = ['黑白题材：街头纪实、建筑线条、静物、想强调形状与光比的时候',
                '需要把"颜色差"翻译成"明暗差"来压平背景的时候']
        bad = ['靠颜色区分主体的题材（颜色差会被压成明度差，色相信息直接丢掉）',
               '想要浓郁色彩或暖调气氛的时候（黑白谈不上冷暖）']
        tip = ['白平衡：**对黑白不产生颜色**（挂 MONO 档时拨它没用）',
               expo_advice(p),
               '先动哪个：先挑滤镜（%s）→ 再动曲线（明暗）→ 颗粒最后加' % filt,
               '最容易翻车：' + ('暗部压得狠 + 光比大 → 阴影会糊成一片黑' if p['sh'] <= -3
                                else '黑白靠明度分主体，颜色接近的物件会粘在一起（换个滤镜或换机位）')]
        if p['grain']:
            tip.append('颗粒：%s' % p['grain'])
        return {'feel': feel, 'key': key, 'tone': tone,
                'good': '；'.join(good), 'bad': '；'.join(bad), 'tip': '；'.join(tip)}

    v = p['v']
    tops = sorted([i for i in range(12) if v[i] > 0], key=lambda i: -v[i])
    bots = sorted([i for i in range(12) if v[i] < 0], key=lambda i: v[i])
    ups = '、'.join('%s %+d' % (AX[i], v[i]) for i in tops[:4]) or '无'
    dns = '、'.join('%s %+d' % (AX[i], v[i]) for i in bots[:4]) or '无'
    feel = ('饱和度%s，%s，反差%s。' % (sat_word(p), dir_word(p), con_word(p)))
    # 第 55 轮：补两条退化情况 —— 12 轴全为 0、以及"只有往下的轴"（新补的配方里有这种）
    # 原来 tops 为空时会生成「色环把 无 推上去……具体到画面：。」这种句子
    if not tops and not bots:
        key = '12 个色轴全部为 0：这条不动色环，只靠影调曲线与白平衡出味道。'
    else:
        if tops and bots:
            key = '色环把 %s 推上去，把 %s 收下来。' % (ups, dns)
        elif tops:
            key = '色环把 %s 推上去，几乎没有往下收的轴。' % ups
        else:
            key = '色环没有往上推的轴，只把 %s 收下来。' % dns
        key += ('具体到画面：' + '；'.join(UP[AX[i]] for i in tops[:2]) + '。' if tops else
                '没有往上推的轴，画面里没有哪个颜色被刻意加强。')
        if bots:
            key += '往下收的后果：' + '；'.join(DOWN[AX[i]] for i in bots[:2]) + '。'
    tone = ('色调曲线 高光 %+d / 中间调 %+d / 暗部 %+d，对比 %+d，阴影补偿 %+d，锐度 %+d。'
            % (p['hi'], p['mid'], p['sh'], p['con'], p['eff'], p['shp']))
    tone += ('暗部与高光都收 → 反差偏硬、层次靠中间调撑；' if (p['hi'] <= -2 and p['sh'] <= -2) else
             '暗部提起、高光压住 → 反差平顺，亮暗都接得住；' if (p['sh'] >= 1 and p['hi'] <= -1) else
             '反差接近原片，不抢色环的戏；')
    good, bad = [], []
    if p['eff_c'] - p['eff_w'] >= 4:
        good.append('需要冷调压场：蓝调时刻、雨后、阴影、天空与水面占大比例的画面')
        bad.append('日落、烛光、暖色灯等本身偏暖的场面（冷调会把暖意抵消）')
        bad.append('想要"暖肤"的近距离人像（冷调会让肤色偏青灰）')
    elif p['eff_w'] - p['eff_c'] >= 4:
        good.append('需要暖调气氛：傍晚、灯光街景、木质与暖色主体')
        bad.append('室内钨丝灯、暖色灯光（暖上加暖，肤色容易发黄）')
        bad.append('雪、雾、水面等本身偏冷的题材（两边互相顶）')
    else:
        good.append('日常通吃、混光环境、不想让画面偏色的时候')
        bad.append('想要极强风格化的时候（这条走的是中性路线）')
    if p['g'] >= 8:
        good.append('绿色主体：植被、草地、苔藓、林间')
    if sat_word(p) in ('清淡', '寡淡'):
        bad.append('本身灰平的天气（雾、阴天）——低饱和叠低饱和会更没劲')
    if con_word(p) == '硬朗':
        bad.append('光比大又不好测光的场面（暗部容易压死、高光容易顶）')
    if p['shp'] >= 2:
        bad.append('需要"胶片柔"或高 ISO 弱光时（锐度推高会把噪点一起提出来）')
    tip = ['白平衡：偏移 **%s**%s —— 偏移要**自己在相机上拨**，同一档位里几个槽位可以各不相同'
           % (wbtxt(p['wba'], p['wbg']), ('（这条原本是固定色温 %sK，挂 AUTO 会更偏）' % p['wbt']) if p.get('wbt') else ''),
           expo_advice(p),
           order_advice(p),
           trap(r, p)]
    if p['hue']:
        tip.append('色相：%s' % p['hue'])
    return {'feel': feel, 'key': key, 'tone': tone,
            'good': '；'.join(good), 'bad': '；'.join(bad), 'tip': '；'.join(tip)}


if __name__ == '__main__':
    s = io.open(r'D:\workspace\om3-handbook\app\base.html', encoding='utf-8').read()
    i = s.index('window.__OM3RECIPES__')
    j = s.index('];', i) + 1
    REC = json.loads(s[s.index('=', i) + 1:j])
    want = sys.argv[1:]
    for r in REC:
        if want and r['slug'] not in want:
            continue
        g = gen6(r)
        p = profile(r)
        print('=' * 100)
        print('%-32s %s ｜ %s ｜ %s ｜ WB %s' % (r['n'], sat_word(p), dir_word(p), con_word(p), wbtxt(p['wba'], p['wbg'])))
        for k, lab in (('feel', '画面感觉'), ('key', '色彩重点'), ('tone', '影调'), ('good', '适合'), ('bad', '避开'), ('tip', '提示')):
            print('  【%s】%s' % (lab, g[k]))
