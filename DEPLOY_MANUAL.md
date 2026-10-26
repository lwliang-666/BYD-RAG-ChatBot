# BYD-RAG-ChatBot 手动部署到云服务器方案

## 一、服务器要求

| 项目 | 最低配置 | 说明 |
|------|----------|------|
| CPU | 2 核 | Embedding 模型推理需要一定算力 |
| 内存 | 4 GB | bge-large-zh-v1.5 模型加载约需 1.3 GB |
| 硬盘 | 40 GB | Python 环境 + 模型文件 + 数据库 |
| 系统 | Ubuntu 22.04 LTS | 推荐 LTS 版本 |
| 网络 | 公网 IP + 开放 80/443 端口 | 前端访问 + API |

---

## 二、服务器环境初始化

### 2.1 系统更新

```bash
sudo apt update && sudo apt upgrade -y
```

### 2.2 安装基础工具

```bash
sudo apt install -y git curl wget vim unzip build-essential
```

### 2.3 安装 Python 3.11+

```bash
sudo apt install -y python3 python3-pip python3-venv
# 确认版本
python3 --version  # 需要 >= 3.11
```

如果系统自带版本低于 3.11，通过 deadsnakes PPA 安装：

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
# 设置为默认
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### 2.4 安装 Node.js 20+（前端构建用）

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
# 安装 pnpm
sudo npm install -g pnpm
```

---

## 三、安装 PostgreSQL 16 + pgvector

### 3.1 安装 PostgreSQL 16

```bash
# 添加 PostgreSQL 官方 APT 源
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-16 postgresql-server-dev-16
```

### 3.2 安装 pgvector 扩展

```bash
# 从源码编译安装 pgvector
cd /tmp
git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### 3.3 创建数据库和用户

```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 在 psql 中执行
CREATE USER byd_rag WITH PASSWORD '你的数据库密码';
CREATE DATABASE byd_rag WITH ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C' TEMPLATE template0 OWNER byd_rag;
\c byd_rag
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

### 3.4 配置 PostgreSQL 允许本地连接

编辑 `/etc/postgresql/16/main/pg_hba.conf`，确保有以下行：

```
local   all   byd_rag   md5
host    all   byd_rag   127.0.0.1/32   md5
```

编辑 `/etc/postgresql/16/main/postgresql.conf`，调整性能参数：

```
shared_buffers = 1GB
effective_cache_size = 3GB
work_mem = 64MB
```

重启 PostgreSQL：

```bash
sudo systemctl restart postgresql
sudo systemctl enable postgresql
```

### 3.5 初始化数据表

将项目中的 `docker/init.sql` 内容在 byd_rag 数据库中执行：

```bash
sudo -u postgres psql -d byd_rag -f /opt/byd-rag/docker/init.sql
```

---

## 四、部署后端

### 4.1 创建项目目录

```bash
sudo mkdir -p /opt/byd-rag
sudo chown $USER:$USER /opt/byd-rag
```

### 4.2 拉取代码

```bash
cd /opt/byd-rag
git clone git@github.com:你的用户名/BYD-RAG-ChatBot.git repo
```

如果使用 Deploy Key（只读），配置 SSH key 后：

```bash
cd /opt/byd-rag
git clone git@github.com:你的用户名/BYD-RAG-ChatBot.git repo
```

### 4.3 创建 Python 虚拟环境

```bash
cd /opt/byd-rag/repo/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4.4 配置环境变量

**公共配置** `.env`（已在仓库中，无需修改）：

```ini
# JWT
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

**密钥配置** `.env.secrets`（需手动创建，不提交 git）：
**部署到服务器上的命令** `scp /Users/lwliang/Desktop/AI/BYD-RAG-ChatBot/backend/.env.secrets  byd-server:/opt/byd-rag/backend/.env.secrets`

```bash
cd /opt/byd-rag/repo/backend
cat > .env.secrets << 'EOF'
# 数据库（替换为实际密码）
DATABASE_URL=postgresql+asyncpg://byd_rag:你的数据库密码@localhost:5432/byd_rag

# JWT 签名密钥（替换为随机强密钥）
JWT_SECRET_KEY=替换为随机密钥

# LLM API 密钥
LLM_API_KEY=你的LLM密钥

# 讯飞语音听写
XFYUN_APP_ID=你的APP_ID
XFYUN_API_KEY=你的API_KEY
XFYUN_API_SECRET=你的API_SECRET
EOF

chmod 600 .env.secrets
```

生成随机 JWT 密钥：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4.5 创建上传目录

```bash
mkdir -p /opt/byd-rag/repo/backend/uploads
```

### 4.6 PDF 文档入库

将 PDF 文件上传到服务器：

```bash
# 本地执行
scp originData/BYD-QZJ05.pdf 用户名@服务器IP:/opt/byd-rag/repo/originData/
```

在服务器上执行入库：

```bash
cd /opt/byd-rag/repo/backend
source venv/bin/activate
python -m scripts.ingest
```

入库完成后确认数据：

```bash
sudo -u postgres psql -d byd_rag -c "SELECT COUNT(*) FROM document_chunks;"
```

### 4.7 预下载 Embedding 模型

首次启动时模型会自动下载，但建议提前下载避免启动超时：

```bash
cd /opt/byd-rag/repo/backend
source venv/bin/activate
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-zh-v1.5')"
```

如果服务器网络下载慢，可在本地下载后上传模型缓存目录：

```bash
# 本地下载
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-zh-v1.5')"
# 打包缓存
tar czf bge-model.tar.gz -C ~/.cache/huggingface/hub models--BAAI--bge-large-zh-v1.5

# 上传到服务器
scp bge-model.tar.gz 用户名@服务器IP:/tmp/

# 服务器解压
ssh 用户名@服务器IP
mkdir -p ~/.cache/huggingface/hub
tar xzf /tmp/bge-model.tar.gz -C ~/.cache/huggingface/hub
```

---

## 五、部署前端

### 5.1 构建前端

在服务器上构建（或本地构建后上传 dist 目录）：

**方式 A：服务器构建**

```bash
cd /opt/byd-rag/repo/frontend
pnpm install
VITE_API_BASE_URL=https://你的域名/api pnpm build
```

**方式 B：本地构建后上传**

```bash
# 本地执行
cd frontend
pnpm install
VITE_API_BASE_URL=https://你的域名/api pnpm build
scp -r dist/ 用户名@服务器IP:/opt/byd-rag/frontend-dist/
```

> 注意：`VITE_API_BASE_URL` 是前端 API 请求的基础路径，需要指向后端实际地址。
> 如果前后端同域（通过 Nginx 反代），设为空字符串即可：`VITE_API_BASE_URL= pnpm build`

---

## 六、配置 Nginx 反向代理

### 6.1 安装 Nginx

```bash
sudo apt install -y nginx
```

### 6.2 配置站点

创建配置文件：

```bash
sudo vim /etc/nginx/sites-available/byd-rag
```

写入以下内容（HTTP 版本，后续可加 HTTPS）：

```nginx
server {
    listen 80;
    server_name 你的域名或IP;

    # 前端静态文件
    root /opt/byd-rag/frontend-dist;
    index index.html;

    # 前端路由（Hash 模式不需要 try_files，但加上更安全）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持：禁用缓冲，确保流式响应实时传输
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # 上传文件访问代理
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

> 注意：上面 `proxy_pass` 行的 `$host` 前面缺少 `proxy_set`，正确写法是：
> `proxy_set_header Host $host;`

修正后的完整配置：

```nginx
server {
    listen 80;
    server_name 你的域名或IP;

    root /opt/byd-rag/frontend-dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### 6.3 启用站点

```bash
sudo ln -s /etc/nginx/sites-available/byd-rag /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 6.4 配置 HTTPS（推荐）

使用 Let's Encrypt 免费证书：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 你的域名
```

Certbot 会自动修改 Nginx 配置，添加 SSL 并设置 HTTP 到 HTTPS 重定向。

---

## 七、配置后端 Systemd 服务

### 7.1 创建 Service 文件

```bash
sudo vim /etc/systemd/system/byd-rag.service
```

写入：

```ini
[Unit]
Description=BYD RAG ChatBot Backend
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=你的用户名
Group=你的用户名
WorkingDirectory=/opt/byd-rag/repo/backend
ExecStart=/opt/byd-rag/repo/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

> 注意：`--workers 1` 是因为 Embedding 模型占用内存大，多 worker 会重复加载模型。
> 2 核 4G 服务器建议单 worker 运行。

### 7.2 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl start byd-rag
sudo systemctl enable byd-rag
```

### 7.3 查看日志

```bash
# 查看实时日志
sudo journalctl -u byd-rag -f

# 查看最近 100 行
sudo journalctl -u byd-rag -n 100
```

---

## 八、更新后端 CORS 配置

部署后需要更新 `backend/app/main.py` 中的 CORS 允许源，添加服务器域名：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://你的域名",       # 添加这行
        "https://www.你的域名",   # 添加这行（如有 www）
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

修改后提交代码并重新拉取部署。

---

## 九、一键部署脚本

创建 `/opt/byd-rag/deploy.sh`：

```bash
#!/bin/bash
# deploy.sh - 一键部署脚本
# 从 GitHub 拉取最新代码，同步到运行目录，重启后端服务

set -e

REPO_DIR=/opt/byd-rag/repo
BACKEND_DIR=/opt/byd-rag/repo/backend
FRONTEND_DIR=/opt/byd-rag/repo/frontend
DIST_DIR=/opt/byd-rag/frontend-dist

echo "=== 拉取最新代码 ==="
cd $REPO_DIR
git pull origin master

echo "=== 更新后端依赖 ==="
cd $BACKEND_DIR
source venv/bin/activate
pip install -r requirements.txt -q -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "=== 构建前端 ==="
cd $FRONTEND_DIR
pnpm install
VITE_API_BASE_URL= pnpm build

echo "=== 同步前端产物 ==="
rm -rf $DIST_DIR
cp -r $FRONTEND_DIR/dist $DIST_DIR

echo "=== 重启后端服务 ==="
sudo systemctl restart byd-rag

echo "=== 部署完成 ==="
sudo systemctl status byd-rag --no-pager
```

```bash
chmod +x /opt/byd-rag/deploy.sh
```

日常更新只需执行：

```bash
/opt/byd-rag/deploy.sh
```

---

## 十、验证部署

### 10.1 检查后端健康

```bash
curl http://localhost:8000/health
# 期望返回: {"status":"ok"}
```

### 10.2 检查前端访问

浏览器打开 `https://你的域名`，应看到登录页面。

### 10.3 检查 API 连通

```bash
# 测试登录接口
curl -X POST https://你的域名/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"lwliang","password":"123456"}'
```

### 10.4 检查数据库

```bash
sudo -u postgres psql -d byd_rag -c "SELECT COUNT(*) FROM document_chunks;"
# 应返回入库的文档块数量
```

---

## 十一、常见问题排查

### Q1: 后端启动失败，日志显示 `ModuleNotFoundError`

```bash
# 检查虚拟环境是否激活
cd /opt/byd-rag/repo/backend
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: Embedding 模型加载失败

```bash
# 检查模型缓存
ls ~/.cache/huggingface/hub/
# 手动下载
source venv/bin/activate
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-zh-v1.5')"
```

### Q3: 数据库连接失败

```bash
# 检查 PostgreSQL 状态
sudo systemctl status postgresql
# 测试连接
psql -U byd_rag -d byd_rag -h localhost -c "SELECT 1;"
# 检查 .env.secrets 中的 DATABASE_URL 密码是否正确
```

### Q4: Nginx 502 Bad Gateway

```bash
# 检查后端是否运行
sudo systemctl status byd-rag
# 检查 Nginx 配置
sudo nginx -t
# 查看后端日志
sudo tail -f /var/log/nginx/error.log
```

### Q5: SSE 流式响应中断

Nginx 默认会缓冲代理响应，确保配置了 `proxy_buffering off;` 和足够的 `proxy_read_timeout`。

### Q6: 前端 API 请求 404

检查 `VITE_API_BASE_URL` 构建时是否正确设置。如果通过 Nginx 反代，设为空字符串即可。

---

## 十二、服务器安全加固

### 12.1 防火墙

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 12.2 SSH 安全

```bash
# 禁用密码登录，仅允许密钥
sudo vim /etc/ssh/sshd_config
# 设置: PasswordAuthentication no
sudo systemctl restart sshd
```

### 12.3 自动安全更新

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 十三、部署清单

按顺序执行，逐项确认：

- [ ] 服务器系统更新完成
- [ ] Python 3.11+ 安装完成
- [ ] Node.js 20+ 和 pnpm 安装完成
- [ ] PostgreSQL 16 安装完成
- [ ] pgvector 扩展安装完成
- [ ] 数据库 byd_rag 创建完成
- [ ] 数据表初始化完成（执行 init.sql）
- [ ] 代码拉取到 /opt/byd-rag/repo/
- [ ] Python 虚拟环境创建并安装依赖
- [ ] .env.secrets 配置完成（数据库密码、JWT 密钥、LLM 密钥、讯飞密钥）
- [ ] .env.secrets 权限设为 600
- [ ] uploads 目录创建完成
- [ ] PDF 文件上传并入库完成
- [ ] Embedding 模型预下载完成
- [ ] 前端构建完成（VITE_API_BASE_URL 设置正确）
- [ ] Nginx 安装并配置反向代理
- [ ] Nginx SSE 配置（proxy_buffering off）确认
- [ ] 后端 CORS 配置添加域名
- [ ] HTTPS 证书配置完成
- [ ] Systemd 服务配置并启动
- [ ] 后端健康检查通过（/health 返回 ok）
- [ ] 前端页面可访问
- [ ] 登录功能正常
- [ ] AI 对话功能正常（SSE 流式响应）
- [ ] 防火墙配置完成
- [ ] deploy.sh 一键部署脚本创建完成
