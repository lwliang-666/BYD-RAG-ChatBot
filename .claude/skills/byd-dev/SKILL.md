---
name: byd-dev
description: 管理 BYD-RAG-ChatBot 项目的开发环境。当用户提到启动服务、停止服务、环境配置、数据库操作、PDF 入库、make 命令、开发环境、端口 5173/8000/5432、运行项目等开发运维操作时触发。包括 make dev/db/backend/frontend/ingest/db-reset 等命令的使用指导、服务依赖关系、端口配置和环境变量说明。
---

# BYD-RAG-ChatBot 开发环境管理

## 服务架构

```
浏览器 (localhost:5173)
  → Vite 开发服务器 (端口 5173)
    → 代理 /api/* 和 /uploads/* 到
      → FastAPI 后端 (端口 8000)
        → PolarDB-PG 数据库 (端口 5432, Docker)
        → 讯飞星火 LLM API (外部服务)
        → 本地 SentenceTransformer 模型 (bge-large-zh-v1.5)
```

**依赖链**: 数据库 → 后端 → 前端，必须按顺序启动。

## 启动步骤

### 首次搭建

```bash
# 1. 安装依赖
make install

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，设置 LLM_API_KEY 或确保系统环境变量 XFXC_API_KEY 已设置

# 3. 启动数据库
make db

# 4. 等待数据库就绪（约 30 秒），然后入库 PDF 文档
make ingest

# 5. 启动全部服务
make dev
```

### 日常开发

```bash
make dev        # 一键启动：数据库 + 后端(后台) + 前端(前台)
```

或分别启动：

```bash
make db         # 启动 PolarDB-PG 数据库 (Docker)
make backend    # 启动 FastAPI 后端 (uvicorn --reload, 端口 8000)
make frontend   # 启动 Vite 前端 (端口 5173)
```

## Makefile 目标速查

| 目标 | 命令 | 说明 |
|------|------|------|
| `make install` | pip install + pnpm install | 安装所有依赖 |
| `make db` | docker compose up -d | 启动数据库 |
| `make db-down` | docker compose down | 停止数据库 |
| `make db-reset` | down -v && up -d | 重置数据库（删除所有数据） |
| `make ingest` | python -m scripts.ingest | PDF 文档入库 |
| `make backend` | uvicorn app.main:app --reload | 启动后端 |
| `make frontend` | pnpm dev | 启动前端 |
| `make dev` | db + backend(后台) + frontend | 全部启动 |

## 停止服务

```bash
# 停止前端/后端：Ctrl+C 或
lsof -ti:5173 | xargs kill
lsof -ti:8000 | xargs kill

# 停止数据库
make db-down
```

## 健康检查

```bash
# 数据库
docker exec byd_rag_polardb pg_isready -U postgres -d byd_rag

# 后端
curl -s http://localhost:8000/health

# 前端
curl -s http://localhost:5173 > /dev/null && echo "OK"
```

## 环境变量

关键配置项（`backend/.env` 或系统环境变量）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@localhost:5432/byd_rag` | 数据库连接 |
| `JWT_SECRET_KEY` | `your-secret-key-change-in-production` | JWT 签名密钥 |
| `LLM_API_KEY` | 从 `XFXC_API_KEY` 环境变量读取 | 讯飞星火 API 密钥 |
| `LLM_MODEL_ID` | `astron-code-latest` | LLM 模型 ID |
| `LLM_BASE_URL` | `https://maas-coding-api.cn-huabei-1.xf-yun.com/v2` | LLM API 地址 |
| `EMBEDDING_MODEL_PATH` | `BAAI/bge-large-zh-v1.5` | Embedding 模型路径 |
| `RAG_TOP_K` | `5` | 检索返回的文档块数量 |

**注意**: `LLM_API_KEY` 在代码中通过 `os.getenv("XFXC_API_KEY", "")` 读取系统环境变量，不是从 `.env` 文件读取。

## 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 后端启动报数据库连接失败 | 数据库未就绪 | 等待 30 秒后重试，或检查 `docker ps` |
| 前端代理 500 错误 | 后端未启动 | 先启动后端 `make backend` |
| Embedding 模型加载失败 | 本地无模型缓存 | 自动降级为 API 模式，或设置 `HF_ENDPOINT=https://hf-mirror.com` 下载 |
| LLM API 调用失败 | API Key 未设置 | 确认 `XFXC_API_KEY` 环境变量已设置 |
| 端口被占用 | 旧进程未关闭 | `lsof -ti:8000 \| xargs kill` |

## 测试账号

用户名: `lwliang`，密码: `123456`
