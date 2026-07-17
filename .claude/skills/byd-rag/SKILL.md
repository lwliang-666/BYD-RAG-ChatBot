---
name: byd-rag
description: BYD-RAG-ChatBot RAG 管道的开发与调试指导。当用户涉及 PDF 分块策略、embedding 模型、向量检索、LLM 调用、Prompt 优化、检索质量调优等 RAG 相关工作时触发。也适用于 "RAG 不工作"、"检索无结果"、"回答质量差"、"embedding 报错"、"LLM 出错"、"SSE 断流"、"优化检索" 等场景。涵盖 chunking → embedding → retriever → graph 的完整管道，以及参数调优和效果评估。
---

# BYD-RAG-ChatBot RAG 管道开发与调试

## 管道架构

```
用户提问
  → Query Embedding (bge-large-zh-v1.5, 1024维)
    → pgvector 相似度检索 (HNSW, cosine)
      → Top-K 文档块 (默认5条)
        → Prompt 组装 + 历史消息 (最近6条)
          → 讯飞星火 LLM 流式生成
            → SSE 流式响应
```

**核心文件**:
- `backend/app/rag/chunking.py` — PDF 解析与语义分块
- `backend/app/rag/embedding.py` — 文本向量化
- `backend/app/rag/retriever.py` — 向量存储与检索
- `backend/app/rag/graph.py` — RAG 流程编排 + SYSTEM_PROMPT

## 诊断清单

### Step 1: 检查 Embedding 模型

查看后端启动日志：
- `Embedding 模型加载完成` → 正常
- `Embedding 模型加载失败，将使用 API 方式` → 降级为 API 调用

本地模型缓存位置: `~/.cache/huggingface/hub/`

国内下载镜像:
```bash
HF_ENDPOINT=https://hf-mirror.com python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-zh-v1.5')"
```

### Step 2: 检查向量库数据

```bash
PGPASSWORD=password psql -h localhost -U postgres -d byd_rag -c "SELECT COUNT(*) FROM document_chunks;"
```

如果为 0，执行 `make ingest` 入库 PDF。

### Step 3: 检查检索质量

低相似度（< 0.5）通常意味着查询与文档内容不匹配，或分块粒度不合适。

### Step 4: 检查 LLM 连接

确认 `XFXC_API_KEY` 环境变量已设置。查看后端日志中 `stream_rag_answer` 相关 DEBUG 输出。

### Step 5: 检查 SSE 流

使用 curl 直接测试：
```bash
curl -N -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -X POST http://localhost:8000/api/chat/conversations/<id>/messages \
  -d '{"content":"驱逐舰05的续航是多少"}'
```

## 关键参数

| 参数 | 默认值 | 位置 | 说明 |
|------|--------|------|------|
| `RAG_TOP_K` | 5 | config.py / .env | 检索返回的文档块数量 |
| `CHUNK_MAX_TOKENS` | 800 | config.py / .env | 单个分块最大 token 数 |
| `CHUNK_OVERLAP_TOKENS` | 50 | config.py / .env | 相邻分块重叠 token 数 |
| `EMBEDDING_BATCH_SIZE` | 64 | config.py / .env | 批量嵌入的批次大小 |
| `EMBEDDING_DIMENSION` | 1024 | config.py / .env | 向量维度 |
| 温度参数 | 0.7 | graph.py `_stream_llm` | LLM 生成随机性 |
| `max_tokens` | 2048 | graph.py `_stream_llm` | LLM 最大输出长度 |
| 历史消息数 | 6 | graph.py `stream_rag_answer` | 传入 LLM 的历史消息条数 |

## SYSTEM_PROMPT 模板

位于 `backend/app/rag/graph.py`，核心规则：
1. 仅根据检索到的文档内容回答，不编造
2. 文档无相关信息时明确说明
3. 标注引用来源（页码）
4. 技术参数准确引用原文
5. 中文回答，条理清晰

## 重新入库

修改分块参数后需要重新入库：

```bash
# 1. 清空现有文档块
PGPASSWORD=password psql -h localhost -U postgres -d byd_rag -c "DELETE FROM document_chunks;"

# 2. 重新入库
make ingest
```

ingest 脚本有去重保护：如果文档块已存在则跳过，所以必须先清空。

## 调优方向

| 问题 | 调整方向 |
|------|----------|
| 检索不到相关内容 | 增大 `RAG_TOP_K`，减小 `CHUNK_MAX_TOKENS` |
| 回答包含无关信息 | 减小 `RAG_TOP_K`，优化 SYSTEM_PROMPT |
| 回答过于简略 | 增大 `max_tokens`，调整温度 |
| 上下文丢失 | 增大 `CHUNK_OVERLAP_TOKENS`，增大历史消息数 |
| 多轮对话遗忘 | 检查 chat_history 是否正确传入 |
| LLM 编造内容 | 强化 SYSTEM_PROMPT 约束，降低温度 |
