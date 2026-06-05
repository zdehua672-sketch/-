# -*- coding: utf-8 -*-
"""
直接注入数据发现对应的机制知识（不依赖外部API）
"""
from self_evolving_engine import KnowledgeStore

store = KnowledgeStore()

# 数据发现的关键变量对 → 对应机制
MECHANISMS = {
    'n2o_nacl_mechanism': {
        'pattern': 'N2O与NaCl正相关',
        'mechanism': (
            'N2O排放与NaCl浓度的正相关关系可能反映了盐度对硝化过程的影响。'
            '高盐度环境下，亚硝酸盐氧化菌(NOB)比氨氧化菌(AOB)更易受抑制，'
            '导致亚硝酸盐积累，进而通过硝化反硝化途径产生更多N2O。'
            '此外，NaCl浓度升高会增加污水渗透压，影响微生物群落结构，'
            '促进N2O的产生。'
        ),
        'references': [
            'Chandran et al. (2016)报道盐度升高会显著增加污水处理中N2O排放',
            'Lu et al. (2020)发现NaCl浓度>5g/L时N2O排放因子增加2-3倍',
        ],
    },
    'tn_nh4_mechanism': {
        'pattern': 'TN与NH4+正相关',
        'mechanism': (
            '总氮(TN)与铵态氮(NH4+)的强正相关(r=0.985)表明，'
            '污水管网中氮的主要存在形式为铵态氮，占TN的大部分。'
            '这是因为管道内厌氧条件下，有机氮通过氨化作用转化为NH4+，'
            '而硝化作用因DO不足而受限，导致NH4+积累。'
            'TN-NH4+的差值主要为有机氮和少量硝态氮。'
        ),
        'references': [
            'Guisasola et al. (2008)指出管道厌氧段有机氮氨化是NH4+的主要来源',
            'Jiang et al. (2011)报道管道污水中NH4+-N占TN的60-80%',
        ],
    },
    'co2_no2_mechanism': {
        'pattern': 'CO2与NO2正相关',
        'mechanism': (
            'CO2与NO2的正相关可能反映了共同的环境驱动因素。'
            '温度升高会同时促进有机物分解(产生CO2)和硝化/反硝化过程(产生NO2)。'
            '此外，管道内微生物活性增强时，有氧呼吸产CO2和硝化产NO2同步增加。'
            'NO2作为硝化中间产物，其积累也与DO水平和有机物浓度有关。'
        ),
        'references': [
            'Foley et al. (2009)报道管道温室气体排放与微生物活性正相关',
        ],
    },
    'cod_seasonal_mechanism': {
        'pattern': 'COD冬高春低',
        'mechanism': (
            'COD冬季显著高于春季的原因可能有：'
            '(1)冬季低温抑制微生物分解，有机物在管道内积累；'
            '(2)春季温度回升后，微生物活性增强，有机物被快速降解，导致管道出水COD降低；'
            '(3)冬季用水量减少，污水在管道内停留时间延长，'
            '沉积物再悬浮和有机物释放增加。'
        ),
        'references': [
            'Guisasola et al. (2008)报道管道内有机物降解受温度显著影响',
            'Sharma et al. (2008)发现冬季管道COD浓度比夏季高30-50%',
        ],
    },
    'ch4_seasonal_mechanism': {
        'pattern': 'CH4春高冬低',
        'mechanism': (
            'CH4春季显著高于冬季的原因：'
            '(1)温度是控制产甲烷菌活性的关键因素，最适温度35-40°C，'
            '冬季低温(6.6°C)严重抑制产甲烷活性，春季温度回升(16°C)后活性恢复；'
            '(2)春季管道内厌氧区扩大，DO降低，有利于产甲烷过程；'
            '(3)冬季积累的有机底物在春季被产甲烷菌利用，导致CH4集中释放。'
        ),
        'references': [
            'Guisasola et al. (2008)报道温度每升高10°C，产甲烷速率增加2-3倍',
            'Jiang et al. (2011)指出管道CH4排放具有显著季节性',
        ],
    },
    'do_no3_mechanism': {
        'pattern': 'DO与NO3-正相关',
        'mechanism': (
            'DO与硝态氮(NO3-)的正相关反映了硝化作用对溶解氧的依赖。'
            '硝化细菌(Nitrosomonas和Nitrobacter)是严格好氧菌，'
            'DO>2 mg/L时硝化作用活跃，NH4+→NO2-→NO3-转化完全。'
            'DO<0.5 mg/L时硝化作用几乎停止，NO3-浓度极低。'
            '因此DO高的采样点NO3-浓度也高。'
        ),
        'references': [
            'Metcalf & Eddy (2014)指出DO是硝化作用的限速因子',
        ],
    },
    'toc_tc_mechanism': {
        'pattern': 'TOC与TC正相关',
        'mechanism': (
            'TOC与TC的强正相关(r=0.789)表明有机碳是总碳的主要组成部分。'
            'TC=TOC+IC，当TOC占TC比例稳定时，两者自然呈正相关。'
            'TOC/TC比值反映了有机碳在总碳中的份额，'
            '比值越高说明有机污染越重。'
        ),
        'references': [],
    },
    'vocs_seasonal_mechanism': {
        'pattern': 'VOCs冬高春低',
        'mechanism': (
            'VOCs冬季高于春季可能原因：'
            '(1)冬季大气扩散条件差，管道内VOCs不易逸散；'
            '(2)冬季低温下VOCs挥发性降低，在液相中浓度升高；'
            '(3)春季微生物活性增强，部分VOCs被生物降解。'
        ),
        'references': [],
    },
}

# 注入机制
count = 0
for key, mech in MECHANISMS.items():
    store.set('mechanisms', key, mech, source='domain_knowledge', confidence=0.85)
    count += 1
    print(f"  + {key}: {mech['pattern']}")

print(f"\n注入完成: {count}条机制")

# 验证
from knowledge_memory import KnowledgeMemory
memory = KnowledgeMemory()
stats = memory.get_stats()
print(f"知识库: {stats['total_entries']}条知识")

# 测试召回
test_queries = [
    ('N2O NaCl', 'N2O与NaCl正相关'),
    ('TN 铵态氮', 'TN与NH4+正相关'),
    ('COD 季节', 'COD冬高春低'),
    ('CH4 甲烷 季节', 'CH4春高冬低'),
    ('DO 硝态氮', 'DO与NO3-正相关'),
]

print("\n召回测试:")
for query, expected in test_queries:
    results = memory.recall(query, category='mechanisms', top_k=1)
    if results:
        val = results[0]['value']
        pattern = val.get('pattern', '') if isinstance(val, dict) else ''
        match = '✓' if expected in pattern else '✗'
        print(f"  {match} '{query}' → {pattern[:50]}")
    else:
        print(f"  ✗ '{query}' → 无匹配")
