# 生产环境部署指南

## 概述

本文档描述了移动端AI财务助手系统的生产环境部署配置和流程。

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │      Nginx      │    │   Application   │
│    (Optional)   │────│  Reverse Proxy  │────│    (FastAPI)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Static Files  │    │   PostgreSQL    │
                       │   (Nginx)       │    │   Database      │
                       └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐    ┌─────────────────┐
                       │     Redis       │    │   Monitoring    │
                       │    Cache        │    │ (Prometheus +   │
                       └─────────────────┘    │   Grafana)      │
                                              └─────────────────┘
```

## 部署前准备

### 1. 系统要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **内存**: 最少 4GB，推荐 8GB+
- **存储**: 最少 50GB，推荐 100GB+
- **CPU**: 最少 2核，推荐 4核+
- **网络**: 稳定的互联网连接

### 2. 软件依赖

```bash
# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 其他工具
sudo apt-get update
sudo apt-get install -y curl wget openssl bc
```

### 3. 环境变量配置

复制环境变量模板并填入实际值：

```bash
cp .env.prod.example .env.prod
```

编辑 `.env.prod` 文件，设置以下关键变量：

```bash
# 数据库密码（强密码）
DB_PASSWORD=your_secure_db_password_here

# 应用密钥（至少32字符）
SECRET_KEY=your_secret_key_here_at_least_32_characters_long

# AI服务密钥
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Redis密码
REDIS_PASSWORD=your_redis_password_here

# 监控密码
GRAFANA_PASSWORD=your_grafana_admin_password_here
```

## 部署流程

### 1. 自动部署（推荐）

```bash
# 加载环境变量
source .env.prod

# 执行部署脚本
./scripts/deploy.sh
```

### 2. 手动部署

#### 步骤1: 创建必要目录

```bash
mkdir -p logs logs/nginx uploads backups ssl
mkdir -p monitoring/grafana/dashboards monitoring/grafana/datasources
```

#### 步骤2: 生成SSL证书

```bash
# 自签名证书（测试用）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=Finance Assistant/CN=your-domain.com"

# 生产环境建议使用Let's Encrypt
# certbot certonly --standalone -d your-domain.com
```

#### 步骤3: 构建和启动服务

```bash
# 构建镜像
docker-compose -f docker-compose.prod.yml build

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

#### 步骤4: 运行数据库迁移

```bash
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

## 服务配置

### 1. Nginx配置

- **端口**: 80 (HTTP), 443 (HTTPS)
- **SSL**: TLS 1.2+
- **限流**: API 10req/s, 认证 5req/s
- **压缩**: Gzip启用
- **安全头**: 完整的安全头配置

### 2. 应用配置

- **端口**: 8000
- **工作进程**: 4个
- **健康检查**: `/health` 端点
- **日志**: 结构化日志输出

### 3. 数据库配置

- **版本**: PostgreSQL 15
- **连接池**: 20个连接
- **备份**: 每日自动备份
- **监控**: 连接数和性能监控

### 4. Redis配置

- **版本**: Redis 7
- **内存限制**: 256MB
- **持久化**: RDB + AOF
- **密码保护**: 启用

## 监控和日志

### 1. Prometheus监控

- **访问地址**: http://localhost:9090
- **监控指标**:
  - 应用性能指标
  - 系统资源使用
  - 数据库性能
  - Redis性能

### 2. Grafana仪表板

- **访问地址**: http://localhost:3000
- **默认账号**: admin / $GRAFANA_PASSWORD
- **预配置仪表板**:
  - 应用性能监控
  - 系统资源监控
  - 业务指标监控

### 3. 日志收集

- **Filebeat**: 收集应用和系统日志
- **日志路径**: `./logs/`
- **日志轮转**: 自动轮转和清理

## 安全配置

### 1. 网络安全

- **防火墙**: 只开放必要端口
- **SSL/TLS**: 强制HTTPS
- **HSTS**: 启用HTTP严格传输安全

### 2. 应用安全

- **认证**: JWT令牌认证
- **授权**: 基于角色的访问控制
- **输入验证**: 严格的输入验证和清理
- **限流**: API调用频率限制

### 3. 数据安全

- **加密**: 敏感数据加密存储
- **备份**: 加密备份
- **访问控制**: 数据库访问限制

## 备份和恢复

### 1. 数据库备份

```bash
# 手动备份
docker-compose -f docker-compose.prod.yml run --rm db-backup

# 自动备份（crontab）
0 2 * * * /path/to/project/scripts/backup.sh
```

### 2. 数据恢复

```bash
# 恢复数据库
docker-compose -f docker-compose.prod.yml exec db psql -U finance_user -d finance_db < backup_file.sql
```

### 3. 完整系统备份

```bash
# 备份配置和数据
tar -czf system_backup_$(date +%Y%m%d).tar.gz \
    docker-compose.prod.yml \
    .env.prod \
    nginx/ \
    ssl/ \
    backups/ \
    monitoring/
```

## 健康检查

### 1. 自动健康检查

```bash
# 运行健康检查脚本
./scripts/health_check.sh
```

### 2. 手动检查

```bash
# 检查服务状态
docker-compose -f docker-compose.prod.yml ps

# 检查应用健康
curl -f http://localhost/health

# 检查数据库
docker-compose -f docker-compose.prod.yml exec db pg_isready -U finance_user -d finance_db

# 检查Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

## 性能优化

### 1. 应用优化

- **连接池**: 优化数据库连接池大小
- **缓存**: 合理使用Redis缓存
- **异步处理**: 使用异步I/O
- **代码优化**: 定期性能分析和优化

### 2. 数据库优化

- **索引**: 合理创建数据库索引
- **查询优化**: 优化慢查询
- **分区**: 大表分区策略
- **连接优化**: 优化连接参数

### 3. 系统优化

- **内核参数**: 优化网络和文件系统参数
- **资源限制**: 合理设置容器资源限制
- **负载均衡**: 多实例负载均衡

## 故障排除

### 1. 常见问题

#### 应用无法启动
```bash
# 查看应用日志
docker-compose -f docker-compose.prod.yml logs app

# 检查配置文件
docker-compose -f docker-compose.prod.yml config
```

#### 数据库连接失败
```bash
# 检查数据库状态
docker-compose -f docker-compose.prod.yml exec db pg_isready

# 查看数据库日志
docker-compose -f docker-compose.prod.yml logs db
```

#### Redis连接失败
```bash
# 检查Redis状态
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# 查看Redis日志
docker-compose -f docker-compose.prod.yml logs redis
```

### 2. 性能问题

#### 响应时间过长
- 检查数据库查询性能
- 检查Redis缓存命中率
- 检查系统资源使用情况

#### 内存使用过高
- 检查应用内存泄露
- 优化数据库查询
- 调整缓存策略

## 维护操作

### 1. 日常维护

```bash
# 查看系统状态
./scripts/health_check.sh

# 清理Docker资源
docker system prune -f

# 更新SSL证书
# certbot renew

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

### 2. 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新构建和部署
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# 运行迁移
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### 3. 扩容操作

```bash
# 增加应用实例
docker-compose -f docker-compose.prod.yml up -d --scale app=3

# 配置负载均衡
# 更新nginx配置以支持多实例
```

## 联系信息

- **技术支持**: tech-support@your-domain.com
- **紧急联系**: emergency@your-domain.com
- **文档更新**: docs@your-domain.com

---

**注意**: 本文档应根据实际部署环境和需求进行调整。在生产环境部署前，请务必在测试环境中验证所有配置和流程。