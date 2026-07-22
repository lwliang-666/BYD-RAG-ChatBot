# BYD-RAG-ChatBot 项目开发计划

## 一、项目概述

基于比亚迪 驱逐舰05 技术文档(PDF)，构建一个具备 RAG 向量检索增强功能的 AI 问答系统。

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vite + Vue3 + vue-router + Pinia |
| 后端 | Python + LangGraph + FastAPI |
| 数据库 | Docker + PolarDB-PG (pgvector) |
| LLM | 讯飞星火 coding plan (astron-code-latest) |
| Embedding | bge-large-zh-v1.5 (SentenceTransformer 本地推理) |
| 认证 | JWT Token |

### 核心功能

1. 用户注册/登录 (JWT 认证)
2. AI 对话 (RAG 增强检索)
3. 对话管理 (新建/重命名/置顶/删除-逻辑删除)
4. 用户信息管理 (头像上传/用户名修改-唯一性校验)
5. PDF 文档解析与向量化入库

---

## 二、项目目录结构

```
BYD-RAG-ChatBot/
+-- frontend/
|   +-- public/
|   +-- src/
|   |   +-- api/
|   |   |   +-- request.js
|   |   |   +-- auth.js
|   |   |   +-- chat.js
|   |   |   +-- user.js
|   |   +-- assets/
|   |   |   +-- default-avatar.svg
|   |   +-- components/
|   |   |   +-- ChatMessage.vue
|   |   |   +-- ChatInput.vue
|   |   |   +-- AvatarUpload.vue
|   |   +-- router/
|   |   |   +-- index.js
|   |   +-- stores/
|   |   |   +-- auth.js
|   |   |   +-- chat.js
|   |   |   +-- user.js
|   |   +-- views/
|   |   |   +-- LoginView.vue
|   |   |   +-- RegisterView.vue
|   |   |   +-- ChatView.vue
|   |   +-- App.vue
|   |   +-- main.js
|   +-- index.html
|   +-- vite.config.js
|   +-- package.json
+-- backend/
|   +-- app/
|   |   +-- api/
|   |   |   +-- auth.py
|   |   |   +-- chat.py
|   |   |   +-- user.py
|   |   +-- core/
|   |   |   +-- config.py
|   |   |   +-- security.py
|   |   |   +-- deps.py
|   |   +-- models/
|   |   |   +-- user.py
|   |   |   +-- chat.py
|   |   |   +-- document.py
|   |   |   +-- rate_limit.py
|   |   +-- schemas/
|   |   |   +-- auth.py
|   |   |   +-- chat.py
|   |   |   +-- user.py
|   |   +-- services/
|   |   |   +-- auth_service.py
|   |   |   +-- chat_service.py
|   |   |   +-- user_service.py
|   |   |   +-- rag_service.py
|   |   |   +-- speech_service.py
|   |   |   +-- rate_limit_service.py
|   |   +-- rag/
|   |   |   +-- embedding.py
|   |   |   +-- chunking.py
|   |   |   +-- retriever.py
|   |   |   +-- graph.py
|   |   +-- main.py
|   +-- scripts/
|   |   +-- ingest.py
|   +-- requirements.txt
|   +-- .env
+-- docker/
|   +-- docker-compose.yml
+-- originData/
|   +-- BYD-QZJ05.pdf
+-- .gitignore
+-- PROJECT_PLAN.md
```

---

## 三、数据库设计 (PolarDB-PG + pgvector)

### 3.1 用户表 (users)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| username | VARCHAR(50) | NOT NULL | 用户名(登录名, 部分唯一索引) |
| display_name | VARCHAR(50) | | 显示名称(可修改) |
| password_hash | VARCHAR(255) | NOT NULL | 密码哈希 |
| avatar_url | VARCHAR(500) | | 头像路径 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |
| is_deleted | BOOLEAN | DEFAULT FALSE | 逻辑删除标记 |

### 3.2 对话表 (conversations)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | FK -> users.id | 所属用户 |
| title | VARCHAR(200) | DEFAULT '新对话' | 对话标题 |
| is_pinned | BOOLEAN | DEFAULT FALSE | 是否置顶 |
| is_deleted | BOOLEAN | DEFAULT FALSE | 逻辑删除标记 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | | 更新时间 |

### 3.3 消息表 (messages)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| conversation_id | UUID | FK -> conversations.id | 所属对话 |
| role | VARCHAR(20) | NOT NULL | user/assistant/system |
| content | TEXT | NOT NULL | 消息内容 |
| sources | JSONB | | RAG 检索来源(文档片段引用) |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

### 3.4 文档块表 (document_chunks)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| document_name | VARCHAR(200) | NOT NULL | 源文档名称 |
| chunk_index | INTEGER | NOT NULL | 块序号 |
| content | TEXT | NOT NULL | 文本内容 |
| embedding | VECTOR(1024) | | 向量(bge-large-zh 维度) |
| metadata | JSONB | | 元数据(页码/章节等) |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

### 3.5 提问次数限制表 (question_rate_limits)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| user_id | UUID | NOT NULL | 用户 ID |
| date | DATE | NOT NULL | 日期 |
| count | INTEGER | DEFAULT 0 | 当日提问次数 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

### 3.6 索引设计

- users: username 部分唯一索引(WHERE is_deleted = FALSE, 允许软删除用户名重新注册)
- conversations: user_id + is_deleted 复合索引, is_pinned 索引
- messages: conversation_id 索引
- document_chunks: embedding 向量索引(IVFFlat 或 HNSW)
- question_rate_limits: user_id + date 联合唯一索引(每个用户每天只有一条记录)

---

## 四、API 接口设计

### 4.1 认证模块 (/api/auth)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录(返回 JWT) |
| POST | /api/auth/refresh | 刷新 Token |

### 4.2 对话模块 (/api/chat)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/chat/conversations | 获取对话列表(支持分页) |
| POST | /api/chat/conversations | 创建新对话 |
| GET | /api/chat/conversations/{id} | 获取对话详情(含消息) |
| PUT | /api/chat/conversations/{id} | 更新对话(重命名/置顶) |
| DELETE | /api/chat/conversations/{id} | 逻辑删除对话 |
| POST | /api/chat/conversations/{id}/messages | 发送消息(SSE 流式响应) |

### 4.3 用户模块 (/api/user)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/user/profile | 获取用户信息 |
| PUT | /api/user/profile | 更新用户信息(用户名唯一性校验) |
| POST | /api/user/avatar | 上传头像 |
| PUT | /api/user/username | 修改用户名(唯一性校验) |

### 4.5 语音识别接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/chat/speech-to-text | 上传音频文件，调用讯飞语音听写 API 返回识别文字 |

### 4.6 SSE 流式响应格式

聊天接口采用 Server-Sent Events 流式返回:

```
event: token
data: {"content": "部分内容"}

event: sources
data: {"chunks": [{"content": "...", "metadata": {"page": 5}}]}

event: done
data: {"remaining": {"user_remaining": 15, "global_remaining": 280}}
```

### 4.7 提问次数限制

- 每个用户每天最多提问 20 次
- 全局每天最多提问 300 次
- 超限时返回 HTTP 429 状态码，detail 包含 `user_remaining` 和 `global_remaining`
- SSE done 事件中返回本次提问后的剩余次数

---

## 五、RAG 架构设计

### 5.1 数据处理流程

```mermaid
flowchart LR
    A[PDF 文档] --> B[PyMuPDF 解析]
    B --> C[语义分块]
    C --> D[SentenceTransformer Embedding]
    D --> E[PolarDB-PG 存储]
```

### 5.2 查询流程

```mermaid
flowchart TD
    Q[用户提问] --> R[Query Embedding]
    R --> S[pgvector 相似度检索]
    S --> T[Top-K 文档块]
    T --> U[Prompt 组装]
    U --> V[讯飞星火 LLM]
    V --> W[流式响应]
    W --> X[前端展示]
```

### 5.3 RAG 查询流程

采用过程式实现，简洁高效:

```mermaid
flowchart TD
    Q[用户提问] --> R[Query Embedding]
    R --> S[pgvector 相似度检索]
    S --> T[Top-K 文档块]
    T --> U[Prompt 组装 + 历史消息]
    U --> V[讯飞星火 LLM 流式生成]
    V --> W[SSE 流式响应]
    W --> X[前端展示]
```

> 注: graph.py 中保留了 LangGraph 的 RAGState/retrieve_node/generate_node 定义作为扩展预留，当前主流程 stream_rag_answer 采用过程式实现。

### 5.4 语义分块策略

1. 使用 PyMuPDF 提取 PDF 文本(含页码/位置信息)
2. 按段落/章节标题进行语义切分
3. 块大小: 目标 500 tokens, 最大 800 tokens
4. 块重叠: 50 tokens (保持上下文连贯)
5. 保留元数据: 页码/章节名/文档名
6. 对于图表密集页面, 提取图片并单独存储描述

### 5.5 Embedding 配置

- 模型: bge-large-zh-v1.5 (SentenceTransformer 本地推理)
- 维度: 1024
- 运行方式: 本地 SentenceTransformer 推理, 加载失败时回退到 API 方式
- 批量处理: 每批 64 条文本块

---

## 六、前端页面架构

### 6.1 页面布局

```mermaid
flowchart LR
    subgraph loginPage [登录/注册页]
        L1[登录表单]
        L2[注册表单]
    end
    subgraph chatPage [聊天主页]
        subgraph sidebar [左侧边栏]
            S1[新建对话按钮]
            S2[对话记录列表]
            S3[用户信息区]
        end
        subgraph mainArea [右侧主区域]
            M1[对话标题栏]
            M2[消息列表]
            M3[输入框]
        end
    end
    loginPage -->|登录成功| chatPage
```

### 6.2 路由设计

| 路径 | 组件 | 权限 |
|------|------|------|
| /login | LoginView | 公开 |
| /register | RegisterView | 公开 |
| / | ChatView | 需登录 |

### 6.3 状态管理 (Pinia)

- auth store: token/登录状态/登出
- chat store: 对话列表/当前对话/消息列表/SSE 连接
- user store: 用户信息/头像/显示名

### 6.4 关键交互

- 对话列表: 支持三点按钮菜单(重命名/置顶/删除)
- 消息展示: 用户消息靠右, AI 消息靠左, 支持 Markdown 渲染
- AI 回答: SSE 流式逐字显示, 底部展示引用来源
- 语音输入: 输入框旁麦克风按钮, 前端使用 MediaRecorder 录音, 上传到后端调用讯飞语音听写 WebSocket API 识别, 结果填入输入框后用户手动发送, 录音中显示红色脉冲动画, 识别中显示"识别中"提示
- 语音播放: AI 消息和流式内容支持语音朗读, 使用 Web Speech API SpeechSynthesis, 自动去除 Markdown 标记后朗读纯文本, 播放中按钮高亮, 点击可停止
- 头像上传: 点击头像弹出文件选择, 支持 jpg/png/gif/webp, 大小限制 2MB
- 用户名修改: 双击用户名或单击编辑图标进入编辑模式, 失焦时校验唯一性

---

## 七、开发步骤

### 阶段一: 基础设施搭建 (预计 1-2 天)

**步骤 1.1: 项目初始化**
- 创建 .gitignore 文件
- 初始化前端项目: pnpm create vite frontend --template vue
- 初始化后端项目: 创建 backend/ 目录结构
- 创建 backend/requirements.txt (核心依赖: fastapi, uvicorn, sqlalchemy, asyncpg, pyjwt, passlib, python-jose, python-multipart, langgraph, langchain-core, langchain-openai, pymupdf, httpx, pydantic, pydantic-settings, python-dotenv, sse-starlette, tiktoken, sentence-transformers)

**步骤 1.2: Docker + PolarDB-PG 搭建**
- 编写 docker/docker-compose.yml
- 配置 PolarDB-PG 容器(端口 5432)
- 启用 pgvector 扩展: CREATE EXTENSION vector
- 创建数据库和初始用户
- 验证连接

**步骤 1.3: 后端数据库连接**
- 配置 backend/app/core/config.py (数据库连接串/密钥等)
- 使用 SQLAlchemy 2.0 + async 引擎
- 创建所有数据表(见第三节)
- 编写 Alembic 迁移配置(可选)

### 阶段二: 后端认证模块 (预计 1 天)

**步骤 2.1: JWT 工具实现**
- 实现 backend/app/core/security.py
  - 密码哈希: bcrypt
  - JWT 生成/验证: python-jose
  - Token 过期时间: access_token 30min, refresh_token 7d

**步骤 2.2: 认证 API**
- POST /api/auth/register: 注册(用户名唯一性校验/密码强度校验)
- POST /api/auth/login: 登录(返回 access_token + refresh_token)
- POST /api/auth/refresh: 刷新 Token
- 编写 backend/app/api/auth.py 路由
- 编写 backend/app/services/auth_service.py 业务逻辑
- 编写 backend/app/schemas/auth.py 请求/响应模型

**步骤 2.3: 认证中间件**
- 实现 get_current_user 依赖注入
- 需认证接口自动校验 JWT

### 阶段三: RAG 核心模块 (预计 2-3 天)

**步骤 3.1: PDF 解析与语义分块**
- 实现 backend/app/rag/chunking.py
  - 使用 PyMuPDF (fitz) 提取 PDF 文本
  - 按章节标题/段落进行语义切分
  - 保留元数据(页码/章节名)
  - 块大小: 目标 500 tokens, 最大 800, 重叠 50

**步骤 3.2: SentenceTransformer Embedding 集成**
- 实现 backend/app/rag/embedding.py
  - 加载 bge-large-zh-v1.5 SentenceTransformer 模型
  - 实现批量文本向量化接口
  - 批大小: 64 条/批
  - 输出维度: 1024
  - 模型加载失败时回退到 API 方式

**步骤 3.3: 向量存储与检索**
- 实现 backend/app/rag/retriever.py
  - 文档块入库: INSERT INTO document_chunks (content, embedding, metadata)
  - 相似度检索: SELECT ... ORDER BY embedding <=> query_vector LIMIT K
  - Top-K 参数: 默认 5, 可配置
  - 创建 HNSW 向量索引

**步骤 3.4: PDF 入库脚本**
- 实现 backend/scripts/ingest.py
  - 读取 originData/BYD-QZJ05.pdf
  - 调用分块 -> Embedding -> 入库流程
  - 支持断点续传(已处理的块跳过)
  - 进度条显示

**步骤 3.5: RAG 查询流程**
- 实现 backend/app/rag/graph.py
  - 检索: 调用 retriever 获取相关文档块
  - 生成: 组装 Prompt + 历史消息 + 调用讯飞星火 LLM
  - 流式输出: 逐 token 返回前端(SSE 格式)
  - 保留 LangGraph 扩展预留(RAGState/retrieve_node/generate_node)

### 阶段四: 后端对话与用户模块 (预计 1-2 天)

**步骤 4.1: 对话 API**
- GET /api/chat/conversations: 获取对话列表(按置顶+时间排序, 过滤逻辑删除)
- POST /api/chat/conversations: 创建新对话
- GET /api/chat/conversations/{id}: 获取对话详情(含全部消息)
- PUT /api/chat/conversations/{id}: 更新对话(重命名/置顶切换)
- DELETE /api/chat/conversations/{id}: 逻辑删除(is_deleted=True)
- POST /api/chat/conversations/{id}/messages: 发送消息(SSE 流式)
  - 保存用户消息到 messages 表
  - 调用 LangGraph 工作流
  - SSE 流式返回 AI 回答
  - 保存 AI 回答到 messages 表

**步骤 4.2: 用户信息 API**
- GET /api/user/profile: 获取当前用户信息
- PUT /api/user/profile: 更新显示名称
- PUT /api/user/username: 修改用户名(唯一性校验, 冲突返回 409)
- POST /api/user/avatar: 上传头像(文件存储到本地 uploads/ 目录)

**步骤 4.3: RAG 服务整合**
- 实现 backend/app/services/rag_service.py
  - 整合 LangGraph 工作流
  - 管理对话上下文(历史消息作为上下文传入)
  - 返回流式生成器供 SSE 使用

### 阶段五: 前端开发 (预计 3-4 天)

**步骤 5.1: 前端项目搭建**
- pnpm create vite frontend --template vue
- 安装依赖: vue-router, pinia, axios, markdown-it, highlight.js
- 配置 vite.config.js (代理 /api 到后端)
- 配置 vue-router (登录/注册/聊天页)
- 配置 Pinia stores

**步骤 5.2: 登录/注册页面**
- LoginView.vue: 品牌标题(比亚迪驱逐舰05 智能问答助手, 中文艺术字体+渐变+光斑背景) + 用户名+密码表单, 登录按钮, 跳转注册链接
- RegisterView.vue: 用户名+密码+确认密码, 注册按钮, 跳转登录链接
- 封装 api/auth.js: login/register/refresh
- auth store: 保存 token, 自动刷新, 路由守卫

**步骤 5.3: 聊天主页面布局**
- ChatView.vue: 左右分栏布局(侧边栏 280px + 主区域 flex)
- 左侧边栏:
  - 顶部: "开启新对话" 按钮
  - 中部: 对话记录列表(支持滚动加载)
  - 底部: 用户信息区(头像+用户名+设置)
- 右侧主区域:
  - 顶部: 当前对话标题
  - 中部: 消息列表(自动滚动到底部)
  - 底部: 输入框+发送按钮

**步骤 5.4: 对话管理功能**
- 对话列表组件:
  - 显示对话标题+时间
  - 置顶对话置顶显示+置顶图标
  - 三点按钮菜单: 重命名/置顶/取消置顶/删除
  - 点击切换对话
- 新建对话: 点击按钮创建空对话, 自动切换
- 重命名: 弹出输入框修改标题
- 删除: 确认弹窗后逻辑删除

**步骤 5.5: 消息展示与发送**
- ChatMessage.vue:
  - 用户消息: 靠右显示, 用户头像, 悬停显示操作按钮(一键复制/一键填入输入框)
  - AI 消息: 靠左显示, AI 图标, Markdown 渲染, 代码高亮
  - AI 消息操作: 语音播放按钮(使用 Web Speech API SpeechSynthesis, 自动去除 Markdown 标记朗读纯文本)
  - AI 消息底部: 引用来源折叠区(点击展开查看原文档片段)
- ChatInput.vue:
  - 多行输入框(Enter 发送, Shift+Enter 换行)
  - 发送按钮(发送中禁用)
  - 暴露 setText 方法供外部填入内容
  - 清空按钮(输入框有内容时显示, 点击清空并聚焦)
  - 语音输入按钮(MediaRecorder 录音, 上传后端讯飞语音识别 API, 录音中红色脉冲动画, 识别中提示)
- SSE 流式接收:
  - 使用 EventSource 或 fetch + ReadableStream
  - 逐字追加 AI 回答内容
  - 完成后保存完整消息

**步骤 5.6: 用户信息管理**
- 头像区域:
  - 默认显示线性 SVG 占位图
  - 点击触发文件选择, 上传新头像(支持 jpg/png/gif/webp)
  - 上传后即时预览
- 用户名:
  - 默认显示登录名
  - 双击用户名或单击编辑图标进入编辑模式
  - 失焦/回车时调用后端校验唯一性
  - 重复则提示错误, 保留原值

### 阶段六: 联调与优化 (预计 1-2 天)

**步骤 6.1: 前后端联调**
- 登录/注册流程联调
- 对话 CRUD 联调
- SSE 流式对话联调
- 用户信息修改联调
- 头像上传联调

**步骤 6.2: RAG 效果优化**
- 调整分块参数(块大小/重叠)
- 调整 Top-K 检索数量
- 优化 Prompt 模板(加入比亚迪领域知识提示)
- 测试不同类型问题的回答质量

**步骤 6.3: 体验优化**
- 消息加载骨架屏
- 对话切换过渡动画
- 网络异常处理与重试
- Token 过期自动刷新
- 移动端响应式适配(可选)

### 阶段七: 部署与文档 (预计 1 天)

**步骤 7.1: 部署配置**
- 前端: pnpm build, Nginx 托管静态文件
- 后端: Uvicorn + Gunicorn 多进程
- 数据库: Docker Compose 编排
- 环境变量: .env 配置管理

**步骤 7.2: 启动脚本**
- 编写 Makefile 或启动脚本
- docker compose up -d (启动数据库)
- python ingest.py (PDF 入库, 首次运行)
- uvicorn app.main:app (启动后端)
- pnpm dev (启动前端开发服务器)

---

## 八、核心依赖清单

### 后端 (requirements.txt)

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29.0
pyjwt>=2.8.0
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
python-multipart>=0.0.9
langgraph>=0.1.0
langchain-core>=0.2.0
langchain-openai>=0.1.0
pymupdf>=1.24.0
httpx>=0.27.0
pydantic>=2.0
pydantic-settings>=2.0
python-dotenv>=1.0.0
sse-starlette>=2.0.0
tiktoken>=0.7.0
sentence-transformers>=2.0.0
```

### 前端 (package.json)

```
vue@3
vue-router@4
pinia@2
axios@1
markdown-it@14
highlight.js@11
```

---

## 九、关键配置项 (.env)

```
# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/byd_rag

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# LLM
LLM_MODEL_ID=astron-code-latest
LLM_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/v2

# Embedding
EMBEDDING_MODEL_PATH=BAAI/bge-large-zh-v1.5
EMBEDDING_DIMENSION=1024
EMBEDDING_BATCH_SIZE=64

# RAG
RAG_TOP_K=5
CHUNK_MAX_TOKENS=800
CHUNK_OVERLAP_TOKENS=50

# 文件上传
UPLOAD_DIR=./uploads
MAX_AVATAR_SIZE_MB=2

# 提问次数限制
USER_DAILY_QUESTION_LIMIT=20
GLOBAL_DAILY_QUESTION_LIMIT=300
```

**密钥配置** (`.env.secrets`，不提交到 git，云服务器通过环境变量或此文件设置)：
```
# LLM API 密钥
LLM_API_KEY=xxx

# 讯飞语音听写
XFYUN_APP_ID=xxx
XFYUN_API_KEY=xxx
XFYUN_API_SECRET=xxx
```

---

## 十、开发时间线总览

| 阶段 | 内容 | 预计时间 |
|------|------|----------|
| 一 | 基础设施搭建 | 1-2 天 |
| 二 | 后端认证模块 | 1 天 |
| 三 | RAG 核心模块 | 2-3 天 |
| 四 | 后端对话与用户模块 | 1-2 天 |
| 五 | 前端开发 | 3-4 天 |
| 六 | 联调与优化 | 1-2 天 |
| 七 | 部署与文档 | 1 天 |
| **合计** | | **10-15 天** |
