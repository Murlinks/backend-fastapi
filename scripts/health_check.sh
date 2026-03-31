#!/bin/bash

# 生产环境健康检查脚本
# Requirements: 8.3, 8.4, 8.5

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检查服务状态
check_service_status() {
    log_info "检查服务状态..."
    
    services=("app" "db" "redis" "nginx" "prometheus" "grafana")
    failed_services=()
    
    for service in "${services[@]}"; do
        if docker-compose -f docker-compose.prod.yml ps $service | grep -q "Up"; then
            log_success "$service 服务运行正常"
        else
            log_error "$service 服务未运行"
            failed_services+=("$service")
        fi
    done
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        log_error "以下服务未正常运行: ${failed_services[*]}"
        return 1
    fi
    
    return 0
}

# 检查HTTP端点
check_http_endpoints() {
    log_info "检查HTTP端点..."
    
    endpoints=(
        "http://localhost/health:应用健康检查"
        "http://localhost/docs:API文档"
        "http://localhost:3000:Grafana"
        "http://localhost:9090:Prometheus"
    )
    
    failed_endpoints=()
    
    for endpoint_info in "${endpoints[@]}"; do
        url=$(echo $endpoint_info | cut -d: -f1)
        name=$(echo $endpoint_info | cut -d: -f2)
        
        if curl -f -s --max-time 10 "$url" > /dev/null; then
            log_success "$name ($url) 可访问"
        else
            log_error "$name ($url) 不可访问"
            failed_endpoints+=("$name")
        fi
    done
    
    if [[ ${#failed_endpoints[@]} -gt 0 ]]; then
        log_error "以下端点不可访问: ${failed_endpoints[*]}"
        return 1
    fi
    
    return 0
}

# 检查数据库连接
check_database() {
    log_info "检查数据库连接..."
    
    if docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U finance_user -d finance_db; then
        log_success "数据库连接正常"
        
        # 检查数据库表
        table_count=$(docker-compose -f docker-compose.prod.yml exec -T db psql -U finance_user -d finance_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
        
        if [[ $table_count -gt 0 ]]; then
            log_success "数据库包含 $table_count 个表"
        else
            log_warning "数据库中没有表，可能需要运行迁移"
        fi
        
        return 0
    else
        log_error "数据库连接失败"
        return 1
    fi
}

# 检查Redis连接
check_redis() {
    log_info "检查Redis连接..."
    
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis连接正常"
        
        # 检查Redis内存使用
        memory_info=$(docker-compose -f docker-compose.prod.yml exec -T redis redis-cli info memory | grep used_memory_human)
        log_info "Redis内存使用: $memory_info"
        
        return 0
    else
        log_error "Redis连接失败"
        return 1
    fi
}

# 检查磁盘空间
check_disk_space() {
    log_info "检查磁盘空间..."
    
    # 检查根分区
    root_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $root_usage -lt 80 ]]; then
        log_success "根分区使用率: ${root_usage}%"
    elif [[ $root_usage -lt 90 ]]; then
        log_warning "根分区使用率: ${root_usage}% (建议清理)"
    else
        log_error "根分区使用率: ${root_usage}% (空间不足)"
        return 1
    fi
    
    # 检查Docker卷空间
    docker_usage=$(docker system df | grep "Local Volumes" | awk '{print $4}' | sed 's/[^0-9.]//g')
    if [[ -n "$docker_usage" ]]; then
        log_info "Docker卷使用空间: ${docker_usage}"
    fi
    
    return 0
}

# 检查内存使用
check_memory_usage() {
    log_info "检查内存使用..."
    
    # 系统内存使用
    memory_info=$(free -h | grep "Mem:")
    total_mem=$(echo $memory_info | awk '{print $2}')
    used_mem=$(echo $memory_info | awk '{print $3}')
    available_mem=$(echo $memory_info | awk '{print $7}')
    
    log_info "系统内存: 总计 $total_mem, 已用 $used_mem, 可用 $available_mem"
    
    # Docker容器内存使用
    log_info "容器内存使用:"
    docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" | head -10
    
    return 0
}

# 检查日志错误
check_logs_for_errors() {
    log_info "检查最近的错误日志..."
    
    # 检查应用日志中的错误
    error_count=$(docker-compose -f docker-compose.prod.yml logs --tail=100 app 2>/dev/null | grep -i "error\|exception\|failed" | wc -l)
    
    if [[ $error_count -eq 0 ]]; then
        log_success "应用日志中没有发现错误"
    elif [[ $error_count -lt 5 ]]; then
        log_warning "应用日志中发现 $error_count 个错误"
    else
        log_error "应用日志中发现 $error_count 个错误，需要检查"
        
        # 显示最近的错误
        log_info "最近的错误日志:"
        docker-compose -f docker-compose.prod.yml logs --tail=10 app 2>/dev/null | grep -i "error\|exception\|failed" | tail -5
        
        return 1
    fi
    
    return 0
}

# 检查SSL证书
check_ssl_certificate() {
    log_info "检查SSL证书..."
    
    if [[ -f "ssl/cert.pem" ]] && [[ -f "ssl/key.pem" ]]; then
        # 检查证书有效期
        expiry_date=$(openssl x509 -in ssl/cert.pem -noout -enddate | cut -d= -f2)
        expiry_timestamp=$(date -d "$expiry_date" +%s)
        current_timestamp=$(date +%s)
        days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
        
        if [[ $days_until_expiry -gt 30 ]]; then
            log_success "SSL证书有效，还有 $days_until_expiry 天到期"
        elif [[ $days_until_expiry -gt 7 ]]; then
            log_warning "SSL证书还有 $days_until_expiry 天到期，建议更新"
        else
            log_error "SSL证书还有 $days_until_expiry 天到期，需要立即更新"
            return 1
        fi
    else
        log_error "SSL证书文件不存在"
        return 1
    fi
    
    return 0
}

# 检查备份状态
check_backup_status() {
    log_info "检查备份状态..."
    
    if [[ -d "backups" ]]; then
        backup_count=$(find backups -name "backup_*.sql.gz" -mtime -1 | wc -l)
        
        if [[ $backup_count -gt 0 ]]; then
            log_success "发现 $backup_count 个最近24小时内的备份"
            
            # 显示最新备份
            latest_backup=$(find backups -name "backup_*.sql.gz" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
            if [[ -n "$latest_backup" ]]; then
                backup_size=$(du -h "$latest_backup" | cut -f1)
                backup_time=$(stat -c %y "$latest_backup" | cut -d. -f1)
                log_info "最新备份: $latest_backup ($backup_size, $backup_time)"
            fi
        else
            log_warning "没有发现最近24小时内的备份"
        fi
    else
        log_warning "备份目录不存在"
    fi
    
    return 0
}

# 性能测试
performance_test() {
    log_info "执行简单性能测试..."
    
    # 测试API响应时间
    api_response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost/health)
    api_response_ms=$(echo "$api_response_time * 1000" | bc)
    
    if (( $(echo "$api_response_time < 1.0" | bc -l) )); then
        log_success "API响应时间: ${api_response_ms}ms"
    elif (( $(echo "$api_response_time < 2.0" | bc -l) )); then
        log_warning "API响应时间: ${api_response_ms}ms (较慢)"
    else
        log_error "API响应时间: ${api_response_ms}ms (过慢)"
        return 1
    fi
    
    return 0
}

# 生成健康检查报告
generate_report() {
    log_info "生成健康检查报告..."
    
    report_file="health_check_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "财务助手系统健康检查报告"
        echo "生成时间: $(date)"
        echo "================================"
        echo
        
        echo "服务状态:"
        docker-compose -f docker-compose.prod.yml ps
        echo
        
        echo "系统资源使用:"
        echo "内存使用:"
        free -h
        echo
        echo "磁盘使用:"
        df -h
        echo
        echo "CPU负载:"
        uptime
        echo
        
        echo "容器资源使用:"
        docker stats --no-stream
        echo
        
        echo "最近的应用日志:"
        docker-compose -f docker-compose.prod.yml logs --tail=20 app
        
    } > "$report_file"
    
    log_success "健康检查报告已生成: $report_file"
}

# 主函数
main() {
    log_info "开始系统健康检查..."
    echo "检查时间: $(date)"
    echo "================================"
    
    failed_checks=0
    
    # 执行各项检查
    check_service_status || ((failed_checks++))
    echo
    
    check_http_endpoints || ((failed_checks++))
    echo
    
    check_database || ((failed_checks++))
    echo
    
    check_redis || ((failed_checks++))
    echo
    
    check_disk_space || ((failed_checks++))
    echo
    
    check_memory_usage || ((failed_checks++))
    echo
    
    check_logs_for_errors || ((failed_checks++))
    echo
    
    check_ssl_certificate || ((failed_checks++))
    echo
    
    check_backup_status || ((failed_checks++))
    echo
    
    performance_test || ((failed_checks++))
    echo
    
    # 生成报告
    generate_report
    echo
    
    # 总结
    echo "================================"
    if [[ $failed_checks -eq 0 ]]; then
        log_success "所有健康检查通过！系统运行正常。"
        exit 0
    else
        log_error "有 $failed_checks 项检查失败，请检查系统状态。"
        exit 1
    fi
}

# 执行主函数
main "$@"