# 全栈项目部署经验手册

基于 BYD-RAG-ChatBot 部署到腾讯云的实战经验，总结可复用的部署流程和踩坑记录。

---

## 架构模式

```
前端 (Vue/React SPA) → Vercel 静态托管（自动 HTTPS + CDN）
后端 (FastAPI/Node) → 云服务器 Nginx 反向代理
数据库 (PostgreSQL) → 云服务器 apt 安装（非 Docker）
```

核心思路：前端零成本托管 Vercel，后端+数据库放云服务器。

---

## 一、服务器准备

### 1.1 购买

- 规格：2核4G 起步（embedding 模型 + 数据库 + 后端 ≈ 3GB 内存）
- 系统：Ubuntu 24.04 LTS
- 平台：腾讯云/阿里云轻量应用服务器，50-100 元/月

### 1.2 SSH 免密登录

本地生成无 passphrase 的专用密钥（避免 id_rsa 有 passphrase 导致 sshpass/CI 失败）：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/<项目名> -N "" -C "<项目名>-deploy"
```

将公钥添加到服务器：

```bash
# 方式一：密码登录后添加
ssh-copy-id -i ~/.ssh/<项目名>.pub root@<服务器IP>

# 方式二：腾讯云轻量应用服务器可能要求微信扫码验证
# 先关闭扫码验证，再用密码登录添加公钥
```

配置 SSH config 简化连接：

```
# ~/.ssh/config
Host <项目名>-server
    HostName <服务器IP>
    User root
    IdentityFile ~/.ssh/<项目名>
    IdentitiesOnly yes
```

### 1.3 踩坑记录

| 问题 | 原因 | 解决 |
|------|------|------|
| sshpass 连接超时 | 本地 id_rsa 有 passphrase，SSH 先尝试密钥认证卡住 | 生成无 passphrase 的专用密钥，用 `IdentitiesOnly yes` |
| 腾讯云首次 SSH 要求微信扫码 | 轻量应用服务器默认开启扫码验证 | 在腾讯云控制台关闭扫码验证 |
| SSH 连接偶尔超时 | 服务器内存不足时响应变慢 | 升级配置或优化内存使用 |

---

## 二、环境搭建

### 2.1 基础软件

```bash
apt update && apt upgrade -y
apt install -y git curl wget vim unzip build-essential
apt install -y nginx
apt install -y python3-venv python3-pip
apt install -y postgresql postgresql-16-pgvector
apt install -y certbot
```

### 2.2 Docker 是否安装

按需安装。如果只是跑数据库，建议直接 apt 安装 PostgreSQL，避免国内拉取 Docker 镜像的网络问题。

```bash
# 如果确实需要 Docker
curl -fsSL https://get.docker.com | sh

# 配置国内镜像源
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": ["https://docker.1ms.run"]
}
EOF
systemctl restart docker
```

### 2.3 踩坑记录

| 问题 | 原因 | 解决 |
|------|------|------|
| Docker Hub 镜像拉取超时 | 国内网络无法访问 Docker Hub | 改用 apt 安装 PostgreSQL + pgvector |
| Docker 国内镜像源 429 | 短时间请求过多被限流 | 只保留一个镜像源，重试 |

---

## 三、数据库部署

### 3.1 推荐方案：apt 安装 PostgreSQL + pgvector

比 Docker 方案更稳定，国内服务器首选：

```bash
# 安装
apt install -y postgresql postgresql-16-pgvector

# 配置
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '<强密码>';"
sudo -u postgres psql -c "CREATE DATABASE <数据库名> WITH ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C' TEMPLATE template0;"

# 执行建表脚本
cat init.sql | sudo -u postgres psql -d <数据库名>

# 仅监听本地
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" /etc/postgresql/16/main/postgresql.conf
systemctl restart postgresql
```

### 3.2 Navicat 远程查看

通过 SSH 隧道连接，无需开放数据库端口：

- 主机：`127.0.0.1`，端口：`5432`
- SSH 隧道：启用，主机 `<服务器IP>`，用户名 `root`，私钥选 `~/.ssh/<项目名>`
- 通行短语：专用密钥留空

---

## 四、后端部署

### 4.1 服务器 SSH 密钥配置

在服务器上生成 GitHub 专用密钥（不复用本地密钥，方便单独撤销）：

```bash
ssh-keygen -t ed25519 -C "server-deploy" -f ~/.ssh/id_ed25519_github -N ""
cat >> ~/.ssh/config << 'EOF'
Host github.com
  IdentityFile ~/.ssh/id_ed25519_github
EOF
```

把公钥添加到 GitHub 仓库 Settings > Deploy keys（不勾选 Allow write access，只读即可）。

测试连接：`ssh -T git@github.com`，看到 "successfully authenticated" 即成功。

### 4.2 服务器 clone 仓库

```bash
cd /opt
git clone --depth 1 git@github.com:<user>/<repo>.git <repo-dir>
```

**大文件处理**：如果仓库有大文件（PDF、模型等），先从 git 历史移除再 clone，否则国内服务器 clone 极慢：

```bash
# 本地执行：从历史中移除大文件
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch <大文件路径>' --prune-empty -- --all
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin --force --all
```

把大文件加入 `.gitignore`，服务器上单独保留。

### 4.3 部署脚本

创建 `/opt/<项目名>/deploy.sh`，核心逻辑：拉代码 → 同步到运行目录 → 安装依赖 → 重启服务 → 检查状态。

```bash
#!/bin/bash
set -e

# 拉取最新代码
cd /opt/<repo-dir>
git fetch origin
git reset --hard origin/master

# 同步到运行目录（排除服务器特有文件）
rsync -av --delete \
  --exclude=".env" \
  --exclude=".env.secrets" \
  --exclude="uploads/" \
  --exclude="__pycache__/" \
  --exclude="venv/" \
  /opt/<repo-dir>/backend/ /opt/<项目名>/backend/

# 安装依赖
cd /opt/<项目名>/backend
/opt/<项目名>/backend/venv/bin/pip install -q -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 重启服务
sudo systemctl restart <service-name>
sleep 2

# 检查状态
if sudo systemctl is-active --quiet <service-name>; then
  echo "部署成功"
else
  echo "部署失败"
  sudo systemctl status <service-name> --no-pager
  exit 1
fi
```

**关键点**：`.env`、`uploads/`、`venv/` 等服务器特有文件用 rsync `--exclude` 排除，避免被仓库代码覆盖。

### 4.4 GitHub Actions 自动部署

创建 `.github/workflows/deploy.yml`：

```yaml
name: Deploy Backend

on:
  push:
    branches: [master]
    paths:
      - 'backend/**'
      - '.github/workflows/deploy.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: bash /opt/<项目名>/deploy.sh
```

**关键点**：
- `paths` 过滤：只有后端代码变更才触发，避免前端改动无谓触发
- 敏感信息用 GitHub Secrets，不硬编码

在 GitHub 仓库 Settings > Secrets and variables > Actions 中添加：

| Secret | 值 | 说明 |
|--------|-----|------|
| `SERVER_HOST` | 服务器 IP | |
| `SERVER_USER` | SSH 用户名 | |
| `SERVER_SSH_KEY` | 本地 SSH 私钥内容 | `cat ~/.ssh/<key> \| pbcopy` 复制 |

### 4.5 虚拟环境和依赖（首次部署）

```bash
cd /opt/<项目名>/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4.6 环境变量

```bash
# 创建 .env
vim /opt/<项目名>/backend/.env
chmod 600 /opt/<项目名>/backend/.env

# 敏感信息通过系统环境变量注入
echo 'export XFXC_API_KEY="<密钥>"' >> /etc/environment
source /etc/environment
```

### 4.4 HuggingFace 模型下载

国内服务器必须使用镜像：

```bash
HF_ENDPOINT=https://hf-mirror.com python -m scripts.ingest
```

可在后台运行避免 SSH 超时：

```bash
nohup bash -c 'HF_ENDPOINT=https://hf-mirror.com python -m scripts.ingest' > /tmp/ingest.log 2>&1 &
```

### 4.5 Systemd 服务

```ini
[Unit]
Description=<项目名> Backend
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/<项目名>/backend
Environment=XFXC_API_KEY=<密钥>
ExecStart=/opt/<项目名>/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> `--workers` 根据内存调整，2核4G 服务器设为 1（embedding 模型占约 1GB 内存）

### 4.7 踩坑记录

| 问题 | 原因 | 解决 |
|------|------|------|
| 后端启动报 Directory not exist | uploads 目录不存在 | `mkdir -p /opt/<项目名>/uploads` |
| Embedding 模型加载失败 | 无法访问 huggingface.co | 设置 `HF_ENDPOINT=https://hf-mirror.com` |
| PDF 入库 0 个文本块 | PDF 上传不完整（94MB 只传了 47MB） | 重新上传并验证文件大小 |
| 入库进程跑 30 分钟 | embedding 计算耗时长 + 内存紧张 | 正常现象，2核4G 跑 266 页 PDF 约需 30 分钟 |
| git clone 超时 | 仓库含大文件（90MB PDF），国内服务器访问 GitHub 慢 | 从 git 历史移除大文件，仓库从 243MB 降到 625KB |
| filter-branch 报错 Cannot rewrite branches | 有未暂存的改动 | 先 `git stash`，filter-branch 后 `git stash pop` |
| deploy.sh 中 pip install 导致脚本中断 | 没有新增依赖时 pip 可能返回非零退出码 | 加 `|| true` 或 `-q` 静默模式 |

---

## 五、Nginx 反向代理

### 5.1 配置模板

```nginx
server {
    listen 8443 ssl;  # 非备案用 8443，已备案用 443
    server_name api.<域名>;

    ssl_certificate /etc/letsencrypt/live/api.<域名>/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.<域名>/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 5M;

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 支持（关键！）
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        chunked_transfer_encoding on;
    }

    # 静态文件代理（上传文件等）
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000/uploads/;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

### 5.2 证书申请

先配置 HTTP 版 Nginx，证书申请后再切 HTTPS：

```bash
# 1. 临时 HTTP 配置
# 2. 停 Nginx，用 standalone 模式申请证书
systemctl stop nginx
certbot certonly --standalone -d api.<域名> --agree-tos --email <邮箱> --no-eff-email

# 3. 证书成功后切换 Nginx 为 HTTPS 配置
# 4. 重启 Nginx
systemctl start nginx
```

> **优先用 standalone 模式**（HTTP 80 端口验证），比 DNS 验证简单得多。DNS 验证每次重新运行 Certbot 会生成新 challenge 值，需要反复更新 TXT 记录。

### 5.3 防火墙

腾讯云轻量应用服务器有**两层防火墙**：
1. **控制台防火墙**：在腾讯云网页配置，必须开放端口
2. **系统 UFW**：在服务器命令行配置

两层都要放行。

---

## 六、前端部署到 Vercel

### 6.1 代码修改清单

**必须修改的文件：**

1. **`frontend/src/api/request.js`** — baseURL 使用环境变量：
   ```javascript
   const api = axios.create({
     baseURL: import.meta.env.VITE_API_BASE_URL || '',
     timeout: 30000,
   })
   ```

2. **`backend/app/main.py`** — CORS 添加线上域名：
   ```python
   allow_origins=[
       "http://localhost:5173",
       "https://<域名>",
       "https://www.<域名>",
   ],
   ```

3. **`frontend/.env.production`** — 创建生产环境变量：
   ```
   VITE_API_BASE_URL=https://api.<域名>:8443
   ```

4. **`vercel.json`** — 创建 Vercel 配置：
   ```json
   {
     "buildCommand": "cd frontend && pnpm install && pnpm build",
     "outputDirectory": "frontend/dist",
     "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
   }
   ```

### 6.2 关键踩坑：跨域资源请求

**问题**：axios 请求走了 baseURL，但原生 fetch 和资源 URL 没有。

**必须检查的三类场景：**

1. **SSE 流式请求**：`fetch('/api/...')` 不会自动加 baseURL
   ```javascript
   // 错误
   fetch(`/api/chat/conversations/${id}/messages`, {...})

   // 正确
   const baseURL = import.meta.env.VITE_API_BASE_URL || ''
   fetch(`${baseURL}/api/chat/conversations/${id}/messages`, {...})
   ```

2. **token 刷新**：`axios.post('/api/auth/refresh')` 用裸 axios 实例不走 baseURL
   ```javascript
   // 错误
   const res = await axios.post('/api/auth/refresh', {...})

   // 正确
   const baseURL = import.meta.env.VITE_API_BASE_URL || ''
   const res = await axios.post(`${baseURL}/api/auth/refresh`, {...})
   ```

3. **静态资源 URL**：后端返回的 `/uploads/xxx.png` 是相对路径，浏览器会请求前端域名
   ```javascript
   // 后端返回: avatar_url = "/uploads/xxx.png"
   // 需要在前端拼接完整地址
   function resolveUrl(url) {
     if (!url || url.startsWith('http')) return url
     return `${import.meta.env.VITE_API_BASE_URL || ''}${url}`
   }
   ```

### 6.3 Vercel 项目配置

在 Vercel Dashboard 中：
- **Root Directory**: `frontend`
- **Build Command**: `pnpm build`
- **Output Directory**: `dist`
- **Environment Variables**: 必须在 Vercel 设置中添加 `VITE_API_BASE_URL`（仅 `.env.production` 不够）

> `.env.production` 文件 Vite 构建时会读取，但 Vercel 的 Root Directory 设为 `frontend` 后可能不读到根目录的文件。最稳妥的做法是同时在 `.env.production` 和 Vercel 环境变量中都配置。

### 6.4 DNS 配置

在 Vercel DNS 中添加：
- `@` → A 记录 → Vercel Anycast IP（前端）
- `www` → CNAME → `cname.vercel-dns.com`（前端）
- `api` → A 记录 → 云服务器 IP（后端）

---

## 七、安全加固

```bash
# 1. UFW 防火墙
ufw default deny incoming
ufw allow ssh
ufw allow 8443/tcp   # 或 443/tcp（已备案）
ufw --force enable

# 2. SSH 加固（确认密钥登录正常后再做！）
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl restart sshd

# 3. 敏感文件权限
chmod 600 /opt/<项目名>/backend/.env

# 4. 数据库定时备份
mkdir -p /opt/<项目名>/backup
echo '0 3 * * * sudo -u postgres pg_dump <数据库名> > /opt/<项目名>/backup/$(date +\%Y\%m\%d).sql' | crontab -
```

---

## 八、部署检查清单

### 服务器端
- [ ] SSH 免密登录正常
- [ ] PostgreSQL 运行正常，仅监听本地
- [ ] 后端 Systemd 服务 enabled + active
- [ ] Nginx HTTPS 反向代理正常
- [ ] SSL 证书自动续期启用
- [ ] UFW 防火墙仅开放 22 + 8443
- [ ] SSH 禁用密码登录
- [ ] .env 权限 600
- [ ] 数据库定时备份

### 前端/Vercel
- [ ] Vercel 环境变量 `VITE_API_BASE_URL` 已设置
- [ ] Root Directory 设为 `frontend`
- [ ] 域名绑定 `lwliang.com`
- [ ] CORS 配置包含线上域名

### 联调验证
- [ ] `https://api.<域名>:8443/health` 返回 OK
- [ ] `https://<域名>` 前端页面正常
- [ ] 注册、登录正常
- [ ] 聊天对话（SSE 流式）正常
- [ ] 头像上传和显示正常
- [ ] 所有 fetch 请求走完整 API 地址（非相对路径）

---

## 九、运维命令速查

```bash
# SSH 登录
ssh <项目名>-server

# 后端日志
journalctl -u byd-rag-backend -f

# 重启后端
systemctl restart byd-rag-backend

# Nginx 日志
tail -f /var/log/nginx/error.log

# 数据库查询
sudo -u postgres psql -d <数据库名> -c "SELECT count(*) FROM users;"

# 数据库备份
sudo -u postgres pg_dump <数据库名> > /opt/<项目名>/backup/$(date +%Y%m%d).sql

# 一键部署（手动触发）
bash /opt/<项目名>/deploy.sh

# 更新前端（推送后 Vercel 自动部署）
git push origin master

# 更新后端（推送后 GitHub Actions 自动部署）
git push origin master
# 仅 backend/ 目录变更时触发自动部署
# 查看部署记录：https://github.com/<user>/<repo>/actions
```
