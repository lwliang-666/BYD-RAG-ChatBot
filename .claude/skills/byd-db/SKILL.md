---
name: byd-db
description: BYD-RAG-ChatBot 数据库操作指导。当用户需要查询数据库、修改表结构、调试数据问题、重置数据库、查看 document_chunks 数据、检查用户数据等数据库相关操作时触发。也适用于 "查看数据库"、"查询用户"、"文档块数量"、"重置数据库"、"清空数据"、"psql"、"pgvector" 等场景。涵盖 PolarDB-PG + pgvector 的连接、表结构、索引设计和常用查询。
---

# BYD-RAG-ChatBot 数据库操作

## 连接信息

| 项目 | 值 |
|------|-----|
| 主机 | localhost |
| 端口 | 5432 |
| 用户 | postgres |
| 密码 | password |
| 数据库 | byd_rag |
| 容器名 | byd_rag_polardb |

快速连接：
```bash
PGPASSWORD=password psql -h localhost -U postgres -d byd_rag
```

或进入容器：
```bash
docker exec -it byd_rag_polardb psql -U postgres -d byd_rag
```

## 表结构

### users — 用户表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| username | VARCHAR(50) | 用户名（部分唯一索引） |
| display_name | VARCHAR(50) | 显示名称 |
| password_hash | VARCHAR(255) | 密码哈希 |
| avatar_url | VARCHAR(500) | 头像路径 |
| is_deleted | BOOLEAN | 逻辑删除标记 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**部分唯一索引**: `ix_users_username_active` — 仅在 `is_deleted = FALSE` 时保证用户名唯一

### conversations — 对话表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 所属用户 (FK → users.id) |
| title | VARCHAR(200) | 对话标题 |
| is_pinned | BOOLEAN | 是否置顶 |
| is_deleted | BOOLEAN | 逻辑删除标记 |
| created_at / updated_at | TIMESTAMP | 时间戳 |

### messages — 消息表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| conversation_id | UUID | 所属对话 (FK → conversations.id) |
| role | VARCHAR(20) | user / assistant / system |
| content | TEXT | 消息内容 |
| sources | JSONB | RAG 检索来源 |
| created_at | TIMESTAMP | 创建时间 |

### document_chunks — 文档块表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| document_name | VARCHAR(200) | 源文档名称 |
| chunk_index | INTEGER | 块序号 |
| content | TEXT | 文本内容 |
| embedding | VECTOR(1024) | 向量 (bge-large-zh-v1.5) |
| metadata | JSONB | 元数据 (页码/章节) |
| created_at | TIMESTAMP | 创建时间 |

## pgvector 索引

- 向量维度: 1024 (bge-large-zh-v1.5)
- 索引类型: HNSW
- 距离度量: cosine similarity (`<=>` 操作符)
- 索引参数: `m = 16, ef_construction = 64`

检查索引是否存在：
```sql
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'document_chunks';
```

如索引缺失，手动创建：
```sql
CREATE INDEX idx_document_chunks_embedding
ON document_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

## 常用查询

```sql
-- 文档块总数
SELECT COUNT(*) FROM document_chunks;

-- 按文档统计块数
SELECT document_name, COUNT(*) FROM document_chunks GROUP BY document_name;

-- 查看活跃用户
SELECT id, username, display_name, created_at FROM users WHERE is_deleted = FALSE;

-- 用户对话统计
SELECT u.username, COUNT(c.id) AS conv_count
FROM users u LEFT JOIN conversations c ON u.id = c.user_id AND c.is_deleted = FALSE
WHERE u.is_deleted = FALSE
GROUP BY u.username;

-- 最近消息
SELECT id, role, LEFT(content, 50) AS preview, created_at
FROM messages ORDER BY created_at DESC LIMIT 10;

-- 查看某对话的完整消息
SELECT role, content, sources FROM messages
WHERE conversation_id = '<uuid>' ORDER BY created_at;

-- 向量检索测试（需提供查询向量）
SELECT id, document_name, LEFT(content, 100),
  1 - (embedding <=> '<query_vector>'::vector) AS similarity
FROM document_chunks
ORDER BY embedding <=> '<query_vector>'::vector
LIMIT 5;
```

## Docker 容器管理

```bash
# 启动
cd docker && docker compose up -d

# 停止
cd docker && docker compose down

# 重置（删除所有数据）
cd docker && docker compose down -v && docker compose up -d

# 查看状态
docker ps --filter name=byd_rag_polardb

# 查看日志
docker logs byd_rag_polardb
```

## 数据重置场景

| 级别 | 操作 | 命令 |
|------|------|------|
| 仅清空文档块 | 重新入库 | `DELETE FROM document_chunks;` 然后 `make ingest` |
| 清空用户数据 | 保留表结构 | `DELETE FROM messages; DELETE FROM conversations; DELETE FROM users;` |
| 完全重置 | 重建所有 | `make db-reset` |

## SQLAlchemy 模型映射

| SQL 表 | ORM 模型 | 文件 |
|--------|----------|------|
| users | User | backend/app/models/user.py |
| conversations | Conversation | backend/app/models/chat.py |
| messages | Message | backend/app/models/chat.py |
| document_chunks | DocumentChunk | backend/app/models/document.py |

**注意**: `DocumentChunk.metadata_` 在 Python 中带下划线后缀，映射到 SQL 列名 `metadata`（避免与 SQLAlchemy 保留字冲突）。
