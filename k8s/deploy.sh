#!/bin/bash

# Kubernetes 部署脚本
# 用法: ./deploy.sh [environment]
# 环境: dev, staging, production

set -e

ENVIRONMENT=${1:-staging}
NAMESPACE="finance-assistant"

if [ "$ENVIRONMENT" = "production" ]; then
    NAMESPACE="finance-assistant"
elif [ "$ENVIRONMENT" = "staging" ]; then
    NAMESPACE="finance-assistant-staging"
else
    NAMESPACE="finance-assistant-dev"
fi

echo "========================================="
echo "部署环境: $ENVIRONMENT"
echo "命名空间: $NAMESPACE"
echo "========================================="

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}错误: kubectl 未安装${NC}"
    exit 1
fi

# 检查集群连接
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}错误: 无法连接到 Kubernetes 集群${NC}"
    exit 1
fi

echo -e "${GREEN}✓ kubectl 已就绪${NC}"

# 1. 创建命名空间
echo -e "\n${YELLOW}步骤 1/8: 创建命名空间${NC}"
kubectl apply -f namespace.yaml
kubectl label namespace $NAMESPACE environment=$ENVIRONMENT --overwrite

# 2. 部署配置
echo -e "\n${YELLOW}步骤 2/8: 部署配置映射${NC}"
kubectl apply -f configmap.yaml -n $NAMESPACE

# 3. 部署密钥
echo -e "\n${YELLOW}步骤 3/8: 部署密钥${NC}"
echo -e "${RED}警告: 请确保已更新 secrets.yaml 中的所有密钥！${NC}"
read -p "是否继续? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "部署已取消"
    exit 1
fi
kubectl apply -f secrets.yaml -n $NAMESPACE

# 4. 部署数据库
echo -e "\n${YELLOW}步骤 4/8: 部署 PostgreSQL${NC}"
kubectl apply -f postgres-statefulset.yaml -n $NAMESPACE
echo "等待 PostgreSQL 就绪..."
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
echo -e "${GREEN}✓ PostgreSQL 已就绪${NC}"

# 5. 部署 Redis
echo -e "\n${YELLOW}步骤 5/8: 部署 Redis${NC}"
kubectl apply -f redis-statefulset.yaml -n $NAMESPACE
echo "等待 Redis 就绪..."
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=300s
echo -e "${GREEN}✓ Redis 已就绪${NC}"

# 6. 部署应用
echo -e "\n${YELLOW}步骤 6/8: 部署应用${NC}"
kubectl apply -f app-deployment.yaml -n $NAMESPACE
echo "等待应用就绪..."
kubectl wait --for=condition=available deployment/finance-app -n $NAMESPACE --timeout=300s
echo -e "${GREEN}✓ 应用已就绪${NC}"

# 7. 部署 Ingress
echo -e "\n${YELLOW}步骤 7/8: 部署 Ingress${NC}"
kubectl apply -f ingress.yaml -n $NAMESPACE

# 8. 部署自动扩缩容
echo -e "\n${YELLOW}步骤 8/8: 部署 HPA${NC}"
kubectl apply -f hpa.yaml -n $NAMESPACE

# 可选: 部署监控
read -p "是否部署监控? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}部署监控组件${NC}"
    kubectl apply -f monitoring.yaml -n $NAMESPACE
fi

# 显示部署状态
echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}=========================================${NC}"

echo -e "\n查看资源状态:"
kubectl get all -n $NAMESPACE

echo -e "\n查看 Ingress:"
kubectl get ingress -n $NAMESPACE

echo -e "\n查看 HPA:"
kubectl get hpa -n $NAMESPACE

# 健康检查
echo -e "\n${YELLOW}执行健康检查...${NC}"
sleep 10

POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=finance-app -o jsonpath='{.items[0].metadata.name}')
if kubectl exec -n $NAMESPACE $POD_NAME -- curl -f http://localhost:8000/health &> /dev/null; then
    echo -e "${GREEN}✓ 健康检查通过${NC}"
else
    echo -e "${RED}✗ 健康检查失败${NC}"
    echo "查看日志:"
    kubectl logs -n $NAMESPACE $POD_NAME --tail=50
fi

echo -e "\n${GREEN}部署完成！${NC}"
echo -e "访问应用: https://api.finance-assistant.com"
echo -e "查看日志: kubectl logs -f deployment/finance-app -n $NAMESPACE"
echo -e "查看状态: kubectl get all -n $NAMESPACE"
