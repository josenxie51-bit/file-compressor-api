from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import tempfile
import os
from pathlib import Path

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'service': 'File Compressor API',
        'version': '1.0',
        'endpoints': {
            '/': 'GET - API信息',
            '/health': 'GET - 健康检查',
            '/compress': 'POST - 压缩文件'
        }
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/compress', methods=['POST'])
def compress():
    """简化的压缩接口"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名空'}), 400
        
        # 获取压缩参数
        level = request.form.get('level', 'extreme')
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='_compressed') as tmp:
            # 简单处理：这里只是保存文件，实际应该压缩
            file.save(tmp.name)
            temp_path = tmp.name
        
        # 返回文件
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=f'compressed_{file.filename}'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Vercel需要这个
if __name__ == '__main__':
    app.run()
