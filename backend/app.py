from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from parsers import PDFParser, WordParser, ExcelParser
from extractors import DataExtractor
from output import ExcelWriter

app = Flask(__name__)
CORS(app)

# 配置
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output_files'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'xlsx', 'xls'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_parser(file_path, file_ext):
    """根据文件扩展名选择合适的解析器"""
    if file_ext == 'pdf':
        return PDFParser(file_path)
    elif file_ext in ['doc', 'docx']:
        return WordParser(file_path)
    elif file_ext in ['xls', 'xlsx']:
        return ExcelParser(file_path)
    else:
        raise ValueError(f"不支持的文件类型: {file_ext}")


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'ok', 'message': '服务运行正常'})


@app.route('/api/upload', methods=['POST'])
def upload_files():
    """文件上传和处理接口"""
    try:
        # 检查是否有文件
        if 'files' not in request.files:
            return jsonify({'error': '没有文件上传'}), 400

        files = request.files.getlist('files')

        if len(files) == 0:
            return jsonify({'error': '没有选择文件'}), 400

        uploaded_files = []
        documents_data = []

        # 处理每个上传的文件
        for file in files:
            if file.filename == '':
                continue

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_ext = filename.rsplit('.', 1)[1].lower()
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                # 保存文件
                file.save(file_path)
                uploaded_files.append(filename)

                try:
                    # 解析文档
                    parser = get_parser(file_path, file_ext)
                    structured_data = parser.extract_structured_data()

                    # 提取数据
                    extractor = DataExtractor()
                    processed_data = extractor.process_document(structured_data)
                    documents_data.append(processed_data)

                except Exception as e:
                    # 清理已上传的文件
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return jsonify({'error': f'解析文件 {filename} 时出错: {str(e)}'}), 500
            else:
                return jsonify({'error': f'不支持的文件类型: {file.filename}'}), 400

        if len(documents_data) == 0:
            return jsonify({'error': '没有成功处理的文件'}), 400

        # 合并所有文档的数据
        extractor = DataExtractor()
        merged_data = extractor.merge_data(documents_data)

        # 生成Excel文件
        excel_writer = ExcelWriter()
        output_file = excel_writer.save(merged_data)

        # 清理上传的文件
        for filename in uploaded_files:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)

        return jsonify({
            'success': True,
            'message': f'成功处理 {len(documents_data)} 个文件',
            'output_file': os.path.basename(output_file),
            'data_summary': {
                'documents_count': len(merged_data['documents']),
                'keywords_extracted': len(merged_data['all_keyword_data']),
                'table_rows': len(merged_data['all_table_data']),
                'clauses_found': len(merged_data['all_clauses'])
            }
        })

    except Exception as e:
        return jsonify({'error': f'处理请求时出错: {str(e)}'}), 500


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """下载生成的Excel文件"""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': f'下载文件时出错: {str(e)}'}), 500


@app.route('/api/files', methods=['GET'])
def list_files():
    """列出所有生成的Excel文件"""
    try:
        files = []
        for filename in os.listdir(app.config['OUTPUT_FOLDER']):
            if filename.endswith('.xlsx'):
                file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
                file_stat = os.stat(file_path)
                files.append({
                    'filename': filename,
                    'size': file_stat.st_size,
                    'created_at': file_stat.st_ctime
                })

        files.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': f'获取文件列表时出错: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
