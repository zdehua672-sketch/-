# -*- coding: utf-8 -*-
"""
代理配置模块

使用方法:
1. 设置环境变量 HTTP_PROXY 和 HTTPS_PROXY
2. 或在此文件中直接配置代理地址

常见代理格式:
- HTTP代理: http://127.0.0.1:7890
- HTTPS代理: http://127.0.0.1:7890
- SOCKS5代理: socks5://127.0.0.1:1080
"""

import os

# ============================================================
# 代理配置（优先使用环境变量，其次使用此处配置）
# ============================================================

# 常见代理软件默认端口
# Clash: 7890
# V2Ray: 10809
# Shadowsocks: 1080
# SSR: 1080

# HTTP 代理地址（留空则不使用）
HTTP_PROXY = os.environ.get('HTTP_PROXY', '')

# HTTPS 代理地址（留空则不使用）
HTTPS_PROXY = os.environ.get('HTTPS_PROXY', '')

# ============================================================
# 常见代理配置示例（取消注释即可使用）
# ============================================================

# Clash 默认配置
# HTTP_PROXY = 'http://127.0.0.1:7890'
# HTTPS_PROXY = 'http://127.0.0.1:7890'

# V2Ray 默认配置
# HTTP_PROXY = 'http://127.0.0.1:10809'
# HTTPS_PROXY = 'http://127.0.0.1:10809'

# Shadowsocks 默认配置
# HTTP_PROXY = 'socks5://127.0.0.1:1080'
# HTTPS_PROXY = 'socks5://127.0.0.1:1080'

# ============================================================
# 代理验证
# ============================================================

def get_proxy_config():
    """获取代理配置"""
    config = {}
    if HTTP_PROXY:
        config['http'] = HTTP_PROXY
    if HTTPS_PROXY:
        config['https'] = HTTPS_PROXY
    return config


def set_proxy_env():
    """设置代理环境变量"""
    if HTTP_PROXY:
        os.environ['HTTP_PROXY'] = HTTP_PROXY
    if HTTPS_PROXY:
        os.environ['HTTPS_PROXY'] = HTTPS_PROXY


def test_proxy():
    """测试代理连接"""
    import urllib.request
    try:
        proxy_handler = urllib.request.ProxyHandler(get_proxy_config())
        opener = urllib.request.build_opener(proxy_handler)
        response = opener.open('http://httpbin.org/ip', timeout=10)
        result = response.read().decode('utf-8')
        print(f"代理测试成功: {result}")
        return True
    except Exception as e:
        print(f"代理测试失败: {e}")
        return False


if __name__ == '__main__':
    print("当前代理配置:")
    print(f"  HTTP_PROXY: {HTTP_PROXY or '未设置'}")
    print(f"  HTTPS_PROXY: {HTTPS_PROXY or '未设置'}")
    print()
    test_proxy()
