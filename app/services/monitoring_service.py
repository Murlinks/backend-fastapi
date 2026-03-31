"""
监控和告警服务
提供系统监控、性能指标收集、告警规则管理等功能
"""
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client import start_http_server as start_prometheus_server

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警数据类"""
    id: str
    severity: AlertSeverity
    title: str
    description: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        # HTTP请求指标
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint']
        )
        
        # 数据库指标
        self.db_query_duration = Histogram(
            'db_query_duration_seconds',
            'Database query duration',
            ['operation', 'table']
        )
        
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Active database connections'
        )
        
        # 缓存指标
        self.cache_hits = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type']
        )
        
        self.cache_misses = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_type']
        )
        
        self.cache_hit_rate = Gauge(
            'cache_hit_rate',
            'Cache hit rate',
            ['cache_type']
        )
        
        # 业务指标
        self.expenses_created = Counter(
            'expenses_created_total',
            'Total expenses created',
            ['category']
        )
        
        self.budgets_created = Counter(
            'budgets_created_total',
            'Total budgets created',
            ['category']
        )
        
        # AI服务指标
        self.ai_requests_total = Counter(
            'ai_requests_total',
            'Total AI requests',
            ['service', 'operation']
        )
        
        self.ai_request_duration = Histogram(
            'ai_request_duration_seconds',
            'AI request duration',
            ['service', 'operation']
        )
        
        self.ai_errors = Counter(
            'ai_errors_total',
            'Total AI errors',
            ['service', 'error_type']
        )
        
        # 系统指标
        self.system_memory_usage = Gauge(
            'system_memory_usage_bytes',
            'System memory usage'
        )
        
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage'
        )
        
        # 自定义指标
        self.custom_metrics = {}
    
    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float
    ):
        """记录HTTP请求"""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_db_query(
        self,
        operation: str,
        table: str,
        duration: float
    ):
        """记录数据库查询"""
        self.db_query_duration.labels(
            operation=operation,
            table=table
        ).observe(duration)
    
    def record_cache_hit(self, cache_type: str):
        """记录缓存命中"""
        self.cache_hits.labels(cache_type=cache_type).inc()
        self._update_cache_hit_rate(cache_type)
    
    def record_cache_miss(self, cache_type: str):
        """记录缓存未命中"""
        self.cache_misses.labels(cache_type=cache_type).inc()
        self._update_cache_hit_rate(cache_type)
    
    def _update_cache_hit_rate(self, cache_type: str):
        """更新缓存命中率"""
        hits = self.cache_hits.labels(cache_type=cache_type)._value.get()
        misses = self.cache_misses.labels(cache_type=cache_type)._value.get()
        
        if hits is not None and misses is not None:
            total = hits + misses
            if total > 0:
                rate = hits / total
                self.cache_hit_rate.labels(cache_type=cache_type).set(rate)
    
    def record_expense_created(self, category: str):
        """记录支出创建"""
        self.expenses_created.labels(category=category).inc()
    
    def record_budget_created(self, category: str):
        """记录预算创建"""
        self.budgets_created.labels(category=category).inc()
    
    def record_ai_request(
        self,
        service: str,
        operation: str,
        duration: float
    ):
        """记录AI请求"""
        self.ai_requests_total.labels(
            service=service,
            operation=operation
        ).inc()
        
        self.ai_request_duration.labels(
            service=service,
            operation=operation
        ).observe(duration)
    
    def record_ai_error(
        self,
        service: str,
        error_type: str
    ):
        """记录AI错误"""
        self.ai_errors.labels(
            service=service,
            error_type=error_type
        ).inc()
    
    def update_system_metrics(self):
        """更新系统指标"""
        import psutil
        import os
        
        # 内存使用
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        self.system_memory_usage.set(memory_info.rss)
        
        # CPU使用
        cpu_percent = process.cpu_percent()
        self.system_cpu_usage.set(cpu_percent)


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_handlers: List[Callable[[Alert], None]] = []
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_rules = self._init_default_rules()
    
    def _init_default_rules(self) -> Dict[str, Dict[str, Any]]:
        """初始化默认告警规则"""
        return {
            "high_error_rate": {
                "enabled": True,
                "severity": AlertSeverity.ERROR,
                "metric": "http_requests_total",
                "condition": "error_rate > 0.05",
                "threshold": 0.05,
                "window": "5m",
                "description": "错误率超过5%"
            },
            "slow_response_time": {
                "enabled": True,
                "severity": AlertSeverity.WARNING,
                "metric": "http_request_duration_seconds",
                "condition": "p95 > 1.0",
                "threshold": 1.0,
                "window": "5m",
                "description": "P95响应时间超过1秒"
            },
            "high_memory_usage": {
                "enabled": True,
                "severity": AlertSeverity.WARNING,
                "metric": "system_memory_usage_bytes",
                "condition": "usage > 0.8",
                "threshold": 0.8,
                "window": "1m",
                "description": "内存使用率超过80%"
            },
            "high_cpu_usage": {
                "enabled": True,
                "severity": AlertSeverity.WARNING,
                "metric": "system_cpu_usage_percent",
                "condition": "usage > 0.8",
                "threshold": 0.8,
                "window": "1m",
                "description": "CPU使用率超过80%"
            },
            "cache_low_hit_rate": {
                "enabled": True,
                "severity": AlertSeverity.INFO,
                "metric": "cache_hit_rate",
                "condition": "rate < 0.7",
                "threshold": 0.7,
                "window": "5m",
                "description": "缓存命中率低于70%"
            },
            "ai_service_error": {
                "enabled": True,
                "severity": AlertSeverity.ERROR,
                "metric": "ai_errors_total",
                "condition": "errors > 10",
                "threshold": 10,
                "window": "1m",
                "description": "AI服务错误数超过10"
            }
        }
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    def remove_alert_handler(self, handler: Callable[[Alert], None]):
        """移除告警处理器"""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)
    
    def check_alerts(self, metrics: Dict[str, float]):
        """检查告警条件"""
        for rule_name, rule in self.alert_rules.items():
            if not rule["enabled"]:
                continue
            
            try:
                if self._evaluate_rule(rule, metrics):
                    alert = Alert(
                        id=f"{rule_name}_{int(time.time())}",
                        severity=rule["severity"],
                        title=f"告警: {rule['description']}",
                        description=rule["description"],
                        metric_name=rule["metric"],
                        current_value=metrics.get(rule["metric"], 0),
                        threshold=rule["threshold"],
                        metadata={"rule_name": rule_name}
                    )
                    
                    self._trigger_alert(alert)
            except Exception as e:
                logger.error(f"检查告警规则{rule_name}失败: {e}")
    
    def _evaluate_rule(
        self,
        rule: Dict[str, Any],
        metrics: Dict[str, float]
    ) -> bool:
        """评估告警规则"""
        metric_name = rule["metric"]
        threshold = rule["threshold"]
        condition = rule["condition"]
        
        if metric_name not in metrics:
            return False
        
        current_value = metrics[metric_name]
        
        # 简单的阈值比较
        if ">" in condition:
            return current_value > threshold
        elif "<" in condition:
            return current_value < threshold
        elif ">=" in condition:
            return current_value >= threshold
        elif "<=" in condition:
            return current_value <= threshold
        elif "==" in condition:
            return current_value == threshold
        
        return False
    
    def _trigger_alert(self, alert: Alert):
        """触发告警"""
        # 添加到当前告警列表
        self.alerts.append(alert)
        
        # 添加到历史记录
        self.alert_history.append(alert)
        
        # 调用所有告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")
        
        # 记录日志
        logger.warning(
            f"告警触发: {alert.title} - {alert.description} "
            f"(当前值: {alert.current_value}, 阈值: {alert.threshold})"
        )
    
    def get_active_alerts(self) -> List[Alert]:
        """获取当前活跃的告警"""
        return self.alerts
    
    def get_alert_history(
        self,
        limit: int = 100
    ) -> List[Alert]:
        """获取告警历史"""
        return list(self.alert_history)[-limit:]
    
    def clear_alert(self, alert_id: str):
        """清除告警"""
        self.alerts = [a for a in self.alerts if a.id != alert_id]
    
    def clear_all_alerts(self):
        """清除所有告警"""
        self.alerts.clear()


class MonitoringService:
    """监控服务"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
    
    async def start(self, prometheus_port: int = 9090):
        """启动监控服务"""
        if self.running:
            logger.warning("监控服务已经在运行")
            return
        
        logger.info("启动监控服务...")
        
        # 启动Prometheus HTTP服务器
        try:
            start_prometheus_server(prometheus_port)
            logger.info(f"Prometheus指标服务器启动在端口{prometheus_port}")
        except Exception as e:
            logger.error(f"启动Prometheus服务器失败: {e}")
        
        # 启动监控任务
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info("监控服务启动成功")
    
    async def stop(self):
        """停止监控服务"""
        if not self.running:
            return
        
        logger.info("停止监控服务...")
        self.running = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("监控服务已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                # 更新系统指标
                self.metrics_collector.update_system_metrics()
                
                # 收集指标并检查告警
                metrics = self._collect_metrics()
                self.alert_manager.check_alerts(metrics)
                
                # 等待下一次检查
                await asyncio.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(60)
    
    def _collect_metrics(self) -> Dict[str, float]:
        """收集当前指标"""
        metrics = {}
        
        # 收集HTTP请求指标
        metrics["http_requests_total"] = sum(
            metric._value.get() or 0
            for metric in self.metrics_collector.http_requests_total.collect()
        )
        
        # 收集系统指标
        metrics["system_memory_usage_bytes"] = self.metrics_collector.system_memory_usage._value.get()
        metrics["system_cpu_usage_percent"] = self.metrics_collector.system_cpu_usage._value.get()
        
        # 收集缓存指标
        for cache_type in ["user_expenses", "budget_summary", "ai_response"]:
            hits = self.metrics_collector.cache_hits.labels(cache_type=cache_type)._value.get() or 0
            misses = self.metrics_collector.cache_misses.labels(cache_type=cache_type)._value.get() or 0
            total = hits + misses
            if total > 0:
                metrics[f"cache_hit_rate_{cache_type}"] = hits / total
        
        return metrics
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return {
            "active_alerts": len(self.alert_manager.get_active_alerts()),
            "recent_alerts": len([
                a for a in self.alert_manager.get_alert_history(100)
                if a.timestamp > datetime.utcnow() - timedelta(hours=1)
            ]),
            "metrics": self._collect_metrics(),
            "alert_rules_status": {
                name: rule["enabled"]
                for name, rule in self.alert_manager.alert_rules.items()
            }
        }
    
    def get_alerts_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        active_alerts = self.alert_manager.get_active_alerts()
        recent_alerts = self.alert_manager.get_alert_history(100)
        
        # 按严重级别分组
        by_severity = {}
        for alert in active_alerts:
            severity = alert.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(alert)
        
        return {
            "total_active": len(active_alerts),
            "by_severity": {
                severity: len(alerts)
                for severity, alerts in by_severity.items()
            },
            "recent_count": len([
                a for a in recent_alerts
                if a.timestamp > datetime.utcnow() - timedelta(hours=24)
            ]),
            "alerts": [
                {
                    "id": alert.id,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "description": alert.description,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in active_alerts[-10:]  # 最近10个告警
            ]
        }


# 全局监控服务实例
monitoring_service = MonitoringService()