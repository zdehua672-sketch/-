# -*- coding: utf-8 -*-
"""
端到端集成测试
==============
用模拟数据测试完整的论文生成流程，
验证所有模块的连通性。

运行: python test_full_pipeline.py
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def create_test_data(output_dir):
    """创建模拟测试数据"""
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    n = 30
    data = {
        '采样点': [f'R{i+1}' for i in range(n)],
        '季节': ['冬季'] * 15 + ['春季'] * 15,
        'CH4平均值': np.random.normal(25, 8, n).clip(5, 50),
        'CO2': np.random.normal(800, 200, n).clip(300, 1500),
        'N2O平均值': np.random.normal(0.5, 0.2, n).clip(0.1, 1.5),
        'VOCs(ppb)': np.random.normal(50, 20, n).clip(10, 120),
        'TOC（mg/L)': np.random.normal(45, 15, n).clip(10, 100),
        'IC(mg/L)': np.random.normal(30, 10, n).clip(5, 60),
        'TC(mg/L)': np.random.normal(75, 20, n).clip(20, 150),
        'DO(mg/L)': np.random.normal(1.5, 1.0, n).clip(0.1, 5),
        'COD（mg/L)': np.random.normal(120, 40, n).clip(30, 250),
        '总氮（mg/L)': np.random.normal(25, 8, n).clip(5, 50),
        '铵态氮（mg/L)': np.random.normal(15, 5, n).clip(3, 30),
        '硝态氮（mg/L)': np.random.normal(5, 2, n).clip(1, 12),
        'pH': np.random.normal(7.2, 0.3, n).clip(6.5, 8.0),
        '液温': np.concatenate([np.random.normal(12, 2, 15), np.random.normal(18, 2, 15)]),
        '电导率(uS/cm)': np.random.normal(800, 200, n).clip(300, 1500),
        '固总碳（g/kg)': np.random.normal(15, 5, n).clip(3, 30),
        '有机碳（g/kg)': np.random.normal(8, 3, n).clip(1, 18),
        '无机碳（g/kg)': np.random.normal(7, 3, n).clip(1, 15),
    }
    # 制造相关性: DO-CH4负相关, TOC-CH4正相关
    data['CH4平均值'] = data['CH4平均值'] - np.array(data['DO(mg/L)']) * 3
    data['CH4平均值'] = data['CH4平均值'] + np.array(data['TOC（mg/L)']) * 0.2

    df = pd.DataFrame(data)
    filepath = os.path.join(output_dir, 'test_data.xlsx')

    # 写入两个sheet（冬季/春季），兼容DataLoader
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df[df['季节'] == '冬季'].to_excel(writer, sheet_name='冬季', index=False)
        df[df['季节'] == '春季'].to_excel(writer, sheet_name='春季', index=False)
        # 也写一个默认sheet方便其他模块直接读取
        df.to_excel(writer, sheet_name='全部', index=False)

    return filepath


def run_tests():
    """运行全部端到端测试"""
    print("=" * 60)
    print("  端到端集成测试")
    print("=" * 60)

    passed = 0
    failed = 0
    output_dir = tempfile.mkdtemp(prefix='academic_test_')

    def test(name, func):
        nonlocal passed, failed
        print(f"\n  [{name}]")
        try:
            result = func()
            print(f"    -> PASS")
            passed += 1
            return result
        except Exception as e:
            print(f"    -> FAIL: {e}")
            failed += 1
            return None

    # 1. 数据加载
    def t_data():
        from data_loader import DataLoader
        filepath = create_test_data(output_dir)
        # 用 file_path 参数指定具体文件
        loader = DataLoader(file_path=filepath)
        df = loader.load_data()
        assert len(df) > 0
        v = loader.validate_data()
        assert v['valid'], v['errors']
        print(f"    {df.shape[0]}行 x {df.shape[1]}列")
        return df
    df = test("数据加载+验证", t_data)

    # 2. 统计分析
    def t_stats():
        from statistical_analysis import StatisticalAnalyzer
        a = StatisticalAnalyzer(df)
        r = {}
        r['描述统计'] = a.descriptive_statistics()
        r['正态性检验'] = a.normality_test()
        r['组间比较'] = a.compare_groups()
        c, p = a.correlation_analysis(method='pearson')
        r['pearson相关'] = {'相关系数': c, 'p值': p}
        r['PCA'] = a.pca_analysis()
        print(f"    {list(r.keys())}")
        return r
    stats = test("统计分析", t_stats)

    # 3. 高级分析
    def t_adv():
        from advanced_analysis import CrossAnalyzer, AnomalyDeepDiver, DataStoryExtractor
        cr = CrossAnalyzer(df).analyze_all()
        an = AnomalyDeepDiver(df).analyze()
        st = DataStoryExtractor(stats).extract_stories()
        print(f"    交叉:{len(cr)} 异常:{len(an)} 故事:{len(st)}")
        return {'cross': cr, 'anomalies': an, 'stories': st}
    adv = test("高级分析", t_adv)

    # 4. 文献学习
    def t_lit():
        from literature_learner import LiteratureLearner
        l = LiteratureLearner()
        learning = l.learn_from_text(
            'TOC and CH4 correlated (r=0.68). This is due to substrate. '
            'Consistent with Guisasola (2008). Notably, DO negatively correlated with CH4.',
            title='Test'
        )
        print(f"    chains:{len(learning.logic_chains)} structures:{len(learning.paragraph_structures)}")
        return learning
    lit = test("文献学习", t_lit)

    # 5. 段落引擎
    def t_para():
        from paragraph_engine import ParagraphGenerator
        g = ParagraphGenerator('zh')
        p = g.generate_discussion_paragraph(
            finding='TOC与CH4正相关', r_value=0.68, p_value=0.01,
            mechanism='底物效应', literature_ref='Guisasola(2008)'
        )
        assert 'Guisasola' in p and '0.68' in p
        print(f"    {len(p)} chars")
        return p
    test("段落引擎", t_para)

    # 6. 引用安全
    def t_cite():
        from citation_guard import CitationGuard
        g = CitationGuard()
        k = g.assign_keys([{'title':'t','year':2020},{'title':'t2','year':2011}])
        r = g.validate_and_strip(f'good ({k[0]}) bad (ref-aabbccdd)')
        assert r.valid_citations == 1 and r.hallucinated_citations == 1
        b = g.export_bibtex()
        assert '@article' in b
        print(f"    valid:{r.valid_citations} hallucinated:{r.hallucinated_citations}")
    test("引用安全", t_cite)

    # 7. 写作优化
    def t_write():
        from writing_optimizer import polish_paper, check_grammar, translate
        r = polish_paper('本文搞清楚了溶解氧跟甲烷的关系。', 'zh')
        print(f"    润色:{len(r.changes)}处")
        return r
    test("写作优化", t_write)

    # 8. 期刊配置
    def t_journal():
        from paper_writing_agent import JournalConfig
        for k in ['EST','WR','STOTEN','中文核心','硕论']:
            c = JournalConfig(k)
            assert c.max_words > 0
        print(f"    5种期刊OK")
    test("期刊配置", t_journal)

    # 9. LaTeX导出
    def t_latex():
        from latex_exporter import LatexExporter
        e = LatexExporter(template='chinese_thesis')
        d = os.path.join(output_dir, 'latex')
        r = e.export(
            {'abstract':'测试','introduction':'引言','methods':'方法',
             'results':'结果','discussion':'讨论','conclusion':'结论'},
            [{'title':'T','authors':'A','year':2020}], d, title='测试'
        )
        assert os.path.exists(r['main_path']) and os.path.exists(r['bib_path'])
        print(f"    {r['main_path']}")
    test("LaTeX导出", t_latex)

    # 10. 大纲生成
    def t_outline():
        from paper_writing_agent import OutlineGenerator, ResearchDirection
        g = OutlineGenerator(analysis_results=stats, direction=ResearchDirection(topic='碳污染物'))
        o = g.generate('zh')
        assert 'introduction' in o and len(o['introduction']['tips']) > 0
        print(f"    {len(o)}章节")
    test("大纲生成", t_outline)

    # 11. 七句话测试
    def t_seven():
        from motivation_thread import SevenSentenceTest
        t = SevenSentenceTest()
        t.abstract_final = '碳污染物有显著相态分异'
        t.intro_contribution = '本研究系统分析了多相态碳污染物'
        t.discussion_closing = '溶解氧是控制碳转化的关键因素'
        r = t.validate()
        print(f"    passed:{r['passed']} checks:{len(r['checks'])}")
    test("七句话测试", t_seven)

    # 12. 推理矩阵
    def t_rationale():
        from writing_rationale import RationaleMatrix
        m = RationaleMatrix(paper_id='test')
        m.add(finding='DO与CH4负相关', mechanism='厌氧产甲烷', evidence='r=-0.72', section='discussion')
        v = m.validate()
        assert v['total'] == 1
        m.save()
        print(f"    {v['total']}行, 完整性:{v['avg_completeness']}")
    test("推理矩阵", t_rationale)

    # 清理
    shutil.rmtree(output_dir, ignore_errors=True)

    # 总结
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  结果: {passed}/{total} 通过")
    if failed == 0:
        print("  ALL TESTS PASSED!")
    else:
        print(f"  {failed} tests failed")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
