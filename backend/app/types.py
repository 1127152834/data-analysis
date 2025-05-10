import enum  # 导入枚举模块


class MimeTypes(str, enum.Enum):
    """
    定义支持的文件MIME类型枚举

    这些类型用于标识不同格式的文档，用于文档处理和索引
    """

    PLAIN_TXT = "text/plain"  # 纯文本文件
    MARKDOWN = "text/markdown"  # Markdown格式文件
    PDF = "application/pdf"  # PDF文档
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # Word文档
    PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"  # PowerPoint演示文稿
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  # Excel电子表格
    CSV = "text/csv"  # CSV格式文件
