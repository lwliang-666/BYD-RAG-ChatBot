import json
from typing import AsyncGenerator

import httpx
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from app.core.config import get_settings
from app.rag.retriever import search_similar
from app.rag.embedding import embed_query

settings = get_settings()

SYSTEM_PROMPT = """你是比亚迪技术文档的专业问答助手，专注于比亚迪 驱逐舰05 相关技术问题解答。

请严格遵守以下规则：
1. 仅根据下方检索到的文档内容回答用户问题，不要编造或推测内容
2. 如果文档中没有足够信息回答问题，请明确说明"根据现有文档无法回答该问题"
3. 回答时请标注引用来源（如：根据第X页的内容...）
4. 对于技术参数、操作步骤等内容，请准确引用文档原文
5. 回答使用中文，条理清晰，必要时使用编号或分段

检索到的文档内容:
{context}"""


class RAGState(TypedDict):
    query: str
    documents: list[dict]
    rewritten_query: str
    answer: str
    sources: list[dict]


async def retrieve_node(state: RAGState, db) -> RAGState:
    query = state.get("rewritten_query") or state["query"]
    documents = await search_similar(db, query)
    return {**state, "documents": documents}


async def generate_node(state: RAGState) -> AsyncGenerator[str, None]:
    documents = state["documents"]
    query = state["query"]

    context_parts = []
    sources = []
    for doc in documents:
        page = doc.get("metadata", {}).get("page_number", "未知")
        context_parts.append(f"[第{page}页] {doc['content']}")
        sources.append({
            "content": doc["content"][:200],
            "metadata": doc.get("metadata", {}),
            "similarity": doc.get("similarity", 0),
        })

    context = "\n\n".join(context_parts)
    system_msg = SYSTEM_PROMPT.format(context=context)

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": query},
    ]

    full_answer = ""
    async for token in _stream_llm(messages):
        full_answer += token
        yield token

    yield json.dumps({"sources": sources}, ensure_ascii=False)


async def _stream_llm(messages: list[dict]) -> AsyncGenerator[str, None]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{settings.LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.LLM_MODEL_ID,
                "messages": messages,
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 2048,
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue


async def stream_rag_answer(query: str, db, chat_history: list[dict] | None = None) -> AsyncGenerator[str, None]:
    documents = await search_similar(db, query)

    context_parts = []
    sources = []
    for doc in documents:
        page = doc.get("metadata", {}).get("page_number", "未知")
        context_parts.append(f"[第{page}页] {doc['content']}")
        sources.append({
            "content": doc["content"][:200],
            "metadata": doc.get("metadata", {}),
            "similarity": doc.get("similarity", 0),
        })

    context = "\n\n".join(context_parts)
    system_msg = SYSTEM_PROMPT.format(context=context)

    messages = [{"role": "system", "content": system_msg}]

    if chat_history:
        messages.extend(chat_history[-6:])

    messages.append({"role": "user", "content": query})

    async for token in _stream_llm(messages):
        yield f"event: token\ndata: {json.dumps({'content': token}, ensure_ascii=False)}\n\n"

    yield f"event: sources\ndata: {json.dumps({'chunks': sources}, ensure_ascii=False)}\n\n"
    yield "event: done\ndata: {}\n\n"
