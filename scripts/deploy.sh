#!/bin/bash

# 生产环境部署脚本
# Requirements: 8.3, 8.4

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查必要的环境变量
check_env_vars() {
    log_info "检查环境变量..."
    
    required_vars=(
        "DB_PASSWORD"
        "SECRET_KEY"
        "DEEPSEEK_API_KEY"
        "REDIS_PASSWORD"
        "GRAFANA_PASSWORD"
    )
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "缺少必要的环境变量:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
    
    log_success "环境变量检查通过"
}

# 检查Docker和Docker Compose
check_docker() {
    log_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker服务未运行"
        exit 1
    fi
    
    log_success "Docker环境检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."
    
    directories=(
        "logs"
        "logs/nginx"
        "uploads"
        "backups"
        "ssl"
        "monitoring/grafana/dashboards"
        "monitoring/grafana/datasources"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log_info "创建目录: $dir"
    done
    
    log_success "目录创建完成"
}

# 生成SSL证书（自签名，生产环境应使用真实证书）
generate_ssl_cert() {
    log_info "生成SSL证书..."
    
    if [[ ! -f "ssl/cert.pem" ]] || [[ ! -f "ssl/key.pem" ]]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout ssl/key.pem \
            -out ssl/cert.pem \
            -subj "/C=CN/ST=Beijing/L=Beijing/O=Finance Assistant/CN=localhost"
        
        log_success "SSL证书生成完成"
    else
        log_info "SSL证书已存在，跳过生成"
    fi
}

# 配置Redis
setup_redis_config() {
    log_info "配置Redis..."
    
    cat > redis.conf << EOF
# Redis生产环境配置
bind 0.0.0.0
port 6379
requirepass ${REDIS_PASSWORD}

# 持久化配置
save 900 1
save 300 10
save 60 10000

# 内存配置
maxmemory 256mb
maxmemory-policy allkeys-lru

# 安全配置
protected-mode yes
tcp-keepalive 300

# 日志配置
loglevel notice
logfile ""

# 其他配置
timeout 0
databases 16
EOF
    
    log_success "Redis配置完成"
}

# 配置Grafana数据源
setup_grafana_datasources() {
    log_info "配置Grafana数据源..."
    
    mkdir -p monitoring/grafana/datasources
    
    cat > monitoring/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF
    
    log_success "Grafana数据源配置完成"
}

# 配置Grafana仪表板
setup_grafana_dashboards() {
    log_info "配置Grafana仪表板..."
    
    mkdir -p monitoring/grafana/dashboards
    
    cat > monitoring/grafana/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF
    
    log_success "Grafana仪表板配置完成"
}

# 配置Filebeat
setup_filebeat_config() {
    log_info "配置Filebeat..."
    
    cat > monitoring/filebeat.yml << EOF
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/app/*.log
  fields:
    service: finance-assistant
    environment: production
  fields_under_root: true

- type: docker
  containers.ids:
    - "*"
  processors:
    - add_docker_metadata: ~

output.console:
  enabled: true

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0644
EOF
    
    log_success "Filebeat配置完成"
}

# 创建备份脚本
create_backup_script() {
    log_info "创建数据库备份脚本..."
    
    mkdir -p scripts
    
    cat > scripts/backup.sh << 'EOF'
#!/bin/bash

# 数据库备份脚本
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="finance_db"
DB_USER="finance_user"
DB_HOST="db"

# 创建备份
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > $BACKUP_DIR/backup_$DATE.sql

# 压缩备份文件
gzip $BACKUP_DIR/backup_$DATE.sql

# 删除7天前的备份
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

echo "数据库备份完成: backup_$DATE.sql.gz"
EOF
    
    chmod +x scripts/backup.sh
    log_success "备份脚本创建完成"
}

# 构建和启动服务
deploy_services() {
    log_info "构建和启动服务..."
    
    # 停止现有服务
    docker-compose -f docker-compose.prod.yml down
    
    # 构建镜像
    log_info "构建应用镜像..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # 启动服务
    log_info "启动服务..."
    docker-compose -f docker-compose.prod.yml up -d
    
    log_success "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."
    
    services=("db:5432" "redis:6379" "app:8000")
    
    for service in "${services[@]}"; do
        host=$(echo $service | cut -d: -f1)
        port=$(echo $service | cut -d: -f2)
        
        log_info "等待 $host:$port..."
        
        timeout=60
        while ! docker-compose -f docker-compose.prod.yml exec -T $host nc -z localhost $port 2>/dev/null; do
            timeout=$((timeout - 1))
            if [[ $timeout -eq 0 ]]; then
                log_error "$host:$port 启动超时"
                exit 1
            fi
            sleep 1
        done
        
        log_success "$host:$port 已就绪"
    done
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    docker-compose -f docker-compose.prod.yml exec -T app alembic upgrade head
    
    log_success "数据库迁移完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查应用健康状态
    if curl -f http://localhost/health &> /dev/null; then
        log_success "应用健康检查通过"
    else
        log_error "应用健康检查失败"
        exit 1
    fi
    
    # 检查数据库连接
    if docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U finance_user -d finance_db &> /dev/null; then
        log_success "数据库健康检查通过"
    else
        log_error "数据库健康检查失败"
        exit 1
    fi
    
    # 检查Redis连接
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping &> /dev/null; then
        log_success "Redis健康检查通过"
    else
        log_error "Redis健康检查失败"
        exit 1
    fi
}

# 显示部署信息
show_deployment_info() {
    log_success "部署完成！"
    echo
    echo "服务访问地址:"
    echo "  应用: https://localhost"
    echo "  API文档: https://localhost/docs"
    echo "  Grafana: http://localhost:3000 (admin/\$GRAFANA_PASSWORD)"
    echo "  Prometheus: http://localhost:9090"
    echo
    echo "管理命令:"
    echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
    echo "  重启服务: docker-compose -f docker-compose.prod.yml restart"
    echo "  数据库备份: docker-compose -f docker-compose.prod.yml run --rm db-backup"
    echo
}

# 主函数
main() {
    log_info "开始生产环境部署..."
    
    check_env_vars
    check_docker
    create_directories
    generate_ssl_cert
    setup_redis_config
    setup_grafana_datasources
    setup_grafana_dashboards
    setup_filebeat_config
    create_backup_script
    deploy_services
    wait_for_services
    run_migrations
    health_check
    show_deployment_info
    
    log_success "生产环境部署完成！"
}

# 执行主函数
main "$@"