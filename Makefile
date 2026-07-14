.PHONY: help dev backend frontend db ingest install

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## 安装前后端依赖
	cd backend && pip install -r requirements.txt
	cd frontend && pnpm install

db: ## 启动 PolarDB-PG 数据库
	cd docker && docker compose up -d
	@echo "等待数据库启动..."
	@sleep 5
	@echo "数据库已启动，访问端口: 5432"

db-down: ## 停止数据库
	cd docker && docker compose down

db-reset: ## 重置数据库(删除数据)
	cd docker && docker compose down -v
	cd docker && docker compose up -d
	@echo "数据库已重置"

ingest: ## PDF 文档入库
	cd backend && python -m scripts.ingest

backend: ## 启动后端服务
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## 启动前端开发服务器
	cd frontend && pnpm dev

dev: ## 启动完整开发环境(数据库+后端+前端)
	@echo "启动数据库..."
	cd docker && docker compose up -d
	@echo "等待数据库启动..."
	@sleep 3
	@echo "启动后端..."
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "启动前端..."
	cd frontend && pnpm dev
