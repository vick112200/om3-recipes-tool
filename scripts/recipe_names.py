# -*- coding: utf-8 -*-
"""第 43 轮 · 配方中文名对照表（唯一真源）

规则（用户 2026-09-25 确认）：
  · 格式 = 中文名（English）
  · **只译有普通词义的名字**；原厂胶片名 / 机型名 / 代号不动
    （Fuji * / Kodachrome * / Kodak * / Portra * / Velvia * / Ilford HP5 /
      Fujicolor SUPERIA * / OM-3 Fujicolor 200 / Q116 / OM Chrome / OMTC Chrome /
      Portside Chrome / Vibrant Chrome —— 后四个的 "Chrome" 是胶片词，按同一条规则保留）
  · 不在表里的 slug = 名字不变

用法：
    from recipe_names import NAME_OF
    NAME_OF('murder_pink_real')   -> '真实（Real）'
"""
import io
import json
import sys

# slug -> 新名字（中文名（English））
NAME_MAP = {
    # ---- 有普通词义：译 ----
    'chris-brogan_a-bit-more-vivid':      '更鲜艳一点（A Bit More Vivid）',
    'burak-yilmaz_asteroid-city':         '小行星城（Asteroid City）',
    'alberto_torrejon_bleached':          '褪色（Bleached）',
    'kaleigh-whitaker_bluegill-teal':     '蓝鳃青（Bluegill Teal）',
    'stella-toul_carte-postal':           '明信片（carte postale）',
    'basi-torre_cinematic-tundra':        '电影感苔原（Cinematic Tundra）',
    'videopic_city_look':                 '都市感（City Look）',
    'robson-cabanas_cityeurope':          '欧洲城市（CityEurope）',
    'ian-will_cool-spring':               '冷泉（Cool Spring）',
    'om_system_default_1':                '默认 1（Default - 1）',
    'om_system_default_2':                '默认 2（Default - 2）',
    'om_system_default_3':                '默认 3（Default - 3）',
    'om_system_default_4':                '默认 4（Default - 4）',
    'luis-chavez_dirty-pop':              '脏流行（Dirty Pop）',
    'isaac-mitropoulos_dreamy-white':     '梦幻白（Dreamy White）',
    'emily_m4nerds_m4nerds':              '艾米丽自定义配色（Emily\u2019s Custom Color Profile）',
    'kaleigh-whitaker-estill-springs-green': '埃斯蒂尔斯普林斯绿（Estill Springs Green）',
    'jerred_z_eternal_sunshine':          '永恒阳光（Eternal Sunshine）',
    'george_holden_filmed':               '胶片感（Filmed）',
    'ian-will_kinda-portra-v2':           '有点像波特拉（Kinda Portra）',
    'james-bloomer_kodachrome-64-v0':     'Kodachrome 64（早期版）',
    'tom-jackson_kodachrome-64-print':    'Kodachrome 64（冲印版）',
    'om-system_natural':                  '自然（Natural）',
    'peter-turner_night-market':          '夜市（Night Market）',
    'kyler-steele_nostalgic-summer':      '怀旧之夏（Nostalgic Summer）',
    'ian-will_ode-to-ansel':              '致安塞尔（Ode to Ansel）',
    'james-bloomer_om-3-tokyo-wetzlar':   'OM-3 东京—韦茨拉尔（OM-3 Tokyo-Wetzlar）',
    'james-bloomer_om-3-x-monochrome-film-emulation-profile':
                                          'OM-3 X 单色胶片模拟（X-Monochrome）',
    'ali-o-keefe_omtc-cool':              'OMTC 冷调（OMTC Cool）',
    'ali_o_keefe_omtc_soft':              'OMTC 柔调（OMTC Soft）',
    'ali_o_keefe_omtc_warm':              'OMTC 暖调（OMTC Warm）',
    'paul_clark_paul_clark_recipe':       '保罗·克拉克配方（Paul Clark recipe）',
    'ian-will_pnw':                       '太平洋西北（PNW）',
    'mindy_michaels_rainforest_vibes':    '雨林气息（Rainforest Vibes）',
    'murder_pink_real':                   '真实（Real）',
    'kitty-marie_red-soda-pop':           '红色汽水（Red Soda Pop）',
    'andrew-gow_rose-gold':               '玫瑰金（Rose Gold）',
    'gal_root_rusty_vintage':             '锈色复古（Rusty Vintage）',
    'murder_pink_subdued':                '沉静（Subdued）',
    'ian-will_sunset-shift':              '微醺落日（Subtle Sunset）',
    'peter-turner_sydney-grain':          '悉尼颗粒（Sydney Grain）',
    'terry_mclaughlin_terry_mclaughlin_recipe': '特里·麦克劳克林配方（Terry McLaughlin recipe）',
    'burak-yilmaz_the-night-mayor':       '夜市长（The Night Mayor）',
    'karol-mizunia_vintage-teal':         '复古青（Vintage Teal）',
    # ---- 新录入（第 43 轮）----
    'momo_everyday':                      '日常挂机',
}

# 明确「保留原名」的 slug（写出来是为了让探针能断言"这些名字没被误改"）
KEEP = [
    'ibd_fuji-acros', 'ibd-fuji-astia', 'ibd-fuji-classic-chrome', 'jack_wang_fuji_classic_chrome',
    'ibd-fuji-classic-neg', 'ibd-fuji-eterna', 'ibd_fuji-monochrome', 'ibd-fuji-pro-neg-hi',
    'ibd-fuji-pro-neg-std', 'ibd-fuji-provia', 'ibd-fuji-velvia',
    'james-bloomer_fujicolor-superia-premium-400', 'burak-yilmaz_ilford-hp5',
    'angelo_gabelli_kodachrome_25', 'gareth_b_kodachrome_25', 'isaac-mitropoulos_kodachrome-25',
    'james-bloomer_kodachrome-64', 'gareth_b_kodachrome_64', 'isaac-mitropoulos_kodachrome-64',
    'james_bloomer_kodachrome_slim_aarons', 'james-bloomer_kodak-gold-200',
    'james-bloomer_om-3-fujicolor-200', 'isaac-mitropoulos_portra-160',
    'peter-turner_portra-400', 'isaac-mitropoulos_portra-400', 'james-bloomer_portra-400',
    'robsoncabanas_q116', 'rob-trek_velvia', 'videopic_velvia-50',
    'isaac-mitropoulos_velvia-50',
    'jonathan_paragas_om_chrome', 'ali_o_keefe_omtc_chrome',
    'burak-yilmaz_portside-chrome', 'dave_herring_vibrant_chrome',
]


def NAME_OF(slug, old=None):
    return NAME_MAP.get(slug, old)


def check(base_html):
    """自检：表里的 slug 必须都在库里，KEEP 里的名字必须没被表覆盖。"""
    s = io.open(base_html, encoding='utf-8').read()
    i = s.find('window.__OM3RECIPES__')
    j = s.index('=', i) + 1
    while s[j].isspace():
        j += 1
    rec = json.JSONDecoder().raw_decode(s, j)[0]
    slugs = dict((r['slug'], r['n']) for r in rec)
    bad = [k for k in NAME_MAP if k not in slugs]
    bad2 = [k for k in KEEP if k in NAME_MAP]
    bad3 = [k for k in KEEP if k not in slugs]
    return slugs, bad, bad2, bad3


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    slugs, bad, bad2, bad3 = check(r'D:\workspace\om3-handbook\app\base.html')
    print('库里 %d 条；改名的 %d 条，保留的 %d 条' % (len(slugs), len(NAME_MAP), len(KEEP)))
    if bad:
        print('⚠ 表里有但库里没有：', bad)
    if bad2:
        print('⚠ 同时出现在 NAME_MAP 和 KEEP：', bad2)
    if bad3:
        print('⚠ KEEP 里有但库里没有：', bad3)
    print()
    print('%-52s %-42s %s' % ('slug', '旧名', '新名'))
    for slug, old in sorted(slugs.items()):
        print('%-52s %-42s %s' % (slug, old, NAME_OF(slug, old) if slug in NAME_MAP else '（不变）'))
