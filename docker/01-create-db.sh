#!/bin/bash
# 01-create-db.sh - 数据库初始化脚本
# 在 PolarDB-PG 容器首次启动时自动执行
# 功能：创建 UTF8 编码的 byd_rag 数据库，并执行建表脚本
set -e

# 创建 UTF8 编码的 byd_rag 数据库（如果不存在）
# PolarDB-PG 默认创建 SQL_ASCII 编码，这里确保使用 UTF8
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    SELECT 'CREATE DATABASE byd_rag WITH ENCODING '\''UTF8'\'' LC_COLLATE '\''C'\'' LC_CTYPE '\''C'\'' TEMPLATE template0'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'byd_rag')\gexec
EOSQL

# 在 byd_rag 数据库中执行建表脚本
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname byd_rag -f /docker-entrypoint-initdb.d/init.sql
