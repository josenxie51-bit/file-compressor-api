from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import tempfile
import os
from pathlib import Path
import logging
from werkzeug.utils import secure_filename
from PIL import Image
import zipfile
import math

app = Flask(__name__)
CORS(app, origins="*")  # 允许所有来源

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_timestamp():
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def format_file_size(bytes):
    """格式化文件大小"""
    if bytes == 0:
        return "0 Bytes"
    k = 1024
    sizes = ["Bytes", "KB", "MB", "GB"]
    i = int(math.floor(math.log(bytes) / math.log(k)))
    return f"{bytes / math.pow(k, i):.2f} {sizes[i]}"

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'service': 'Ultimate File Compressor API',
        'version': '2.0',
        'features': '极限压缩模式，10MB压到1MB'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/compress', methods=['POST'])
def compress_file():
    """极限压缩API"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 获取压缩参数
        level = request.form.get('level', 'extreme')
        target_size = int(request.form.get('target_size', 1))  # MB
        mode = request.form.get('mode', 'size')
        
        logger.info(f'开始极限压缩: {file.filename}, 级别: {level}')
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 保存上传的文件
            original_filename = secure_filename(file.filename)
            input_path = os.path.join(tmp_dir, original_filename)
            file.save(input_path)
            
            original_size = os.path.getsize(input_path)
            logger.info(f'原始大小: {format_file_size(original_size)}')
            
            # 根据文件类型选择压缩方法
            file_ext = Path(input_path).suffix.lower()
            
            if file_ext == '.pdf':
                output_path = compress_pdf_extreme(input_path, level, target_size, tmp_dir)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                output_path = compress_image_extreme(input_path, level, target_size, tmp_dir)
            elif file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
                output_path = compress_document_extreme(input_path, level, target_size, tmp_dir)
            else:
                output_path = compress_generic_extreme(input_path, level, target_size, tmp_dir)
            
            # 获取压缩后大小
            compressed_size = os.path.getsize(output_path)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            logger.info(f'✅ 压缩完成!')
            logger.info(f'压缩后大小: {format_file_size(compressed_size)}')
            logger.info(f'压缩率: {compression_ratio:.1f}%')
            
            # 返回压缩后的文件
            return send_file(
                output_path,
                as_attachment=True,
                download_name=f'compressed_{original_filename}',
                mimetype='application/octet-stream'
            )
            
    except Exception as e:
        logger.error(f'压缩失败: {str(e)}', exc_info=True)
        return jsonify({'error': f'压缩失败: {str(e)}'}), 500

def compress_pdf_extreme(file_path, level, target_size_mb, tmp_dir):
    """PDF极限压缩"""
    output_path = os.path.join(tmp_dir, 'compressed.pdf')
    
    try:
        # 方法1：尝试使用PyPDF2
        try:
            from PyPDF2 import PdfReader, PdfWriter
            
            reader = PdfReader(file_path)
            writer = PdfWriter()
            
            # 复制所有页面
            for page in reader.pages:
                writer.add_page(page)
            
            # 写入文件
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            logger.info('使用PyPDF2压缩PDF')
            
        except ImportError:
            logger.warning('PyPDF2未安装，使用备用方案')
            import shutil
            shutil.copy2(file_path, output_path)
        
        # 检查是否达到目标大小
        compressed_size = os.path.getsize(output_path)
        target_bytes = target_size_mb * 1024 * 1024
        
        if target_size_mb > 0 and compressed_size > target_bytes:
            logger.info(f'需要更强制压缩，当前大小: {compressed_size/1024/1024:.2f}MB')
            
            # 方法2：转换为图片再转回PDF（极限压缩）
            try:
                from pdf2image import convert_from_path
                import img2pdf
                
                logger.info('使用图片转换进行PDF极限压缩...')
                
                # 设置极低DPI
                dpi = 72
                if level == 'extreme':
                    dpi = 50  # 极限压缩用50DPI
                
                # 将PDF转换为图片
                images = convert_from_path(file_path, dpi=dpi)
                
                image_paths = []
                for i, image in enumerate(images):
                    img_path = os.path.join(tmp_dir, f'page_{i}.jpg')
                    
                    # 极低质量
                    quality = 20 if level == 'extreme' else 40
                    
                    # 转换为RGB
                    if image.mode in ('RGBA', 'LA', 'P'):
                        image = image.convert('RGB')
                    
                    # 调整尺寸（如果需要）
                    max_width = 800 if level == 'extreme' else 1200
                    if image.width > max_width:
                        ratio = max_width / image.width
                        new_height = int(image.height * ratio)
                        image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 保存为极低质量JPEG
                    image.save(img_path, 'JPEG', quality=quality, optimize=True, progressive=True)
                    image_paths.append(img_path)
                
                # 将图片转换回PDF
                pdf_output = os.path.join(tmp_dir, 'compressed_via_images.pdf')
                with open(pdf_output, 'wb') as f:
                    f.write(img2pdf.convert(image_paths))
                
                # 检查最终大小
                final_size = os.path.getsize(pdf_output)
                if final_size < compressed_size:
                    output_path = pdf_output
                    logger.info(f'图片转换压缩成功，最终大小: {final_size/1024/1024:.2f}MB')
                    
            except Exception as img_error:
                logger.warning(f'图片转换失败: {img_error}')
        
        return output_path
        
    except Exception as e:
        logger.error(f'PDF压缩失败: {str(e)}')
        import shutil
        shutil.copy2(file_path, output_path)
        return output_path

def compress_image_extreme(file_path, level, target_size_mb, tmp_dir):
    """图片极限压缩"""
    file_ext = Path(file_path).suffix.lower()
    output_path = os.path.join(tmp_dir, f'compressed{file_ext}')
    
    try:
        with Image.open(file_path) as img:
            # 原始信息
            original_width, original_height = img.size
            logger.info(f'原始图片尺寸: {original_width}x{original_height}')
            
            # 根据压缩级别设置参数
            if level == 'extreme':
                quality = 15     # 极限压缩：15%质量
                max_width = 800  # 最大宽度800px
                format = 'JPEG'  # 强制转为JPEG
            elif level == 'high':
                quality = 40     # 强力压缩：40%质量
                max_width = 1200 # 最大宽度1200px
                format = 'JPEG'
            else:
                quality = 60     # 标准压缩：60%质量
                max_width = 1600 # 最大宽度1600px
                format = 'JPEG' if file_ext in ['.jpg', '.jpeg'] else img.format
            
            # 调整尺寸
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f'调整后尺寸: {max_width}x{new_height}')
            
            # 转换为RGB（如果需要）
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
                output_path = output_path.replace(file_ext, '.jpg')
            
            # 保存压缩后的图片
            if format == 'JPEG':
                img.save(output_path, 'JPEG', 
                        quality=quality, 
                        optimize=True, 
                        progressive=True)
            else:
                img.save(output_path, format, optimize=True)
            
            logger.info(f'图片压缩完成，质量: {quality}%')
            
            # 如果指定了目标大小，尝试进一步压缩
            if target_size_mb > 0:
                current_size = os.path.getsize(output_path)
                target_bytes = target_size_mb * 1024 * 1024
                
                # 逐步降低质量直到达到目标
                while current_size > target_bytes and quality > 10:
                    quality = max(5, quality - 10)  # 每次降低10%，最低5%
                    
                    with Image.open(output_path) as temp_img:
                        temp_output = output_path.replace('.jpg', f'_q{quality}.jpg')
                        temp_img.save(temp_output, 'JPEG', 
                                    quality=quality, 
                                    optimize=True)
                    
                    new_size = os.path.getsize(temp_output)
                    if new_size < current_size:
                        import shutil
                        shutil.move(temp_output, output_path)
                        current_size = new_size
                        logger.info(f'进一步压缩到质量 {quality}%，大小: {current_size/1024/1024:.2f}MB')
                    else:
                        os.remove(temp_output)
                        break
            
            return output_path
            
    except Exception as e:
        logger.error(f'图片压缩失败: {str(e)}')
        import shutil
        shutil.copy2(file_path, output_path)
        return output_path

def compress_document_extreme(file_path, level, target_size_mb, tmp_dir):
    """文档极限压缩"""
    output_path = os.path.join(tmp_dir, 'compressed.zip')
    
    # 使用最高压缩级别
    compression = zipfile.ZIP_DEFLATED
    compresslevel = 9  # 最高压缩级别
    
    with zipfile.ZipFile(output_path, 'w', compression, compresslevel=compresslevel) as zipf:
        zipf.write(file_path, os.path.basename(file_path))
    
    return output_path

def compress_generic_extreme(file_path, level, target_size_mb, tmp_dir):
    """通用文件极限压缩"""
    output_path = os.path.join(tmp_dir, 'compressed.zip')
    
    # 使用最高压缩级别
    compression = zipfile.ZIP_DEFLATED
    compresslevel = 9
    
    with zipfile.ZipFile(output_path, 'w', compression, compresslevel=compresslevel) as zipf:
        zipf.write(file_path, os.path.basename(file_path))
    
    return output_path

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
