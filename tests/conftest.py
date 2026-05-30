"""Pytest 配置 - 共享 fixtures"""
import sys
import os
import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pytest_configure(config):
    """注册自定义marker"""
    config.addinivalue_line("markers", "plotting: 需要matplotlib的测试（可能在Windows上有I/O问题）")
    # 设置matplotlib后端
    import matplotlib
    matplotlib.use('Agg')


@pytest.fixture(autouse=True)
def _restore_stdout(request):
    """修复matplotlib关闭stdout导致的I/O错误"""
    import io
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    yield
    if sys.stdout.closed:
        sys.stdout = original_stdout
    if sys.stderr.closed:
        sys.stderr = original_stderr
