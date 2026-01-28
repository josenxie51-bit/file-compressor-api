from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import tempfile
import os
from pathlib import Path
import logging
from werkzeug.utils import secure_filename
import subprocess
import zipfile
from PIL import Image
import io
import json
import time

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_timestamp():
    """获取当前时间戳"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def format_file_size(bytes):
    """格式化文件大小"""
    if bytes == 0:
        return "0 Bytes"
    k = 1024
    sizes = ["Bytes", "KB", "MB", "GB"]
    i = int(math.floor(math.log(bytes) / math.log(k)))
    return f"{bytes / math.pow(k, i):.2f} {sizes[i]}"

# 需要导入math模块
import math

@app.route('/')
def home():
    """API首页"""
    return jsonify({
        'status': 'online',
        'service': 'File Compressor API',
        'version': '1.0.0',
        'author': 'josenxie51-bit',
        'timestamp': get_timestamp(),
        'endpoints': {
            '/compress': 'POST - 压缩单个文件',
            '/health': 'GET - 健康检查',
            '/test': 'GET - 测试连接',
            '/': 'GET - API信息'
        },
        'features': {
            'supported_formats': ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.txt'],
            'compression_levels': ['extreme', 'high', 'normal'],
            'max_file_size': '50MB'
        }
    })

@app.route('/health')
def health():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': get_timestamp(),
        'service': 'file-compressor-api'
    })

@app.route('/test')
def test():
    """测试连接"""
    return jsonify({
        'message': '✅ API服务器正常运行！',
        'timestamp': get_timestamp(),
        'next_step': '使用 POST /compress 来压缩文件',
        'example_curl': 'curl -X POST -F "file=@yourfile.pdf" https://your-api.vercel.app/compress'
    })

@app.route('/compress', methods=['POST'])
def compress_file():
    """压缩文件API - 真正的强力压缩"""
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件', 'code': 400}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件', 'code': 400}), 400
        
        # 获取压缩参数
        level = request.form.get('level', 'extreme')
        target_size = int(request.form.get('target_size', 1))  # MB
        mode = request.form.get('mode', 'size')
        
        logger.info(f'📦 开始压缩文件: {file.filename}')
        logger.info(f'⚙️  压缩参数: 级别={level}, 目标大小={target_size}MB, 模式={mode}')
        
        # 验证文件类型
        if not is_supported_file(file.filename):
            return jsonify({
                'error': '不支持的文件格式',
                'supported_formats': ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.txt'],
                'your_file': file.filename,
                'code': 400
            }), 400
        
        # 检查文件大小（最大50MB）
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 50 * 1024 * 1024:  # 50MB
            return jsonify({
                'error': '文件太大',
                'max_size': '50MB',
                'your_file_size': format_file_size(file_size),
                'code': 400
            }), 400
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 保存上传的文件
            original_filename = secure_filename(file.filename)
            input_path = os.path.join(tmp_dir, original_filename)
            file.save(input_path)
            
            # 获取原始大小
            original_size = os.path.getsize(input_path)
            logger.info(f'📊 原始文件大小: {format_file_size(original_size)}')
            
            # 根据文件类型选择压缩方法
            output_path = compress_based_on_type(input_path, level, target_size, mode, tmp_dir)
            
            # 获取压缩后大小
            compressed_size = os.path.getsize(output_path)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            logger.info(f'✅ 压缩完成!')
            logger.info(f'📊 压缩后大小: {format_file_size(compressed_size)}')
            logger.info(f'📈 压缩率: {compression_ratio:.1f}%')
            
            # 返回压缩后的文件
            return send_file(
                output_path,
                as_attachment=True,
                download_name=f'compressed_{original_filename}',
                mimetype='application/octet-stream'
            )
            
    except Exception as e:
        logger.error(f'❌ 压缩失败: {str(e)}', exc_info=True)
        return jsonify({
            'error': f'压缩失败: {str(e)}',
            'code': 500,
            'timestamp': get_timestamp()
        }), 500

def is_supported_file(filename):
    """检查是否支持的文件格式"""
    supported_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.txt']
    file_ext = Path(filename).suffix.lower()
    return file_ext in supported_extensions

def compress_based_on_type(file_path, level, target_size_mb, mode, tmp_dir):
    """根据文件类型选择压缩方法"""
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext == '.pdf':
        return compress_pdf(file_path, level, target_size_mb, tmp_dir)
    elif file_ext in ['.jpg', '.jpeg', '.png']:
        return compress_image(file_path, level, target_size_mb, tmp_dir)
    elif file_ext in ['.doc', '.docx']:
        return compress_document(file_path, level, target_size_mb, tmp_dir)
    else:
        # 其他文件（如txt）使用文本压缩
        return compress_text(file_path, level, target_size_mb, tmp_dir)

def compress_pdf(file_path, level, target_size_mb, tmp_dir):
    """压缩PDF文件 - 使用真正的压缩算法"""
    output_path = os.path.join(tmp_dir, 'compressed.pdf')
    
    try:
        # 方法1：使用PyPDF2进行基本优化
        from PyPDF2 import PdfReader, PdfWriter
        
        reader = PdfReader(file_path)
        writer = PdfWriter()
        
        # 复制所有页面
        for page in reader.pages:
            writer.add_page(page)
        
        # 复制元数据
        if reader.metadata:
            writer.add_metadata(reader.metadata)
        
        # 写入压缩后的PDF
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        # 检查是否满足目标大小
        compressed_size = os.path.getsize(output_path)
        target_bytes = target_size_mb * 1024 * 1024
        
        if target_size_mb > 0 and compressed_size > target_bytes:
            logger.info(f'⚡ 需要更强制压缩，当前大小: {compressed_size/1024/1024:.2f}MB')
            # 使用图片转换进行极限压缩
            return compress_pdf_via_images(file_path, level, tmp_dir)
        
        return output_path
        
    except Exception as e:
        logger.warning(f'PyPDF2压缩失败，使用备用方案: {str(e)}')
        # 备用方案：使用图片转换
        return compress_pdf_via_images(file_path, level, tmp_dir)

def compress_pdf_via_images(file_path, level, tmp_dir):
    """通过图片转换进行PDF极限压缩"""
    try:
        # 导入必要的库
        from pdf2image import convert_from_path
        import img2pdf
        
        logger.info('🖼️  使用图片转换进行PDF极限压缩...')
        
        # 设置DPI（越低文件越小）
        dpi = 72 if level == 'extreme' else 96
        
        # 将PDF转换为图片
        images = convert_from_path(file_path, dpi=dpi)
        
        image_paths = []
        for i, image in enumerate(images):
            img_path = os.path.join(tmp_dir, f'page_{i}.jpg')
            
            # 设置图片质量
            quality = 30 if level == 'extreme' else 50
            
            # 转换为RGB并保存为JPEG
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            image.save(img_path, 'JPEG', quality=quality, optimize=True)
            image_paths.append(img_path)
        
        # 将图片转换回PDF
        output_path = os.path.join(tmp_dir, 'compressed_via_images.pdf')
        with open(output_path, 'wb') as f:
            f.write(img2pdf.convert(image_paths))
        
        return output_path
        
    except Exception as e:
        logger.error(f'图片转换压缩失败: {str(e)}')
        # 如果所有方法都失败，返回原文件
        import shutil
        output_path = os.path.join(tmp_dir, 'compressed_fallback.pdf')
        shutil.copy2(file_path, output_path)
        return output_path

def compress_image(file_path, level, target_size_mb, tmp_dir):
    """压缩图片文件 - 真正的图片压缩"""
    file_ext = Path(file_path).suffix.lower()
    output_path = os.path.join(tmp_dir, f'compressed{file_ext}')
    
    try:
        with Image.open(file_path) as img:
            # 获取原始尺寸
            original_width, original_height = img.size
            logger.info(f'🖼️  原始图片尺寸: {original_width}x{original_height}')
            
            # 根据压缩级别设置参数
            quality = get_quality_by_level(level)
            max_dimension = get_max_dimension_by_level(level)
            
            # 调整尺寸
            if max(img.size) > max_dimension:
                # 计算新尺寸
                ratio = max_dimension / max(img.size)
                new_width = int(img.width * ratio)
                new_height = int(img.height * ratio)
                
                # 调整尺寸
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f'📏 调整后尺寸: {new_width}x{new_height}')
            
            # 转换为RGB（如果需要）
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # 保存压缩后的图片
            if file_ext in ['.jpg', '.jpeg']:
                img.save(output_path, 'JPEG', quality=quality, optimize=True, progressive=True)
            elif file_ext == '.png':
                # PNG压缩
                img.save(output_path, 'PNG', optimize=True, compress_level=9)
            else:
                # 其他格式转为JPEG
                output_path = os.path.join(tmp_dir, 'compressed.jpg')
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
            
            logger.info(f'✅ 图片压缩完成，质量: {quality}%')
            
            # 如果指定了目标大小，尝试进一步压缩
            if target_size_mb > 0:
                current_size = os.path.getsize(output_path)
                target_bytes = target_size_mb * 1024 * 1024
                
                if current_size > target_bytes:
                    logger.info(f'⚡ 需要进一步压缩以达到目标大小')
                    return compress_image_to_target(output_path, target_bytes, quality)
            
            return output_path
            
    except Exception as e:
        logger.error(f'图片压缩失败: {str(e)}')
        # 如果失败，返回原文件
        import shutil
        shutil.copy2(file_path, output_path)
        return output_path

def compress_image_to_target(image_path, target_bytes, initial_quality):
    """压缩图片到目标大小"""
    quality = initial_quality
    max_iterations = 5  # 最多尝试5次
    
    for i in range(max_iterations):
        with Image.open(image_path) as img:
            # 逐步降低质量
            quality = max(10, quality - 15)  # 每次降低15%，最低10%
            
            # 保存为新文件
            temp_path = image_path.replace('.jpg', f'_temp_q{quality}.jpg')
            img.save(temp_path, 'JPEG', quality=quality, optimize=True)
            
            current_size = os.path.getsize(temp_path)
            
            # 检查文件大小
            if current_size <= target_bytes or quality <= 20:
                # 替换原文件
                import shutil
                shutil.move(temp_path, image_path)
                logger.info(f'🎯 达到目标大小，最终质量: {quality}%，大小: {format_file_size(current_size)}')
                return image_path
    
    return image_path

def compress_document(file_path, level, target_size_mb, tmp_dir):
    """压缩文档文件（Word等）"""
    file_ext = Path(file_path).suffix.lower()
    output_path = os.path.join(tmp_dir, f'compressed{file_ext}.zip')
    
    # 创建压缩包
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        zipf.write(file_path, os.path.basename(file_path))
    
    return output_path

def compress_text(file_path, level, target_size_mb, tmp_dir):
    """压缩文本文件"""
    output_path = os.path.join(tmp_dir, 'compressed.txt')
    
    try:
        # 读取文本文件
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 简单的文本压缩：移除多余空格和空行
        if level == 'extreme':
            # 极限压缩：移除所有多余空格和空行
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            compressed_content = ' '.join(lines)
        else:
            # 普通压缩：只压缩多余空格
            lines = content.splitlines()
            compressed_lines = []
            for line in lines:
                # 压缩多个空格为一个
                line = ' '.join(line.split())
                if line:  # 跳过空行
                    compressed_lines.append(line)
            compressed_content = '\n'.join(compressed_lines)
        
        # 写入压缩后的文本
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(compressed_content)
        
        logger.info(f'📝 文本压缩完成，原始行数: {len(content.splitlines())}, 压缩后: {len(compressed_content.splitlines())}')
        
        return output_path
        
    except Exception as e:
        logger.error(f'文本压缩失败: {str(e)}')
        # 如果失败，返回原文件
        import shutil
        shutil.copy2(file_path, output_path)
        return output_path

def get_quality_by_level(level):
    """根据压缩级别返回图片质量"""
    qualities = {
        'extreme': 40,   # 极限压缩：质量40%
        'high': 60,      # 强力压缩：质量60%
        'normal': 80     # 标准压缩：质量80%
    }
    return qualities.get(level, 60)

def get_max_dimension_by_level(level):
    """根据压缩级别返回最大图片尺寸"""
    dimensions = {
        'extreme': 1200,   # 极限压缩：最大1200px
        'high': 1600,      # 强力压缩：最大1600px
        'normal': 2000     # 标准压缩：最大2000px
    }
    return dimensions.get(level, 1600)

# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '接口不存在', 'code': 404}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': '请求方法不允许', 'code': 405}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误', 'code': 500}), 500

if __name__ == '__main__':
    # 用于本地测试
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
