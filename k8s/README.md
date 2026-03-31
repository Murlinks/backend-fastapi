# Kubernetes 部署指南

本目录包含完整的 Kubernetes 部署配置文件。

## 目录结构

```
k8s/
├── namespace.yaml              # 命名空间
├── configmap.yaml             # 配置映射
├── secrets.yaml               # 密钥配置
├── app-deployment.yaml        # 应用部署
├── postgres-statefulset.yaml  # PostgreSQL 数据库
├── redis-statefulset.yaml     # Redis 缓存
├── ingress.yaml               # Ingress 路由
├── hpa.yaml                   # 水平自动扩缩容
├── monitoring.yaml            # 监控配置
└── README.md                  # 本文件
```

## 快速开始

### 1. 前置要求

- Kubernetes 集群 (v1.24+)
- kubectl 命令行工具
- Helm (可选，用于安装 Ingress Controller)

### 2. 安装 Ingress Controller

```bash
# 使用 Helm 安装 Nginx Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

### 3. 配置密钥

编辑 `secrets.yaml` 文件，替换所有 `CHANGE_ME_IN_PRODUCTION` 占位符：

```bash
# 生成随机密钥
openssl rand -base64 32

# 编辑 secrets.yaml
vim secrets.yaml
```

重要密钥：
- `DATABASE_PASSWORD`: 数据库密码
- `REDIS_PASSWORD`: Redis 密码
- `SECRET_KEY`: 应用密钥
- `JWT_SECRET_KEY`: JWT 密钥
- `DEEPSEEK_API_KEY`: AI 服务密钥
- `XUNFEI_APP_ID`, `XUNFEI_API_KEY`, `XUNFEI_API_SECRET`: 讯飞语音识别
- `BAIDU_APP_ID`, `BAIDU_API_KEY`, `BAIDU_SECRET_KEY`: 百度语音识别

### 4. 部署应用

```bash
# 创建命名空间
kubectl apply -f namespace.yaml

# 部署配置和密钥
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml

# 部署数据库和缓存
kubectl apply -f postgres-statefulset.yaml
kubectl apply -f redis-statefulset.yaml

# 等待数据库和缓存就绪
kubectl wait --for=condition=ready pod -l app=postgres -n finance-assistant --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n finance-assistant --timeout=300s

# 部署应用
kubectl apply -f app-deployment.yaml

# 部署 Ingress
kubectl apply -f ingress.yaml

# 部署自动扩缩容
kubectl apply -f hpa.yaml

# 部署监控（可选）
kubectl apply -f monitoring.yaml
```

### 5. 验证部署

```bash
# 查看所有资源
kubectl get all -n finance-assistant

# 查看 Pod 状态
kubectl get pods -n finance-assistant

# 查看服务
kubectl get svc -n finance-assistant

# 查看 Ingress
kubectl get ingress -n finance-assistant

# 查看日志
kubectl logs -f deployment/finance-app -n finance-assistant
```

### 6. 访问应用

```bash
# 获取 Ingress IP
kubectl get ingress -n finance-assistant

# 配置 DNS 或 hosts 文件
# 例如: 192.168.1.100 api.finance-assistant.com

# 测试健康检查
curl https://api.finance-assistant.com/health
```

## 配置说明

### 应用配置 (app-deployment.yaml)

- **副本数**: 3 个（可通过 HPA 自动扩展到 10 个）
- **资源限制**:
  - 请求: 512Mi 内存, 500m CPU
  - 限制: 2Gi 内存, 2000m CPU
- **健康检查**:
  - 存活探针: `/health` 端点
  - 就绪探针: `/health` 端点
- **初始化容器**:
  - 等待数据库和 Redis 就绪
  - 自动运行数据库迁移

### 数据库配置 (postgres-statefulset.yaml)

- **类型**: StatefulSet（有状态服务）
- **存储**: 20Gi 持久化存储
- **版本**: PostgreSQL 15
- **优化配置**:
  - 连接池: 100 个连接
  - 共享缓冲区: 256MB
  - 有效缓存: 1GB

### Redis 配置 (redis-statefulset.yaml)

- **类型**: StatefulSet
- **存储**: 5Gi 持久化存储
- **版本**: Redis 7
- **持久化**: RDB + AOF
- **内存限制**: 512MB
- **淘汰策略**: allkeys-lru

### 自动扩缩容 (hpa.yaml)

- **最小副本数**: 3
- **最大副本数**: 10
- **扩容条件**:
  - CPU 使用率 > 70%
  - 内存使用率 > 80%
- **扩容策略**:
  - 快速扩容: 每 30 秒最多增加 100% 或 4 个 Pod
  - 缓慢缩容: 每 60 秒最多减少 50% 或 2 个 Pod

### Ingress 配置 (ingress.yaml)

- **TLS**: 自动 HTTPS（Let's Encrypt）
- **限流**: 100 req/s
- **CORS**: 已启用
- **安全头**: 完整配置
- **超时**: 60 秒

## 监控和日志

### Prometheus 监控

```bash
# 访问 Prometheus
kubectl port-forward svc/prometheus-service 9090:9090 -n finance-assistant

# 浏览器访问
http://localhost:9090
```

### Grafana 仪表板

```bash
# 访问 Grafana
kubectl port-forward svc/grafana-service 3000:3000 -n finance-assistant

# 浏览器访问
http://localhost:3000

# 默认账号: admin
# 密码: 在 secrets.yaml 中配置的 SECRET_KEY
```

### 查看日志

```bash
# 应用日志
kubectl logs -f deployment/finance-app -n finance-assistant

# 数据库日志
kubectl logs -f statefulset/postgres -n finance-assistant

# Redis 日志
kubectl logs -f statefulset/redis -n finance-assistant

# 所有 Pod 日志
kubectl logs -f -l app=finance-app -n finance-assistant
```

## 运维操作

### 扩容/缩容

```bash
# 手动扩容到 5 个副本
kubectl scale deployment/finance-app --replicas=5 -n finance-assistant

# 查看 HPA 状态
kubectl get hpa -n finance-assistant

# 查看 HPA 详情
kubectl describe hpa finance-app-hpa -n finance-assistant
```

### 滚动更新

```bash
# 更新镜像
kubectl set image deployment/finance-app \
  finance-app=your-registry/finance-backend:v2.0.0 \
  -n finance-assistant

# 查看更新状态
kubectl rollout status deployment/finance-app -n finance-assistant

# 查看更新历史
kubectl rollout history deployment/finance-app -n finance-assistant

# 回滚到上一个版本
kubectl rollout undo deployment/finance-app -n finance-assistant

# 回滚到指定版本
kubectl rollout undo deployment/finance-app --to-revision=2 -n finance-assistant
```

### 数据库备份

```bash
# 创建备份
kubectl exec -it postgres-0 -n finance-assistant -- \
  pg_dump -U finance_user finance_db > backup.sql

# 恢复备份
kubectl exec -i postgres-0 -n finance-assistant -- \
  psql -U finance_user finance_db < backup.sql
```

### 重启服务

```bash
# 重启应用
kubectl rollout restart deployment/finance-app -n finance-assistant

# 重启数据库（谨慎操作）
kubectl delete pod postgres-0 -n finance-assistant

# 重启 Redis
kubectl delete pod redis-0 -n finance-assistant
```

## 故障排查

### Pod 无法启动

```bash
# 查看 Pod 状态
kubectl describe pod <pod-name> -n finance-assistant

# 查看事件
kubectl get events -n finance-assistant --sort-by='.lastTimestamp'

# 查看日志
kubectl logs <pod-name> -n finance-assistant
kubectl logs <pod-name> -n finance-assistant --previous  # 查看上一次的日志
```

### 数据库连接失败

```bash
# 检查数据库 Pod
kubectl get pod -l app=postgres -n finance-assistant

# 测试数据库连接
kubectl exec -it postgres-0 -n finance-assistant -- \
  psql -U finance_user -d finance_db -c "SELECT 1"

# 检查密钥配置
kubectl get secret finance-app-secrets -n finance-assistant -o yaml
```

### 服务无法访问

```bash
# 检查 Service
kubectl get svc -n finance-assistant

# 检查 Ingress
kubectl describe ingress finance-app-ingress -n finance-assistant

# 检查 Ingress Controller
kubectl get pods -n ingress-nginx

# 测试内部访问
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://finance-app-service.finance-assistant.svc.cluster.local:8000/health
```

### 性能问题

```bash
# 查看资源使用
kubectl top pods -n finance-assistant
kubectl top nodes

# 查看 HPA 状态
kubectl get hpa -n finance-assistant

# 查看 Pod 资源限制
kubectl describe pod <pod-name> -n finance-assistant | grep -A 5 "Limits"
```

## 安全最佳实践

1. **密钥管理**
   - 使用强密码
   - 定期轮换密钥
   - 考虑使用 Sealed Secrets 或 External Secrets

2. **网络策略**
   - 限制 Pod 间通信
   - 使用 NetworkPolicy

3. **RBAC**
   - 最小权限原则
   - 定期审计权限

4. **镜像安全**
   - 使用官方镜像
   - 定期扫描漏洞
   - 使用私有镜像仓库

5. **备份**
   - 定期备份数据库
   - 备份配置文件
   - 测试恢复流程

## 性能优化

1. **资源配置**
   - 根据实际负载调整资源请求和限制
   - 使用 HPA 自动扩缩容

2. **数据库优化**
   - 调整连接池大小
   - 优化查询
   - 使用索引

3. **缓存策略**
   - 合理使用 Redis 缓存
   - 设置合适的过期时间

4. **网络优化**
   - 使用 CDN
   - 启用 HTTP/2
   - 压缩响应

## 成本优化

1. **资源利用率**
   - 监控资源使用情况
   - 调整 Pod 资源配置
   - 使用 Spot 实例（如果可用）

2. **存储优化**
   - 定期清理旧数据
   - 使用合适的存储类
   - 压缩备份

3. **自动扩缩容**
   - 配置合理的 HPA 策略
   - 在低峰期缩容

## 更新日志

- 2024-01-15: 初始版本
  - 完整的 K8s 部署配置
  - 支持自动扩缩容
  - 集成监控和日志
  - 语音识别服务集成

## 支持

如有问题，请联系：
- 技术支持: tech-support@finance-assistant.com
- 文档: https://docs.finance-assistant.com
