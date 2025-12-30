import pdfplumber
import re
from typing import Dict, List, Any


class PDFParser:
    """PDF文档解析器"""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def extract_text(self) -> str:
        """提取PDF中的所有文本"""
        text = ""
        try:
            with pdfplumber.open(self.file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            raise Exception(f"PDF解析错误: {str(e)}")
        return text

    def extract_tables(self) -> List[List[List[str]]]:
        """提取PDF中的所有表格"""
        tables = []
        try:
            with pdfplumber.open(self.file_path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
        except Exception as e:
            raise Exception(f"PDF表格提取错误: {str(e)}")
        return tables

    def extract_structured_data(self) -> Dict[str, Any]:
        """提取结构化数据"""
        text = self.extract_text()
        tables = self.extract_tables()

        return {
            'text': text,
            'tables': tables,
            'file_type': 'pdf'
        }
