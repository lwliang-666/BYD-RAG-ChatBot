"""
PDF 文档分块模块

负责将 PDF 文档解析为文本、提取标题信息，并按 token 数量
进行语义分块，支持分块间的重叠以保持上下文连贯性。
"""

from dataclasses import dataclass, field
from typing import Optional

import fitz
import tiktoken


@dataclass
class Chunk:
    """文本分块数据类，存储单个分块的内容及元信息"""
    content: str
    chunk_index: int
    page_number: int
    section_title: Optional[str] = None
    metadata: dict = field(default_factory=dict)


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """计算文本的 token 数量

    使用 tiktoken 库按指定编码模型计算。
    """
    enc = tiktoken.get_encoding(model)
    return len(enc.encode(text))


def extract_text_by_page(pdf_path: str) -> list[dict]:
    """按页提取 PDF 文档的文本内容

    返回每页的页码和文本，跳过空白页。
    """
    doc = fitz.open(pdf_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            pages.append({
                "page_number": page_num + 1,
                "text": text.strip(),
            })
    doc.close()
    return pages


def extract_headings_from_page(page) -> list[tuple[str, int]]:
    """从 PDF 页面中提取标题文本

    通过字体大小判断标题，字号 >= 14 的文本视为标题。
    返回 (标题文本, 字体大小) 的列表。
    """
    headings = []
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                font_size = span["size"]
                text = span["text"].strip()
                if not text:
                    continue
                # 字号 >= 14 视为标题
                if font_size >= 14:
                    headings.append((text, int(font_size)))
    return headings


def semantic_chunk_text(
    text: str,
    page_number: int,
    section_title: Optional[str] = None,
    max_tokens: int = 800,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """对单页文本按 token 数量进行分块

    当文本 token 数不超过 max_tokens 时直接返回单个分块；
    超过时按滑动窗口切分，相邻分块间保留 overlap_tokens 的重叠。
    """
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)

    # 文本较短时无需分块
    if len(tokens) <= max_tokens:
        return [Chunk(
            content=text,
            chunk_index=0,
            page_number=page_number,
            section_title=section_title,
        )]

    chunks = []
    start = 0
    chunk_idx = 0

    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)

        chunks.append(Chunk(
            content=chunk_text,
            chunk_index=chunk_idx,
            page_number=page_number,
            section_title=section_title,
        ))

        chunk_idx += 1
        # 非最后一块时，下一块起始位置回退 overlap_tokens 以保持上下文重叠
        start = end - overlap_tokens if end < len(tokens) else end

    return chunks


def chunk_pdf(
    pdf_path: str,
    max_tokens: int = 800,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """将 PDF 文档逐页解析并分块

    对每一页提取文本和标题，然后调用 semantic_chunk_text 进行分块，
    最终返回所有分块列表，分块索引全局递增。
    """
    doc = fitz.open(pdf_path)
    all_chunks = []
    global_chunk_idx = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if not text:
            continue

        # 提取页面标题作为分块的 section_title
        headings = extract_headings_from_page(page)
        section_title = headings[0][0] if headings else None

        page_chunks = semantic_chunk_text(
            text=text,
            page_number=page_num + 1,
            section_title=section_title,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )

        # 重新编号分块索引为全局递增
        for chunk in page_chunks:
            chunk.chunk_index = global_chunk_idx
            global_chunk_idx += 1
            all_chunks.append(chunk)

    doc.close()
    return all_chunks
