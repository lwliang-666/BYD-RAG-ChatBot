# BYD-RAG-ChatBot 线上部署指南

## 架构概览

```
用户浏览器
    |
    v
lwliang.com → Vercel (前端静态托管, 自动 HTTPS + CDN)
    |  /api/*  /uploads/*
    v
api.lwliang.com:8443 → 云服务器 (Nginx 反向代理)
    |
    v
127.0.0.1:8000 → FastAPI + Uvicorn
    |
    v
127.0.0.1:5432 → PolarDB-PG + pgvector (Docker)
```

部署策略：前端部署到 Vercel（免费静态托管 + 自动 HTTPS + CDN），后端和数据库部署到云服务器。

> **非备案说明**：服务器未备案，不能使用 80/443 端口。后端 API 使用 8443 端口，访问地址为 `https://api.lwliang.com:8443`。前端在 Vercel 上不受影响，正常使用 `https://lwliang.com`。

---

## 一、准备工作

### 1.1 购买云服务器

推荐购买轻量应用服务器，性价比最高：

| 平台 | 规格 | 参考价格 | 链接 |
|------|------|----------|------|
| 阿里云 | 2核4G 轻量应用服务器 | 约 50-100 元/月 | https://www.aliyun.com/product/swas |
| 腾讯云 | 2核4G 轻量应用服务器 | 约 50-112 元/月 | https://cloud.tencent.com/product/lighthouse |
| 华为云 | 2核4G HECS 云耀服务器 | 约 59-99 元/月 | https://www.huaweicloud.com/product/hecs.html |

> Embedding 模型 (bge-large-zh-v1.5) 加载需要约 1.3 GB 内存，加上数据库和 FastAPI，4 GB 内存是底线。2核4G 刚好够用，预算充足建议 4核8G。

系统选择 **Ubuntu 22.04 LTS**。

### 1.2 域名规划

域名 `lwliang.com` 已在 Vercel 购买，规划如下：

| 用途 | 域名 | 指向 |
|------|------|------|
| 前端页面 | `lwliang.com` | Vercel |
| 后端 API | `api.lwliang.com:8443` | 云服务器 (49.233.127.241) |

### 1.3 本地确认项目可运行

部署前先在本地确认一切正常：

```bash
# 启动数据库
make db

# PDF 入库
make ingest

# 启动后端
make backend

# 启动前端
make frontend
```

确认登录、对话、RAG 问答功能均正常后再开始部署。

---

## 二、云服务器环境搭建

### 2.1 SSH 登录服务器

```bash
ssh root@49.233.127.241
```

### 2.2 安装基础工具

```bash
apt update && apt upgrade -y
apt install -y git curl wget vim unzip build-essential
```

### 2.3 安装 Docker

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 启动并设置开机自启
systemctl start docker
systemctl enable docker

# 验证
docker --version
```

### 2.4 安装 Python 3.11+

```bash
apt install -y python3.11 python3.11-venv python3-pip
python3.11 --version
```

### 2.5 安装 Nginx

```bash
apt install -y nginx
systemctl start nginx
systemctl enable nginx
```

---

## 三、数据库部署

### 3.1 上传 Docker 配置

在本地执行：

```bash
# 将 docker 目录上传到服务器
scp -r docker/ root@49.233.127.241:/opt/byd-rag/
```

### 3.2 修改 docker-compose.yml

服务器上的 `/opt/byd-rag/docker/docker-compose.yml` 需要修改：

```yaml
services:
  polardb:
    image: polardb/polardb_pg_local_instance:latest
    container_name: byd_rag_polardb
    restart: unless-stopped
    ports:
      # 仅监听本地，不对外暴露
      - "127.0.0.1:5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: <生产环境强密码>
    volumes:
      - polardb_data:/var/libnssdb
      - ./01-create-db.sh:/docker-entrypoint-initdb.d/01-create-db.sh
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d byd_rag"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  polardb_data:
```

关键改动：
- 端口绑定改为 `127.0.0.1:5432`，数据库不对外暴露
- 密码改为强密码

### 3.3 启动数据库

```bash
cd /opt/byd-rag/docker
docker compose up -d

# 等待健康检查通过
docker compose ps
```

---

## 四、后端部署

### 4.1 上传代码

方式一：通过 Git 拉取（推荐，后续更新方便）

```bash
cd /opt/byd-rag
git clone <你的GitHub仓库地址> .
```

方式二：通过 scp 上传

```bash
# 在本地执行
scp -r backend/ root@<服务器IP>:/opt/byd-rag/
```

### 4.2 创建 Python 虚拟环境

```bash
cd /opt/byd-rag/backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4.3 配置环境变量

```bash
vim /opt/byd-rag/backend/.env
```

写入以下内容（根据实际情况修改）：

```env
# 数据库 - 指向本地 Docker 容器
DATABASE_URL=postgresql+asyncpg://postgres:<强密码>@localhost:5432/byd_rag

# JWT - 必须更换为随机强密钥
JWT_SECRET_KEY=<随机生成的64位密钥>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# LLM
LLM_MODEL_ID=astron-code-latest
LLM_BASE_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/v2
# LLM_API_KEY 从系统环境变量 XFXC_API_KEY 读取

# Embedding
EMBEDDING_MODEL_PATH=BAAI/bge-large-zh-v1.5
EMBEDDING_DIMENSION=1024
EMBEDDING_BATCH_SIZE=64

# RAG
RAG_TOP_K=5
CHUNK_MAX_TOKENS=800
CHUNK_OVERLAP_TOKENS=50

# 文件上传
UPLOAD_DIR=/opt/byd-rag/uploads
MAX_AVATAR_SIZE_MB=2

# 提问次数限制
USER_DAILY_QUESTION_LIMIT=20
GLOBAL_DAILY_QUESTION_LIMIT=300
```

生成随机 JWT 密钥：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 4.4 设置 LLM API Key 环境变量

```bash
# 写入系统环境变量，重启后依然生效
echo 'export XFXC_API_KEY="<你的讯飞星火API密钥>"' >> /etc/environment
source /etc/environment
```

### 4.5 PDF 文档入库

```bash
cd /opt/byd-rag/backend
source venv/bin/activate

# 确保 originData 目录中有 PDF 文件
python -m scripts.ingest
```

### 4.6 配置 Systemd 服务

创建后端服务配置：

```bash
vim /etc/systemd/system/byd-rag-backend.service
```

写入：

```ini
[Unit]
Description=BYD RAG ChatBot Backend
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/byd-rag/backend
Environment=XFXC_API_KEY=<你的讯飞星火API密钥>
ExecStart=/opt/byd-rag/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
systemctl daemon-reload
systemctl start byd-rag-backend
systemctl enable byd-rag-backend

# 查看状态
systemctl status byd-rag-backend

# 查看日志
journalctl -u byd-rag-backend -f
```

> `--workers 2` 启动 2 个工作进程，根据服务器 CPU 核数调整，一般设为 `CPU核数 - 1`。

---

## 五、Nginx 反向代理配置

### 5.1 创建 Nginx 配置

```bash
vim /etc/nginx/sites-available/byd-rag
```

写入：

```nginx
server {
    # 非备案服务器，监听 8443 端口而非 443
    listen 8443 ssl;
    server_name api.lwliang.com;

    # SSL 证书路径（Certbot 申请后自动生成）
    ssl_certificate /etc/letsencrypt/live/api.lwliang.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.lwliang.com/privkey.pem;

    # 请求体大小限制（头像上传）
    client_max_body_size 5M;

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持 - 关键配置
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        chunked_transfer_encoding on;
    }

    # 上传文件访问代理
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000/uploads/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}

# HTTP 8443 端口重定向到 HTTPS（用于 Certbot 验证和兼容）
server {
    listen 8443;
    server_name api.lwliang.com;
    return 301 https://$host:8443$request_uri;
}
```

### 5.2 启用配置

```bash
ln -s /etc/nginx/sites-available/byd-rag /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 检查配置语法
nginx -t

# 重载配置
systemctl reload nginx
```

---

## 六、域名 DNS 配置

域名 `lwliang.com` 在 Vercel 购买，DNS 管理也在 Vercel。

### 6.1 在 Vercel 添加 DNS 记录

1. 登录 [Vercel Dashboard](https://vercel.com/dashboard)
2. 进入域名管理：Settings > Domains
3. 点击 `lwliang.com` 旁边的 DNS 配置
4. 添加以下记录：

| 类型 | 名称 | 值 | 说明 |
|------|------|-----|------|
| A | `@` | `76.76.21.21` | Vercel 的 Anycast IP（前端） |
| CNAME | `www` | `cname.vercel-dns.com` | www 子域名（前端） |
| A | `api` | `49.233.127.241` | 后端 API 服务器 |

> 添加 `api` 的 A 记录后，`api.lwliang.com` 就会指向你的云服务器。

### 6.2 等待 DNS 生效

```bash
# 在本地检查 DNS 解析
dig api.lwliang.com
dig lwliang.com

# 检查 8443 端口是否可达（部署 Nginx 后）
curl -k https://api.lwliang.com:8443/health

# 通常几分钟到几小时生效
```

---

## 七、HTTPS 证书配置

### 7.1 前端 HTTPS

Vercel 自动为 `lwliang.com` 提供 HTTPS 证书，无需手动配置。

### 7.2 后端 HTTPS（api.lwliang.com:8443）

非备案服务器使用 8443 端口，Certbot 默认用 80 端口验证域名，需要手动申请证书：

```bash
# 安装 Certbot
apt install -y certbot

# 手动申请证书（使用 DNS 验证方式，不依赖 80 端口）
certbot certonly --manual --preferred-challenges dns -d api.lwliang.com
```

按提示操作：
1. Certbot 会给出一个 TXT 记录值
2. 去 Vercel DNS 设置中添加一条 TXT 记录：`_acme-challenge.api.lwliang.com` = `<Certbot 给的值>`
3. 等待 DNS 生效后按回车继续
4. 证书会生成在 `/etc/letsencrypt/live/api.lwliang.com/`

证书申请成功后，Nginx 配置中已预设了 SSL 证书路径，重载 Nginx 即可：

```bash
nginx -t && systemctl reload nginx
```

### 7.3 设置自动续期

```bash
# Certbot 自动续期已内置 timer，验证一下
systemctl status certbot.timer

# 手动测试续期
certbot renew --dry-run
```

---

## 八、前端部署到 Vercel

### 8.1 修改前端 API 地址

前端 `request.js` 中 `baseURL` 为空，意味着使用相对路径。部署后前端在 `lwliang.com`，API 在 `api.lwliang.com`，需要修改。

修改 `frontend/src/api/request.js`：

```javascript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
})
```

### 8.2 修改后端 CORS 配置

修改 `backend/app/main.py` 中的 CORS 配置，允许线上域名访问：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://lwliang.com",
        "https://www.lwliang.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8.3 创建 Vercel 项目配置

在项目根目录创建 `vercel.json`：

```json
{
  "buildCommand": "cd frontend && pnpm install && pnpm build",
  "outputDirectory": "frontend/dist",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

### 8.4 创建前端环境变量文件

创建 `frontend/.env.production`：

```
VITE_API_BASE_URL=https://api.lwliang.com:8443
```

### 8.5 推送代码到 GitHub

```bash
# 确保代码已提交
git add -A
git commit -m "配置线上部署"
git push origin main
```

### 8.6 在 Vercel 导入项目

1. 登录 [Vercel Dashboard](https://vercel.com/dashboard)
2. 点击 "Add New Project"
3. 选择 "Import Git Repository"
4. 授权并选择你的 GitHub 仓库
5. 配置项目：
   - Framework Preset: **Vite**
   - Root Directory: `frontend`
   - Build Command: `pnpm build`
   - Output Directory: `dist`
6. 在 Environment Variables 中添加：
   - `VITE_API_BASE_URL` = `https://api.lwliang.com:8443`
7. 点击 "Deploy"

### 8.7 绑定域名

1. 在 Vercel 项目 Settings > Domains
2. 添加 `lwliang.com`
3. 按提示配置 DNS（第六步已完成）

---

## 九、验证部署

### 9.1 检查后端

```bash
# 在服务器上
curl http://127.0.0.1:8000/health
# 应返回 {"status":"ok"}

# 从外部检查（HTTPS 证书配置后）
curl https://api.lwliang.com:8443/health
```

### 9.2 检查前端

浏览器访问 `https://lwliang.com`，应看到登录页面。

### 9.3 端到端测试

1. 访问 `https://lwliang.com/register` 注册账号
2. 登录
3. 新建对话，发送问题测试 RAG 问答
4. 测试头像上传
5. 测试用户名修改

---

## 十、日常运维

### 10.1 更新代码

```bash
# 后端更新
cd /opt/byd-rag
git pull origin main
cd backend
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
systemctl restart byd-rag-backend

# 前端更新 - 推送到 GitHub 后 Vercel 自动部署
git push origin main
```

### 10.2 查看日志

```bash
# 后端日志
journalctl -u byd-rag-backend -f

# Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# 数据库日志
cd /opt/byd-rag/docker && docker compose logs -f polardb
```

### 10.3 数据库备份

```bash
# 创建备份目录
mkdir -p /opt/byd-rag/backup

# 手动备份
docker exec byd_rag_polardb pg_dump -U postgres byd_rag > /opt/byd-rag/backup/$(date +%Y%m%d).sql

# 设置定时备份（每天凌晨 3 点）
echo '0 3 * * * docker exec byd_rag_polardb pg_dump -U postgres byd_rag > /opt/byd-rag/backup/$(date +\%Y\%m\%d).sql' | crontab -
```

### 10.4 重新入库 PDF

```bash
cd /opt/byd-rag/backend
source venv/bin/activate
python -m scripts.ingest
```

---

## 十一、安全加固

### 11.1 服务器防火墙

```bash
# 仅开放必要端口（非备案服务器，8443 替代 443）
ufw default deny incoming
ufw allow ssh
ufw allow 8443/tcp
ufw enable
```

> **腾讯云安全组**：还需要在腾讯云控制台的安全组中放行 8443 端口。路径：云服务器控制台 > 安全组 > 入站规则 > 添加规则：TCP 协议，端口 8443，来源 0.0.0.0/0。

### 11.2 SSH 加固

```bash
# 禁用密码登录，仅允许密钥登录
vim /etc/ssh/sshd_config
# 设置: PasswordAuthentication no
# 设置: PermitRootLogin prohibit-password

systemctl restart sshd
```

### 11.3 数据库安全

- 数据库端口仅监听 `127.0.0.1`（已在 docker-compose.yml 配置）
- 使用强密码
- 定期备份

### 11.4 敏感信息

- `.env` 文件权限设为 `600`：`chmod 600 /opt/byd-rag/backend/.env`
- JWT 密钥使用随机强密钥
- API Key 通过环境变量注入，不写入代码

---

## 十二、部署检查清单

- [ ] 云服务器已购买（2核4G+，Ubuntu 22.04）并可 SSH 登录
- [ ] Docker 已安装，数据库容器正常运行
- [ ] 后端代码已上传，虚拟环境已创建
- [ ] `.env` 配置正确（数据库密码、JWT 密钥、API Key）
- [ ] PDF 文档已入库
- [ ] Systemd 服务已配置并正常运行
- [ ] Nginx 反向代理已配置（api.lwliang.com:8443）
- [ ] Vercel DNS 记录已添加（@、www、api 指向 49.233.127.241）
- [ ] HTTPS 证书已申请（api.lwliang.com，DNS 验证方式）并自动续期
- [ ] 前端已部署到 Vercel（lwliang.com）
- [ ] CORS 配置已更新允许 lwliang.com
- [ ] 前端环境变量 `VITE_API_BASE_URL=https://api.lwliang.com:8443` 已设置
- [ ] 防火墙已配置
- [ ] SSH 已加固
- [ ] 数据库定时备份已设置
- [ ] 端到端功能测试通过
