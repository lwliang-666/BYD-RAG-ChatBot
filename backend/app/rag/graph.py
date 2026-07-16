"""
RAG 检索增强生成图模块

基于 LangGraph 构建 RAG 流程，包含检索节点和生成节点。
提供流式 RAG 回答生成功能，将检索到的文档片段作为上下文
传递给 LLM 进行回答生成，并通过 SSE 事件流返回结果。
"""

import json
from typing import AsyncGenerator

import httpx
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from app.core.config import get_settings
from app.rag.retriever import search_similar
from app.rag.embedding import embed_query

settings = get_settings()

# 系统提示词模板，{context} 占位符在运行时替换为检索到的文档内容
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
    """LangGraph 状态定义，在检索和生成节点间传递数据"""
    query: str
    documents: list[dict]
    rewritten_query: str
    answer: str
    sources: list[dict]


async def retrieve_node(state: RAGState, db) -> RAGState:
    """检索节点：根据查询文本检索相似文档片段

    优先使用重写后的查询（rewritten_query），否则使用原始查询。
    """
    query = state.get("rewritten_query") or state["query"]
    documents = await search_similar(db, query)
    return {**state, "documents": documents}


async def generate_node(state: RAGState) -> AsyncGenerator[str, None]:
    """生成节点：基于检索到的文档内容流式生成回答

    将文档片段格式化为上下文后，调用 LLM 流式生成回答，
    最后输出引用来源信息。
    """
    documents = state["documents"]
    query = state["query"]

    # 将检索到的文档片段格式化为上下文文本
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

    # 流式生成回答并逐 token 输出
    full_answer = ""
    async for token in _stream_llm(messages):
        full_answer += token
        yield token

    # 回答结束后输出引用来源
    yield json.dumps({"sources": sources}, ensure_ascii=False)


async def _stream_llm(messages: list[dict]) -> AsyncGenerator[str, None]:
    """调用 LLM 的流式聊天接口，逐 token 返回生成内容

    使用 SSE 协议解析流式响应，提取每个 delta 中的 content 字段。
    """
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
                # 解析 SSE 数据行
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
    """流式生成 RAG 回答的完整流程

    流程：检索相似文档 -> 构建上下文 -> 调用 LLM 流式生成 -> 输出引用来源。
    支持传入聊天历史以保持多轮对话上下文，最近 6 条历史消息会被包含在请求中。
    输出格式为 SSE 事件流（token 事件和 sources 事件）。
    """
    import sys
    print(f"[DEBUG stream_rag_answer] 开始检索", file=sys.stderr, flush=True)
    documents = await search_similar(db, query)
    print(f"[DEBUG stream_rag_answer] 检索到 {len(documents)} 个文档", file=sys.stderr, flush=True)

    # 格式化检索结果为上下文文本
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

    # 构建消息列表：系统提示 + 聊天历史 + 当前查询
    messages = [{"role": "system", "content": system_msg}]

    if chat_history:
        # 仅保留最近 6 条历史消息，避免上下文过长
        messages.extend(chat_history[-6:])

    messages.append({"role": "user", "content": query})

    # 流式输出 token 事件
    print(f"[DEBUG stream_rag_answer] 开始流式生成", file=sys.stderr, flush=True)
    async for token in _stream_llm(messages):
        yield f"event: token\ndata: {json.dumps({'content': token}, ensure_ascii=False)}\n\n"

    # 输出引用来源事件
    print(f"[DEBUG stream_rag_answer] 流式生成完成，发送 sources", file=sys.stderr, flush=True)
    yield f"event: sources\ndata: {json.dumps({'chunks': sources}, ensure_ascii=False)}\n\n"
