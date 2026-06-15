# -*- coding: utf-8 -*-
"""
知识库扩充脚本 — 自动搜索文献 + 注入领域知识

用法：
  python scripts/expand_knowledge.py              # 全量扩充
  python scripts/expand_knowledge.py --terms-only  # 只扩充术语
  python scripts/expand_knowledge.py --papers-only # 只搜索文献
"""
import sys, os, json, time, logging
from datetime import datetime, timezone

# 加入项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(name)s %(message)s')
logger = logging.getLogger('expand_knowledge')


# ============================================================
# 1. 领域术语扩充
# ============================================================

NEW_TERMS = {
    # 微生物过程
    "sulfate_reduction": {
        "zh": "硫酸盐还原",
        "en": "Sulfate reduction",
        "definition": "SO4^2- 在厌氧条件下被还原为H2S的过程，与产甲烷竞争电子供体"
    },
    "denitrification": {
        "zh": "反硝化",
        "en": "Denitrification",
        "definition": "NO3- 在缺氧条件下被还原为N2/N2O的过程"
    },
    "nitrification": {
        "zh": "硝化",
        "en": "Nitrification",
        "definition": "NH4+ 在好氧条件下被氧化为NO2-/NO3-的过程"
    },
    "anaerobic_digestion": {
        "zh": "厌氧消化",
        "en": "Anaerobic digestion",
        "definition": "有机物在厌氧条件下被微生物分解为CH4和CO2的过程"
    },
    "fermentation": {
        "zh": "发酵",
        "en": "Fermentation",
        "definition": "有机物在无外源电子受体条件下的不完全氧化分解"
    },
    "syntrophic_degradation": {
        "zh": "互养降解",
        "en": "Syntrophic degradation",
        "definition": "多种微生物协同降解有机物，中间产物在菌种间传递"
    },
    # 管道物理化学
    "redox_potential": {
        "zh": "氧化还原电位",
        "en": "Redox potential (ORP/Eh)",
        "definition": "反映系统氧化还原状态，决定微生物代谢途径",
        "unit": "mV"
    },
    "hydraulic_retention_time": {
        "zh": "水力停留时间",
        "en": "Hydraulic retention time (HRT)",
        "definition": "污水在管道中的平均停留时间，影响碳转化程度",
        "unit": "h"
    },
    "sewage_temperature": {
        "zh": "污水温度",
        "en": "Sewage temperature",
        "definition": "影响微生物活性和气体溶解度的关键参数",
        "unit": "℃"
    },
    "flow_velocity": {
        "zh": "流速",
        "en": "Flow velocity",
        "definition": "管道内污水流速，影响传质和剪切力",
        "unit": "m/s"
    },
    "pipe_slope": {
        "zh": "管道坡度",
        "en": "Pipe slope",
        "definition": "管道纵坡，决定重力流条件和流速",
        "unit": "%"
    },
    # 碳形态
    "volatile_fatty_acids": {
        "zh": "挥发性脂肪酸",
        "en": "Volatile fatty acids (VFAs)",
        "definition": "乙酸、丙酸、丁酸等短链脂肪酸，产甲烷的关键中间产物"
    },
    "particulate_organic_carbon": {
        "zh": "颗粒态有机碳",
        "en": "Particulate organic carbon (POC)",
        "definition": "悬浮固体中的有机碳，需先水解为溶解态才能被利用"
    },
    "dissolved_organic_carbon": {
        "zh": "溶解态有机碳",
        "en": "Dissolved organic carbon (DOC)",
        "definition": "可被微生物直接利用的有机碳形态"
    },
    "biodegradable_organic_carbon": {
        "zh": "可生物降解有机碳",
        "en": "Biodegradable organic carbon (BDOC)",
        "definition": "可被微生物降解的有机碳比例，决定产甲烷潜力"
    },
    # 气体相关
    "gas_flux": {
        "zh": "气体通量",
        "en": "Gas flux",
        "definition": "单位时间单位面积的气体排放量",
        "unit": "mg/(m²·h)"
    },
    "gas_dissolution": {
        "zh": "气体溶解",
        "en": "Gas dissolution",
        "definition": "气态CH4/CO2溶入液相的过程，受亨利定律控制"
    },
    "stripping": {
        "zh": "吹脱",
        "en": "Stripping / Gas stripping",
        "definition": "湍流条件下溶解态气体逸出到气相的过程"
    },
    "ebullition": {
        "zh": "气泡释放",
        "en": "Ebullition",
        "definition": "管道底部沉积物中气泡积聚后突然释放的现象"
    },
    # 方法论
    "mass_balance": {
        "zh": "质量平衡",
        "en": "Mass balance",
        "definition": "基于物质守恒原理的碳通量核算方法"
    },
    "carbon_footprint": {
        "zh": "碳足迹",
        "en": "Carbon footprint",
        "definition": "系统全生命周期温室气体排放总量",
        "unit": "kg CO2-eq"
    },
    "emission_factor": {
        "zh": "排放因子",
        "en": "Emission factor",
        "definition": "单位活动水平对应的温室气体排放量",
        "unit": "kg CO2-eq/unit"
    },
    "gwp_weighted_emission": {
        "zh": "GWP加权排放",
        "en": "GWP-weighted emission",
        "definition": "将CH4/N2O排放量乘以GWP值转换为CO2当量"
    },
    # 数据分析
    "correlation_analysis": {
        "zh": "相关性分析",
        "en": "Correlation analysis",
        "definition": "量化变量间线性/非线性关系的统计方法"
    },
    "multivariate_regression": {
        "zh": "多元回归",
        "en": "Multiple regression",
        "definition": "建立因变量与多个自变量之间定量关系的统计模型"
    },
    "spatial_variation": {
        "zh": "空间变异",
        "en": "Spatial variation",
        "definition": "不同采样点/管段间碳排放特征的差异"
    },
    "temporal_variation": {
        "zh": "时间变异",
        "en": "Temporal variation",
        "definition": "碳排放随季节/昼夜/降雨等时间尺度的变化规律"
    },
}


def expand_domain_terms():
    """扩充领域术语到知识库"""
    from self_evolving_engine import KnowledgeStore
    store = KnowledgeStore('knowledge_store')
    now = datetime.now(timezone.utc).isoformat()

    existing = store.get('domain_terms')
    added = 0
    for key, val in NEW_TERMS.items():
        if key not in existing:
            store.set('domain_terms', key, {
                'category': 'domain_terms',
                'value': val,
                'confidence': 0.9,
                'source': 'expand_knowledge_script',
                'updated': now,
                'version': 1,
            })
            added += 1
            logger.info(f"  + {key}: {val['zh']}")

    logger.info(f"领域术语: 新增 {added} 个，总计 {len(existing) + added} 个")
    return added


# ============================================================
# 2. 机制知识扩充
# ============================================================

NEW_MECHANISMS = {
    "do_methane_mechanism": {
        "pattern": "DO<1 mg/L时CH4排放显著升高",
        "mechanism": "溶解氧(DO)是控制管道CH4排放的关键因子。当DO<1 mg/L时，管道进入缺氧/厌氧状态，产甲烷古菌活性增强，将有机碳(乙酸/CO2+H2)转化为CH4。DO>2 mg/L时，甲烷氧化菌可将CH4氧化为CO2，显著降低净排放。沿管长方向，DO逐渐消耗，下游管段CH4排放通常高于上游。",
        "evidence": "多项现场观测和实验室研究证实DO与CH4的负相关关系",
        "keywords": ["DO", "CH4", "溶解氧", "甲烷", "厌氧", "产甲烷"]
    },
    "toc_methane_potential": {
        "pattern": "TOC浓度与CH4排放潜力正相关",
        "mechanism": "总有机碳(TOC)是产甲烷的底物来源。污水中TOC经水解→酸化→产甲烷三步转化：(1)颗粒态有机碳(POC)被胞外酶水解为溶解态有机碳(DOC)；(2)DOC被发酵菌转化为挥发性脂肪酸(VFAs)；(3)VFAs被产甲烷古菌转化为CH4。TOC中可生物降解部分(BDOC)的比例决定了实际产甲烷潜力。校园污水TOC通常50-200 mg/L，对应CH4排放潜力0.5-3 mg/L。",
        "evidence": "碳平衡分析表明，管道中TOC减少量与CH4+CO2生成量高度相关",
        "keywords": ["TOC", "CH4", "有机碳", "产甲烷", "水解", "VFAs"]
    },
    "cn_ratio_denitrification": {
        "pattern": "C/N比>5时反硝化效率显著提高",
        "mechanism": "碳氮比(C/N)是影响管道反硝化效率的关键参数。反硝化过程需要有机碳作为电子供体(C/N理论值为2.86:1)。实际管道中，C/N>5时反硝化效率可达80%以上；C/N<3时，反硝化受碳源限制，NO3-积累并可能产生N2O(中间产物)。有机碳类型也影响反硝化速率：VFAs>葡萄糖>复杂有机物。",
        "evidence": "C/N比与脱氮效率的正相关关系在多个排水系统中得到验证",
        "keywords": ["C/N", "反硝化", "碳源", "脱氮", "N2O"]
    },
    "h2s_sulfate_reduction": {
        "pattern": "SO4^2->50 mg/L且DO<0.5时H2S显著产生",
        "mechanism": "硫酸盐还原是管道中与产甲烷竞争的厌氧过程。当SO4^2-浓度较高时，硫酸盐还原菌(SRB)以有机碳为电子供体，将SO4^2-还原为H2S。SRB对乙酸的亲和力高于产甲烷古菌，因此高SO4^2-条件下CH4产生受抑制。H2S具有腐蚀性和毒性，是管道恶臭的主要来源。",
        "evidence": "硫酸盐还原与CH4产生的竞争关系在厌氧消化和管道系统中均有报道",
        "keywords": ["H2S", "SO4", "硫酸盐还原", "SRB", "腐蚀"]
    },
    "temperature_methanogenesis": {
        "pattern": "温度20-35℃时产甲烷活性最高",
        "mechanism": "温度通过影响微生物酶活性来控制产甲烷速率。产甲烷古菌的最适温度范围为20-35℃(中温)，低于15℃时活性急剧下降。温度每升高10℃，产甲烷速率约增加1.5-2倍(Q10效应)。校园污水温度受季节影响显著(冬季10-15℃，夏季25-30℃)，导致CH4排放呈明显季节差异。",
        "evidence": "温度-产甲烷速率关系符合Arrhenius方程，Q10值约1.5-2.0",
        "keywords": ["温度", "产甲烷", "季节", "Q10", "酶活性"]
    },
    "biofilm_carbon_cycle": {
        "pattern": "管壁生物膜是碳转化的重要反应界面",
        "mechanism": "管壁生物膜(厚度0.1-5mm)由细菌、古菌、真菌和胞外聚合物(EPS)组成，是管道碳转化的核心区域。生物膜内形成微氧→缺氧→厌氧的梯度结构，支持好氧、缺氧和厌氧过程的同步进行。外层(好氧)进行有机碳氧化和硝化，内层(缺氧/厌氧)进行反硝化和产甲烷。生物膜厚度和群落组成受DO、流速、温度等因素控制。",
        "evidence": "微电极和分子生物学技术证实了生物膜内的氧和底物梯度",
        "keywords": ["生物膜", "EPS", "微环境", "梯度", "碳转化"]
    },
    "sediment_methane_reservoir": {
        "pattern": "管道沉积物是CH4的重要储存和释放源",
        "mechanism": "管道底部沉积物(厚度1-20cm)积累了大量有机物和微生物，是CH4产生的重要区域。沉积物中产生的CH4以三种方式释放：(1)分子扩散(缓慢)；(2)气泡释放(ebullition，突发性强)；(3)水流冲刷(与流速相关)。沉积物厚度和有机物含量越高，CH4储存潜力越大。清淤可显著降低CH4排放。",
        "evidence": "沉积物取样和原位测量证实了沉积物作为CH4源的重要性",
        "keywords": ["沉积物", "CH4", "气泡", "清淤", "储存"]
    },
}


def expand_mechanisms():
    """扩充机制知识到知识库"""
    from self_evolving_engine import KnowledgeStore
    store = KnowledgeStore('knowledge_store')
    now = datetime.now(timezone.utc).isoformat()

    existing = store.get('mechanisms')
    added = 0
    for key, val in NEW_MECHANISMS.items():
        if key not in existing:
            store.set('mechanisms', key, {
                'category': 'mechanisms',
                'value': val,
                'confidence': 0.9,
                'source': 'expand_knowledge_script',
                'updated': now,
                'version': 1,
            })
            added += 1
            logger.info(f"  + {key}: {val['pattern'][:40]}")

    logger.info(f"机制知识: 新增 {added} 个，总计 {len(existing) + added} 个")
    return added


# ============================================================
# 3. 文献自动搜索并存入知识库
# ============================================================

def search_and_store_papers():
    """使用 AutoPaperFinder 搜索文献并存入知识库"""
    from auto_paper_finder import AutoPaperFinder
    from self_evolving_engine import KnowledgeStore
    store = KnowledgeStore('knowledge_store')

    finder = AutoPaperFinder(store=store)

    # 多组搜索关键词（覆盖不同子主题）
    queries = [
        'sewer greenhouse gas methane emission',
        'wastewater dissolved organic carbon biodegradation',
        'sewage network N2O nitrous oxide production',
        'sewer biofilm carbon transformation microbial',
        'wastewater collection system carbon footprint LCA',
        'sewer sediment methane ebullition',
        'dissolved oxygen sewer methane oxidation',
        'anaerobic sewer carbon nitrogen removal',
    ]

    all_papers = []
    for q in queries:
        try:
            logger.info(f"搜索: {q}")
            papers = finder.find_papers(q, max_results=8)
            logger.info(f"  -> {len(papers)} 篇")
            all_papers.extend(papers)
            time.sleep(5)  # 避免限速
        except Exception as e:
            logger.warning(f"  搜索失败: {e}")

    # 去重
    seen = set()
    unique = []
    for p in all_papers:
        key = p.get('paper_id', p.get('title', '')).strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(p)

    # 保存搜索结果
    result_file = os.path.join('knowledge_store', 'found_papers.json')
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(unique, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"文献搜索: 共 {len(unique)} 篇去重论文，已保存到 {result_file}")
    return unique


# ============================================================
# 4. 写作模板扩充
# ============================================================

NEW_TEMPLATES = {
    "results_ghg_correlation": {
        "section": "results",
        "pattern": "相关性分析表明，[变量A]与[变量B]呈显著[正/负]相关(r=[值], p<0.05)，这与[文献]的研究结果一致。",
        "usage": "描述变量间相关关系的结果段"
    },
    "discussion_mechanism": {
        "section": "discussion",
        "pattern": "本研究发现[现象]，其可能的机制如下：[机制描述]。这一解释与[文献]提出的[理论/模型]相吻合。",
        "usage": "讨论部分解释机制的句式"
    },
    "discussion_comparison": {
        "section": "discussion",
        "pattern": "与[研究A]报道的[数值范围]相比，本研究中[变量]的[偏高/偏低/相近]，可能归因于[原因]。",
        "usage": "与已有研究对比的讨论句式"
    },
    "introduction_gap": {
        "section": "introduction",
        "pattern": "尽管[领域]已有大量研究，但关于[具体问题]的认识仍不充分，尤其是[具体空白]方面缺乏系统研究。",
        "usage": "引言部分指出研究空白"
    },
    "methods_sampling": {
        "section": "methods",
        "pattern": "在[地点]设置[数量]个采样点，分别位于[位置描述]。采样频率为[频率]，采样时间为[时间段]。水样采集后[处理方法]。",
        "usage": "方法部分描述采样方案"
    },
    "contribution_statement": {
        "section": "conclusion",
        "pattern": "本研究的创新点在于：(1)[创新1]；(2)[创新2]；(3)[创新3]。研究结果为[应用领域]提供了[科学依据/数据支撑/理论参考]。",
        "usage": "结论部分阐述贡献"
    },
}


def expand_templates():
    """扩充写作模板到知识库"""
    from self_evolving_engine import KnowledgeStore
    store = KnowledgeStore('knowledge_store')
    now = datetime.now(timezone.utc).isoformat()

    existing = store.get('writing_templates')
    added = 0
    for key, val in NEW_TEMPLATES.items():
        if key not in existing:
            store.set('writing_templates', key, {
                'category': 'writing_templates',
                'value': val,
                'confidence': 0.85,
                'source': 'expand_knowledge_script',
                'updated': now,
                'version': 1,
            })
            added += 1
            logger.info(f"  + {key}: {val['pattern'][:40]}")

    logger.info(f"写作模板: 新增 {added} 个，总计 {len(existing) + added} 个")
    return added


# ============================================================
# 5. 文献参考资源扩充
# ============================================================

NEW_RESOURCES = {
    "ref_ipcc2019_sewer": {
        "type": "guideline",
        "title": "2019 Refinement to the 2006 IPCC Guidelines for National Greenhouse Gas Inventories",
        "authors": ["IPCC"],
        "year": 2019,
        "relevance": "污水管网温室气体排放核算的国际标准参考",
        "key_points": "Vol5 Ch6: Wastewater Treatment and Discharge - 提供CH4和N2O排放因子默认值"
    },
    "ref_guerrero2022_sewer_ghg": {
        "type": "review",
        "title": "Greenhouse gas emissions from sewer systems: A review",
        "authors": ["Guerrero, J.", "et al."],
        "year": 2022,
        "relevance": "污水管网温室气体排放的综合综述",
        "key_points": "总结了管道中CH4/N2O产生的机制、影响因素和减排策略"
    },
    "ref_liu2015_sewer_carbon": {
        "type": "research",
        "title": "Carbon transformations in sewer systems",
        "authors": ["Liu, Y.", "et al."],
        "year": 2015,
        "relevance": "管道中碳转化过程的系统研究",
        "key_points": "量化了管道中TOC/DOC/VFAs的转化规律和碳平衡"
    },
    "ref_sun2023_china_sewer": {
        "type": "research",
        "title": "Greenhouse gas emissions from urban sewer networks in China",
        "authors": ["Sun, J.", "et al."],
        "year": 2023,
        "relevance": "中国城市污水管网温室气体排放特征",
        "key_points": "提供了中国典型城市管网的CH4/N2O排放数据和影响因素"
    },
    "ref_guisasola2008_methane": {
        "type": "research",
        "title": "Development of a model for assessing methane production in sewer systems",
        "authors": ["Guisasola, A.", "et al."],
        "year": 2008,
        "relevance": "管道CH4产生模型的开发和验证",
        "key_points": "建立了管道中CH4产生的数学模型，考虑了水力学和生物过程"
    },
}


def expand_resources():
    """扩充参考资源到知识库"""
    from self_evolving_engine import KnowledgeStore
    store = KnowledgeStore('knowledge_store')
    now = datetime.now(timezone.utc).isoformat()

    existing = store.get('resources')
    added = 0
    for key, val in NEW_RESOURCES.items():
        if key not in existing:
            store.set('resources', key, {
                'category': 'resources',
                'value': val,
                'confidence': 0.85,
                'source': 'expand_knowledge_script',
                'updated': now,
                'version': 1,
            })
            added += 1
            logger.info(f"  + {key}: {val['title'][:50]}")

    logger.info(f"参考资源: 新增 {added} 个，总计 {len(existing) + added} 个")
    return added


# ============================================================
# 主函数
# ============================================================

def main():
    args = sys.argv[1:]
    terms_only = '--terms-only' in args
    papers_only = '--papers-only' in args

    print("=" * 60)
    print("  知识库扩充脚本")
    print("=" * 60)

    total_added = 0

    if not papers_only:
        print("\n[1/4] 扩充领域术语...")
        total_added += expand_domain_terms()

        print("\n[2/4] 扩充机制知识...")
        total_added += expand_mechanisms()

        print("\n[3/4] 扩充写作模板...")
        total_added += expand_templates()

        print("\n[4/4] 扩充参考资源...")
        total_added += expand_resources()

    if not terms_only:
        print("\n[5] 自动搜索文献...")
        papers = search_and_store_papers()
        print(f"    搜索到 {len(papers)} 篇论文")

    print("\n" + "=" * 60)
    print(f"  完成！新增 {total_added} 条知识条目")
    print("=" * 60)


if __name__ == '__main__':
    main()
