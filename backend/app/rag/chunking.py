from dataclasses import dataclass, field
from typing import Optional

import fitz
import tiktoken


@dataclass
class Chunk:
    content: str
    chunk_index: int
    page_number: int
    section_title: Optional[str] = None
    metadata: dict = field(default_factory=dict)


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    enc = tiktoken.get_encoding(model)
    return len(enc.encode(text))


def extract_text_by_page(pdf_path: str) -> list[dict]:
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
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)

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
        start = end - overlap_tokens if end < len(tokens) else end

    return chunks


def chunk_pdf(
    pdf_path: str,
    max_tokens: int = 800,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    doc = fitz.open(pdf_path)
    all_chunks = []
    global_chunk_idx = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if not text:
            continue

        headings = extract_headings_from_page(page)
        section_title = headings[0][0] if headings else None

        page_chunks = semantic_chunk_text(
            text=text,
            page_number=page_num + 1,
            section_title=section_title,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        )

        for chunk in page_chunks:
            chunk.chunk_index = global_chunk_idx
            global_chunk_idx += 1
            all_chunks.append(chunk)

    doc.close()
    return all_chunks
