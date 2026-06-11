# -*- coding: utf-8 -*-
"""
Web 界面 — 上传数据 → 下载论文
================================
基于 Flask 的简单 Web UI，支持：
1. 上传 Excel 数据文件
2. 选择领域配置
3. 运行管线
4. 下载生成的论文（DOCX/LaTeX）

用法:
    pip install flask
    python web_app.py
    # 浏览器访问 http://localhost:5000
"""

import os
import sys
import uuid
import threading
from datetime import datetime

# 尝试导入 Flask
try:
    from flask import Flask, request, render_template_string, send_file, jsonify, redirect, url_for
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("Flask 未安装。请运行: pip install flask")
    print("或使用命令行模式: python test_full_pipeline.py")

app = Flask(__name__) if HAS_FLASK else None

# 运行状态存储
run_status = {}

# HTML 模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 学术论文写作系统</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
               background: #f5f5f5; color: #333; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { text-align: center; margin: 30px 0; color: #2c3e50; }
        .card { background: white; border-radius: 8px; padding: 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 600; color: #555; }
        input[type="file"], select { width: 100%; padding: 12px; border: 2px solid #ddd;
                border-radius: 6px; margin-bottom: 20px; font-size: 14px; }
        input[type="file"]:hover, select:hover { border-color: #3498db; }
        button { background: #3498db; color: white; border: none; padding: 14px 30px;
                 border-radius: 6px; cursor: pointer; font-size: 16px; width: 100%;
                 transition: background 0.3s; }
        button:hover { background: #2980b9; }
        button:disabled { background: #bdc3c7; cursor: not-allowed; }
        .status { margin-top: 20px; padding: 15px; border-radius: 6px; display: none; }
        .status.info { display: block; background: #e8f4fd; color: #2980b9; }
        .status.success { display: block; background: #d4edda; color: #155724; }
        .status.error { display: block; background: #f8d7da; color: #721c24; }
        .log { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 6px;
               font-family: monospace; font-size: 12px; max-height: 300px;
               overflow-y: auto; margin-top: 20px; white-space: pre-wrap; display: none; }
        .download-btn { display: inline-block; background: #27ae60; color: white;
                        padding: 10px 20px; border-radius: 6px; text-decoration: none;
                        margin: 5px; }
        .download-btn:hover { background: #219a52; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI 学术论文写作系统</h1>

        <div class="card">
            <form id="uploadForm" enctype="multipart/form-data">
                <label>1. 上传数据文件 (Excel)</label>
                <input type="file" name="datafile" accept=".xlsx,.xls" required>

                <label>2. 选择研究领域</label>
                <select name="domain">
                    <option value="sewer_carbon">污水管网碳排放</option>
                    <option value="water_quality">水质分析</option>
                    <option value="soil_pollution">土壤污染分析</option>
                    <option value="air_quality">大气环境分析</option>
                </select>

                <label>3. 论文语言</label>
                <select name="language">
                    <option value="zh">中文</option>
                    <option value="en">English</option>
                </select>

                <label>4. 论文标题（可选）</label>
                <input type="text" name="title" placeholder="留空则自动生成" style="padding:12px;border:2px solid #ddd;border-radius:6px;margin-bottom:20px;width:100%">

                <button type="submit" id="submitBtn">开始生成论文</button>
            </form>

            <div id="status" class="status"></div>
            <div id="log" class="log"></div>
            <div id="downloads" style="margin-top:20px;display:none">
                <h3>下载文件：</h3>
                <div id="downloadLinks"></div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const btn = document.getElementById('submitBtn');
            const status = document.getElementById('status');
            const log = document.getElementById('log');
            const downloads = document.getElementById('downloads');

            btn.disabled = true;
            btn.textContent = '正在上传...';
            status.className = 'status info';
            status.textContent = '正在上传数据文件...';
            log.style.display = 'block';
            log.textContent = '';
            downloads.style.display = 'none';

            try {
                const response = await fetch('/run', { method: 'POST', body: formData });
                const data = await response.json();

                if (data.run_id) {
                    status.textContent = '管线已启动，正在生成论文...';
                    pollStatus(data.run_id);
                } else {
                    status.className = 'status error';
                    status.textContent = '错误: ' + (data.error || '未知错误');
                    btn.disabled = false;
                    btn.textContent = '开始生成论文';
                }
            } catch(err) {
                status.className = 'status error';
                status.textContent = '上传失败: ' + err.message;
                btn.disabled = false;
                btn.textContent = '开始生成论文';
            }
        });

        async function pollStatus(run_id) {
            const status = document.getElementById('status');
            const log = document.getElementById('log');
            const btn = document.getElementById('submitBtn');
            const downloads = document.getElementById('downloads');
            const downloadLinks = document.getElementById('downloadLinks');

            while(true) {
                await new Promise(r => setTimeout(r, 3000));
                try {
                    const resp = await fetch('/status/' + run_id);
                    const data = await resp.json();

                    log.textContent = data.log || '';

                    if (data.status === 'done') {
                        status.className = 'status success';
                        status.textContent = '论文生成完成!';
                        btn.disabled = false;
                        btn.textContent = '开始生成论文';
                        if (data.files && data.files.length > 0) {
                            downloads.style.display = 'block';
                            downloadLinks.innerHTML = data.files.map(f =>
                                `<a class="download-btn" href="/download/${run_id}/${f}">${f}</a>`
                            ).join('');
                        }
                        break;
                    } else if (data.status === 'error') {
                        status.className = 'status error';
                        status.textContent = '生成失败: ' + (data.error || '未知错误');
                        btn.disabled = false;
                        btn.textContent = '开始生成论文';
                        break;
                    } else {
                        status.textContent = '正在生成... ' + (data.current_step || '');
                    }
                } catch(err) {
                    // 继续轮询
                }
            }
        }
    </script>
</body>
</html>
'''

if HAS_FLASK:
    @app.route('/')
    def index():
        return render_template_string(HTML_TEMPLATE)

    @app.route('/run', methods=['POST'])
    def run_pipeline():
        datafile = request.files.get('datafile')
        domain = request.form.get('domain', 'sewer_carbon')
        language = request.form.get('language', 'zh')
        title = request.form.get('title', '').strip() or None

        if not datafile:
            return jsonify({'error': '请上传数据文件'}), 400

        # 保存上传文件
        run_id = str(uuid.uuid4())[:8]
        run_dir = os.path.join('web_runs', run_id)
        os.makedirs(run_dir, exist_ok=True)
        data_path = os.path.join(run_dir, 'data.xlsx')
        datafile.save(data_path)

        # 启动后台任务
        run_status[run_id] = {
            'status': 'running',
            'log': '正在初始化...\n',
            'current_step': '',
            'files': [],
            'error': None,
        }

        thread = threading.Thread(
            target=_run_pipeline_thread,
            args=(run_id, data_path, domain, language, title, run_dir),
            daemon=True,
        )
        thread.start()

        return jsonify({'run_id': run_id})

    @app.route('/status/<run_id>')
    def get_status(run_id):
        status = run_status.get(run_id)
        if not status:
            return jsonify({'error': '未找到该运行'}), 404
        return jsonify(status)

    @app.route('/download/<run_id>/<filename>')
    def download_file(run_id, filename):
        run_dir = os.path.join('web_runs', run_id)
        filepath = os.path.join(run_dir, filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        return jsonify({'error': '文件不存在'}), 404

    def _run_pipeline_thread(run_id, data_path, domain, language, title, run_dir):
        """后台运行管线"""
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from paper_context import PaperContext, PaperOrchestrator

            ctx = PaperContext(
                data_path=data_path,
                output_dir=run_dir,
                language=language,
                domain=domain,
                title=title,
            )
            orch = PaperOrchestrator()

            # 捕获输出
            import io
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                orch.run(ctx)
            finally:
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout

            run_status[run_id]['log'] += output
            run_status[run_id]['status'] = 'done'

            # 收集输出文件
            files = []
            for f in os.listdir(run_dir):
                if f.endswith(('.docx', '.tex', '.md', '.pdf')):
                    files.append(f)
            run_status[run_id]['files'] = files

        except Exception as e:
            run_status[run_id]['status'] = 'error'
            run_status[run_id]['error'] = str(e)
            run_status[run_id]['log'] += f'\n\n错误: {e}\n'


def main():
    if not HAS_FLASK:
        print("请安装 Flask: pip install flask")
        print("或使用命令行模式: python test_full_pipeline.py")
        return

    print("=" * 50)
    print("  AI 学术论文写作系统 - Web 界面")
    print("  访问: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()
