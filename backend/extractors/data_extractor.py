import re
from typing import Dict, List, Any, Optional


class DataExtractor:
    """数据提取器，用于从文档中提取和整理核心数据"""

    def __init__(self):
        # 可配置的关键词模式，用于识别重要数据
        self.patterns = {
            '合同编号': [r'合同编号[：:]\s*(\S+)', r'编号[：:]\s*(\S+)', r'Contract\s*No[.:]\s*(\S+)'],
            '合同名称': [r'合同名称[：:]\s*(.+?)(?:\n|$)', r'项目名称[：:]\s*(.+?)(?:\n|$)'],
            '甲方': [r'甲方[：:]\s*(.+?)(?:\n|$)', r'Party\s*A[：:]\s*(.+?)(?:\n|$)'],
            '乙方': [r'乙方[：:]\s*(.+?)(?:\n|$)', r'Party\s*B[：:]\s*(.+?)(?:\n|$)'],
            '金额': [r'金额[：:]\s*([0-9,，.]+)\s*元', r'总价[：:]\s*([0-9,，.]+)\s*元', r'Amount[：:]\s*([0-9,，.]+)'],
            '日期': [r'日期[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)', r'签订日期[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)'],
            '签订地点': [r'签订地点[：:]\s*(.+?)(?:\n|$)', r'地点[：:]\s*(.+?)(?:\n|$)'],
            '有效期': [r'有效期[：:]\s*(.+?)(?:\n|$)', r'期限[：:]\s*(.+?)(?:\n|$)'],
        }

    def extract_by_keywords(self, text: str) -> Dict[str, str]:
        """通过关键词提取数据"""
        extracted_data = {}

        for field_name, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_data[field_name] = match.group(1).strip()
                    break

        return extracted_data

    def extract_from_tables(self, tables: List[List[List[str]]]) -> List[Dict[str, Any]]:
        """从表格中提取数据"""
        table_data = []

        for table_idx, table in enumerate(tables):
            if not table or len(table) < 2:
                continue

            # 假设第一行是表头
            headers = table[0]
            for row in table[1:]:
                if len(row) == len(headers):
                    row_dict = dict(zip(headers, row))
                    row_dict['table_index'] = table_idx
                    table_data.append(row_dict)

        return table_data

    def extract_key_clauses(self, text: str) -> List[str]:
        """提取关键条款"""
        clauses = []

        # 查找以数字或标题开头的条款
        clause_patterns = [
            r'第[一二三四五六七八九十百]+条[：:]\s*(.+?)(?=第[一二三四五六七八九十百]+条|$)',
            r'\d+\.\s*(.+?)(?=\n\d+\.|$)',
            r'[（(]\d+[)）]\s*(.+?)(?=\n[（(]\d+[)）]|$)',
        ]

        for pattern in clause_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                clauses.extend([m.strip() for m in matches])
                break

        return clauses[:10]  # 返回前10个条款

    def process_document(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理文档并提取所有相关数据"""
        text = structured_data.get('text', '')

        # 提取关键词数据
        keyword_data = self.extract_by_keywords(text)

        # 提取表格数据
        tables = structured_data.get('tables', [])
        if not tables:
            tables = structured_data.get('sheets', {})
            if tables:
                tables = list(tables.values())

        table_data = self.extract_from_tables(tables)

        # 提取关键条款
        clauses = self.extract_key_clauses(text)

        return {
            'file_type': structured_data.get('file_type', 'unknown'),
            'keyword_data': keyword_data,
            'table_data': table_data,
            'key_clauses': clauses,
            'raw_text': text[:500]  # 保留前500字符作为预览
        }

    def add_custom_pattern(self, field_name: str, patterns: List[str]):
        """添加自定义提取模式"""
        self.patterns[field_name] = patterns

    def merge_data(self, documents_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个文档的数据"""
        merged = {
            'documents': [],
            'all_keyword_data': [],
            'all_table_data': [],
            'all_clauses': []
        }

        for doc_data in documents_data:
            merged['documents'].append({
                'file_type': doc_data.get('file_type'),
                'preview': doc_data.get('raw_text', '')
            })
            merged['all_keyword_data'].append(doc_data.get('keyword_data', {}))
            merged['all_table_data'].extend(doc_data.get('table_data', []))
            merged['all_clauses'].extend(doc_data.get('key_clauses', []))

        return merged
