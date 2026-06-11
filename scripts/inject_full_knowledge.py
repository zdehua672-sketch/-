# -*- coding: utf-8 -*-
"""
完整知识库注入脚本
==================
注入领域机制知识、文献引用、学术术语到 KnowledgeStore。
运行一次即可，数据持久化到 knowledge_store/ 目录。

用法:
    python scripts/inject_full_knowledge.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_memory import KnowledgeMemory


def inject_mechanisms(memory):
    """注入领域机制知识"""
    mechanisms = [
        # 碳氮耦合机制
        {
            'key': 'toc_ch4_mechanism',
            'pattern': 'TOC -> CH4',
            'mechanism': '有机碳(TOC)是产甲烷菌的主要底物。在厌氧条件下，产甲烷菌通过乙酸发酵或CO2还原途径将有机碳转化为甲烷。TOC浓度越高，底物越充足，甲烷产生量越大。污水管网中沉积物的有机碳含量是决定甲烷排放的关键因素。',
            'mechanism_en': 'Organic carbon (TOC) serves as the primary substrate for methanogenic archaea. Under anaerobic conditions, methanogens convert organic carbon to methane through acetoclastic or hydrogenotrophic pathways.',
            'references': ['Guisasola et al., 2008, Water Research', 'Liu et al., 2015, Environmental Science & Technology'],
            'var1': 'TOC', 'var2': 'CH4', 'relation': 'positive',
        },
        {
            'key': 'do_ch4_mechanism',
            'pattern': 'DO -| CH4',
            'mechanism': '溶解氧(DO)对甲烷产生有显著抑制作用。甲烷菌是严格厌氧菌，DO>0.2mg/L即可抑制其活性。好氧条件下，甲烷氧化菌(MOB)可在有氧层氧化甲烷为CO2，减少甲烷排放。管网中DO的空间分布决定了甲烷产生的热区。',
            'mechanism_en': 'Dissolved oxygen (DO) significantly inhibits methanogenesis. Methanogens are strict anaerobes; DO > 0.2 mg/L suppresses their activity. Methanotrophic bacteria (MOB) oxidize CH4 to CO2 in aerobic zones.',
            'references': ['Guisasola et al., 2008', 'Czepiel et al., 1993'],
            'var1': 'DO', 'var2': 'CH4', 'relation': 'negative',
        },
        {
            'key': 'toc_co2_mechanism',
            'pattern': 'TOC -> CO2',
            'mechanism': '有机碳的好氧分解和厌氧发酵都会产生CO2。好氧条件下，异养菌通过有氧呼吸将有机碳氧化为CO2和H2O。厌氧条件下，发酵菌将有机碳分解为挥发性脂肪酸(VFA)和CO2。管网中CO2的产生是碳循环的重要环节。',
            'mechanism_en': 'CO2 is produced through both aerobic decomposition and anaerobic fermentation of organic carbon. Heterotrophic bacteria oxidize organic carbon to CO2 under aerobic conditions.',
            'references': ['Jiang et al., 2011', 'Sharma et al., 2021'],
            'var1': 'TOC', 'var2': 'CO2', 'relation': 'positive',
        },
        {
            'key': 'cod_ch4_mechanism',
            'pattern': 'COD -> CH4',
            'mechanism': '化学需氧量(COD)反映水体中可被氧化的有机物总量。COD越高，可被产甲烷菌利用的有机底物越丰富。在管网厌氧环境中，COD的降解与甲烷产生呈正相关。COD/TOC比值可反映有机物的可生物降解性。',
            'mechanism_en': 'Chemical Oxygen Demand (COD) reflects the total oxidizable organic matter. Higher COD provides more substrate for methanogenic archaea in anaerobic sewer environments.',
            'references': ['Cakir & Stoeckel, 2000', 'Ahn et al., 2011'],
            'var1': 'COD', 'var2': 'CH4', 'relation': 'positive',
        },
        # 氮转化机制
        {
            'key': 'nh4_ch4_mechanism',
            'pattern': 'NH4+ -> CH4',
            'mechanism': '铵态氮(NH4+)与甲烷产生的关联机制包括：(1)氨化作用产生NH4+的同时释放有机碳底物；(2)高浓度NH4+可抑制产甲烷菌(IC50约3000mg/L)；(3)NH4+与CH4在氮碳耦合中存在协同效应。在低碳氮比条件下，NH4+对CH4的促进作用更明显。',
            'mechanism_en': 'Ammonium (NH4+) relates to CH4 production through: ammonification releasing organic carbon substrates; high NH4+ inhibiting methanogens (IC50 ~3000 mg/L); synergistic effects in C-N coupling.',
            'references': ['Rajagopal et al., 2013', 'Yenigün & Demirel, 2013'],
            'var1': 'NH4+', 'var2': 'CH4', 'relation': 'complex',
        },
        {
            'key': 'tn_tp_mechanism',
            'pattern': 'TN ~ TP',
            'mechanism': '总氮(TN)与总磷(TP)的共变关系反映了污水中营养盐的同源性。生活污水中N和P主要来自人类排泄物和洗涤剂，因此通常呈正相关。TN/TP比值可指示污水的营养盐特征和生物可利用性。',
            'mechanism_en': 'The co-variation of TN and TP reflects their common sources in sewage (human excreta and detergents). The N/P ratio indicates nutrient characteristics and bioavailability.',
            'references': ['Metcalf & Eddy, 2003', 'Henze et al., 2008'],
            'var1': 'TN', 'var2': 'TP', 'relation': 'positive',
        },
        # 温度效应
        {
            'key': 'temperature_seasonal',
            'pattern': 'Temperature -> CH4/CO2',
            'mechanism': '温度是驱动碳排放季节差异的核心因素。Q10效应：温度每升高10°C，微生物代谢速率增加2-3倍。冬季(5-10°C)微生物活性低，碳排放量小；夏季(20-30°C)微生物活跃，碳排放量大。产甲烷菌的最适温度为35-40°C(中温)或50-60°C(高温)。',
            'mechanism_en': 'Temperature is the core driver of seasonal carbon emission differences. Q10 effect: metabolic rate increases 2-3x per 10°C rise. Optimal temperature for methanogens: 35-40°C (mesophilic) or 50-60°C (thermophilic).',
            'references': ['Liu et al., 2015', 'Nielsen et al., 2019'],
            'var1': 'Temperature', 'var2': 'CH4/CO2', 'relation': 'positive',
        },
        # 空间分布
        {
            'key': 'spatial_distribution',
            'pattern': 'Distance -> CH4/CO2/H2S',
            'mechanism': '沿管网距离增加，碳排放呈空间梯度变化。管口(DO高)以CO2为主；中段(DO降低)开始产生CH4；末端(完全厌氧)CH4和H2S排放最大。沉积物积累、水力停留时间、管径大小都是影响空间分布的因素。',
            'mechanism_en': 'Along sewer networks, carbon emissions show spatial gradients. Inlet (high DO): mainly CO2. Middle (decreasing DO): CH4 begins. Outlet (fully anaerobic): maximum CH4 and H2S.',
            'references': ['Sharma et al., 2021', 'Foley et al., 2009'],
            'var1': 'Distance', 'var2': 'CH4/CO2/H2S', 'relation': 'gradient',
        },
        # 泥水效应
        {
            'key': 'sediment_effect',
            'pattern': 'Sediment -> CH4/CO2',
            'mechanism': '管网沉积物是碳排放的重要来源。沉积物中有机物浓度高、DO极低，是产甲烷的热区。沉积物厚度增加→厌氧体积增大→甲烷产量增加。泥水界面是生物地球化学反应的活跃区域，碳氮硫的转化在此集中发生。',
            'mechanism_en': 'Sewer sediments are major sources of carbon emissions. High organic matter and near-zero DO in sediments create hotspots for methanogenesis. Sediment depth correlates with anaerobic volume and CH4 production.',
            'references': ['Sharma et al., 2021', 'Hvitved-Jacobsen et al., 2013'],
            'var1': 'Sediment', 'var2': 'CH4/CO2', 'relation': 'positive',
        },
    ]

    for m in mechanisms:
        memory.remember(m, category='mechanisms', source='inject')
    print(f'  注入机制知识: {len(mechanisms)} 条')


def inject_domain_terms(memory):
    """注入领域术语"""
    terms = {
        # 碳排放术语
        'CH4': {'zh': '甲烷', 'en': 'Methane', 'category': 'greenhouse_gas', 'gwp': 28},
        'CO2': {'zh': '二氧化碳', 'en': 'Carbon dioxide', 'category': 'greenhouse_gas', 'gwp': 1},
        'N2O': {'zh': '氧化亚氮', 'en': 'Nitrous oxide', 'category': 'greenhouse_gas', 'gwp': 265},
        'VOCs': {'zh': '挥发性有机物', 'en': 'Volatile organic compounds', 'category': 'air_pollutant'},
        'H2S': {'zh': '硫化氢', 'en': 'Hydrogen sulfide', 'category': 'air_pollutant'},
        'GHG': {'zh': '温室气体', 'en': 'Greenhouse gas', 'category': 'concept'},
        'GWP': {'zh': '全球变暖潜势', 'en': 'Global warming potential', 'category': 'concept'},
        # 水质术语
        'TOC': {'zh': '总有机碳', 'en': 'Total organic carbon', 'category': 'water_quality'},
        'COD': {'zh': '化学需氧量', 'en': 'Chemical oxygen demand', 'category': 'water_quality'},
        'BOD': {'zh': '生化需氧量', 'en': 'Biochemical oxygen demand', 'category': 'water_quality'},
        'DO': {'zh': '溶解氧', 'en': 'Dissolved oxygen', 'category': 'water_quality'},
        'TN': {'zh': '总氮', 'en': 'Total nitrogen', 'category': 'water_quality'},
        'TP': {'zh': '总磷', 'en': 'Total phosphorus', 'category': 'water_quality'},
        'IC': {'zh': '无机碳', 'en': 'Inorganic carbon', 'category': 'water_quality'},
        'TC': {'zh': '总碳', 'en': 'Total carbon', 'category': 'water_quality'},
        'NH4+': {'zh': '铵态氮', 'en': 'Ammonium nitrogen', 'category': 'water_quality'},
        'NO3-': {'zh': '硝态氮', 'en': 'Nitrate nitrogen', 'category': 'water_quality'},
        # 微生物术语
        'methanogen': {'zh': '产甲烷菌', 'en': 'Methanogenic archaea', 'category': 'microorganism'},
        'methanotroph': {'zh': '甲烷氧化菌', 'en': 'Methanotrophic bacteria', 'category': 'microorganism'},
        'SRB': {'zh': '硫酸盐还原菌', 'en': 'Sulfate-reducing bacteria', 'category': 'microorganism'},
        # 管网术语
        'sewer': {'zh': '污水管网', 'en': 'Sewer network', 'category': 'infrastructure'},
        'sediment': {'zh': '沉积物', 'en': 'Sediment', 'category': 'infrastructure'},
        'biofilm': {'zh': '生物膜', 'en': 'Biofilm', 'category': 'infrastructure'},
        # 统计术语
        'Pearson': {'zh': '皮尔逊相关', 'en': 'Pearson correlation', 'category': 'statistics'},
        'PCA': {'zh': '主成分分析', 'en': 'Principal component analysis', 'category': 'statistics'},
        'HCA': {'zh': '层次聚类分析', 'en': 'Hierarchical cluster analysis', 'category': 'statistics'},
        'ANOVA': {'zh': '方差分析', 'en': 'Analysis of variance', 'category': 'statistics'},
    }

    for key, term in terms.items():
        memory.remember(term, category='domain_terms', source='inject')
    print(f'  注入领域术语: {len(terms)} 条')


def inject_references(memory):
    """注入核心参考文献"""
    refs = [
        {
            'key': 'ref_guisasola2008',
            'type': 'academic_paper',
            'title': 'Methane production in sewer systems',
            'authors': ['Guisasola, A.', 'de Haas, D.', 'Keller, J.', 'Yuan, Z.'],
            'year': 2008,
            'journal': 'Water Research',
            'doi': '10.1016/j.watres.2008.03.016',
            'abstract': 'Review of methane formation mechanisms in sewer networks, covering biofilm processes, sediment contributions, and gas-liquid mass transfer.',
        },
        {
            'key': 'ref_sharma2021',
            'type': 'academic_paper',
            'title': 'Greenhouse gas emissions from sewers: A review',
            'authors': ['Sharma, K.', 'Aryal, R.', 'Murthy, S.', 'Yuan, Z.'],
            'year': 2021,
            'journal': 'Water Research',
            'abstract': 'Comprehensive review of GHG emissions from sewer systems including CH4, CO2, N2O, and H2S. Covers spatial-temporal patterns, influencing factors, and mitigation strategies.',
        },
        {
            'key': 'ref_liu2015',
            'type': 'academic_paper',
            'title': 'Methane and nitrous oxide emissions from urban sewage systems',
            'authors': ['Liu, Y.', 'Ni, B.J.', 'Sharma, K.R.', 'Yuan, Z.'],
            'year': 2015,
            'journal': 'Environmental Science & Technology',
            'abstract': 'Quantification of CH4 and N2O emissions from urban sewage systems with seasonal and spatial analysis.',
        },
        {
            'key': 'ref_foley2009',
            'type': 'academic_paper',
            'title': 'GHG production and emission from a full-scale anaerobic sewer system',
            'authors': ['Foley, J.', 'Yuan, Z.', 'Lant, P.'],
            'year': 2009,
            'journal': 'Water Research',
            'abstract': 'Full-scale measurement of greenhouse gas production in anaerobic sewer systems.',
        },
        {
            'key': 'ref_rahman2021',
            'type': 'academic_paper',
            'title': 'Carbon transformation and greenhouse gas emissions in sewer systems',
            'authors': ['Rahman, A.', 'Yuan, Z.', 'Sharma, K.'],
            'year': 2021,
            'journal': 'Science of the Total Environment',
            'abstract': 'Carbon transformation processes and GHG emissions in sewer systems with focus on carbon mass balance.',
        },
    ]

    for ref in refs:
        memory.remember(ref, category='resources', source='inject')
    print(f'  注入参考文献: {len(refs)} 条')


def inject_writing_templates(memory):
    """注入写作模板"""
    templates = {
        'discussion_opening': {
            'zh': '本研究系统分析了{domain}中{variables}的时空分布特征及其驱动机制。结果表明{main_finding}。',
            'en': 'This study systematically analyzed the spatiotemporal distribution of {variables} in {domain}. Results showed that {main_finding}.',
        },
        'correlation_discussion': {
            'zh': '{var1}与{var2}呈{direction}相关(r={r:.3f}, p={p:.4f})，这一结果与{reference}的研究一致。{mechanism}',
            'en': '{var1} showed a {direction} correlation with {var2} (r={r:.3f}, p={p:.4f}), consistent with {reference}. {mechanism}',
        },
        'seasonal_discussion': {
            'zh': '{variable}在{season_high}显著高于{season_low}({test}: p={p:.4f})，这可能与{mechanism}有关。温度效应是驱动季节差异的主要因素。',
            'en': '{variable} was significantly higher in {season_high} than {season_low} ({test}: p={p:.4f}), likely due to {mechanism}.',
        },
        'limitation_statement': {
            'zh': '本研究存在以下局限性：(1){limit1}；(2){limit2}；(3){limit3}。未来研究应{future}。',
            'en': 'This study has the following limitations: (1){limit1}; (2){limit2}; (3){limit3}. Future work should {future}.',
        },
    }

    for key, tpl in templates.items():
        memory.remember(tpl, category='writing_templates', source='inject')
    print(f'  注入写作模板: {len(templates)} 条')


def main():
    print('=' * 50)
    print('  完整知识库注入')
    print('=' * 50)

    memory = KnowledgeMemory()

    inject_mechanisms(memory)
    inject_domain_terms(memory)
    inject_references(memory)
    inject_writing_templates(memory)

    stats = memory.get_stats()
    print(f'\n知识库总计: {stats.get("total_entries", "?")} 条知识')
    print('注入完成!')


if __name__ == '__main__':
    main()
