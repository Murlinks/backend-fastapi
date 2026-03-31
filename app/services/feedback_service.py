"""
用户反馈服务
提供用户反馈收集、分类、分析和处理功能
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """反馈类型"""
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    IMPROVEMENT = "improvement"
    COMPLAINT = "complaint"
    COMPLIMENT = "compliment"
    OTHER = "other"


class FeedbackStatus(Enum):
    """反馈状态"""
    PENDING = "pending"
    REVIEWING = "reviewing"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class FeedbackPriority(Enum):
    """反馈优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Feedback:
    """反馈数据类"""
    id: str
    user_id: str
    type: FeedbackType
    title: str
    description: str
    status: FeedbackStatus = FeedbackStatus.PENDING
    priority: FeedbackPriority = FeedbackPriority.MEDIUM
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    device_info: Optional[Dict[str, Any]] = None
    app_version: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeedbackAnalyzer:
    """反馈分析器"""
    
    def __init__(self):
        self.keyword_categories = {
            "ui": ["界面", "UI", "布局", "颜色", "字体", "按钮", "导航"],
            "performance": ["慢", "卡顿", "响应", "性能", "加载", "速度"],
            "feature": ["功能", "特性", "新增", "添加", "支持", "实现"],
            "bug": ["错误", "异常", "崩溃", "失败", "问题", "故障"],
            "ai": ["AI", "智能", "预测", "分析", "推荐", "识别"],
            "voice": ["语音", "说话", "录音", "识别", "听写"],
            "sync": ["同步", "云端", "备份", "数据", "多设备"]
        }
    
    def categorize_feedback(self, feedback: Feedback) -> str:
        """自动分类反馈"""
        text = f"{feedback.title} {feedback.description}".lower()
        
        category_scores = {}
        for category, keywords in self.keyword_categories.items():
            score = sum(1 for keyword in keywords if keyword.lower() in text)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return "other"
    
    def extract_tags(self, feedback: Feedback) -> List[str]:
        """提取标签"""
        text = f"{feedback.title} {feedback.description}".lower()
        tags = []
        
        for category, keywords in self.keyword_categories.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    tags.append(category)
                    break
        
        return list(set(tags))
    
    def determine_priority(self, feedback: Feedback) -> FeedbackPriority:
        """确定优先级"""
        text = f"{feedback.title} {feedback.description}".lower()
        
        # 关键词匹配
        critical_keywords = ["崩溃", "无法使用", "严重", "紧急", "数据丢失"]
        high_keywords = ["错误", "失败", "问题", "重要", "急需"]
        
        for keyword in critical_keywords:
            if keyword in text:
                return FeedbackPriority.CRITICAL
        
        for keyword in high_keywords:
            if keyword in text:
                return FeedbackPriority.HIGH
        
        # 根据反馈类型确定优先级
        if feedback.type == FeedbackType.BUG_REPORT:
            return FeedbackPriority.HIGH
        elif feedback.type == FeedbackType.FEATURE_REQUEST:
            return FeedbackPriority.MEDIUM
        elif feedback.type == FeedbackType.COMPLAINT:
            return FeedbackPriority.HIGH
        
        return FeedbackPriority.MEDIUM
    
    def analyze_sentiment(self, feedback: Feedback) -> str:
        """分析情感倾向"""
        text = f"{feedback.title} {feedback.description}".lower()
        
        positive_keywords = ["好", "优秀", "棒", "喜欢", "满意", "方便", "实用"]
        negative_keywords = ["差", "不好", "糟糕", "失望", "不满", "难用", "麻烦"]
        
        positive_score = sum(1 for keyword in positive_keywords if keyword in text)
        negative_score = sum(1 for keyword in negative_keywords if keyword in text)
        
        if positive_score > negative_score:
            return "positive"
        elif negative_score > positive_score:
            return "negative"
        else:
            return "neutral"


class FeedbackService:
    """用户反馈服务"""
    
    def __init__(self):
        self.analyzer = FeedbackAnalyzer()
        self.feedback_store: Dict[str, Feedback] = {}
        self.feedback_history: List[Feedback] = []
    
    async def submit_feedback(
        self,
        user_id: str,
        feedback_type: str,
        title: str,
        description: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        screenshots: Optional[List[str]] = None,
        device_info: Optional[Dict[str, Any]] = None,
        app_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        提交用户反馈
        
        Args:
            user_id: 用户ID
            feedback_type: 反馈类型
            title: 反馈标题
            description: 反馈描述
            category: 反馈分类
            tags: 标签
            screenshots: 截图URL列表
            device_info: 设备信息
            app_version: 应用版本
            metadata: 额外元数据
        
        Returns:
            反馈提交结果
        """
        try:
            # 创建反馈对象
            feedback = Feedback(
                id=self._generate_feedback_id(),
                user_id=user_id,
                type=FeedbackType(feedback_type),
                title=title,
                description=description,
                category=category,
                tags=tags or [],
                screenshots=screenshots or [],
                device_info=device_info,
                app_version=app_version,
                metadata=metadata or {}
            )
            
            # 自动分类和标记
            if not feedback.category:
                feedback.category = self.analyzer.categorize_feedback(feedback)
            
            if not feedback.tags:
                feedback.tags = self.analyzer.extract_tags(feedback)
            
            # 确定优先级
            feedback.priority = self.analyzer.determine_priority(feedback)
            
            # 存储反馈
            self.feedback_store[feedback.id] = feedback
            self.feedback_history.append(feedback)
            
            # 记录日志
            logger.info(
                f"收到用户反馈: {feedback.id} - {feedback.title} "
                f"(用户: {user_id}, 类型: {feedback.type.value}, "
                f"优先级: {feedback.priority.value})"
            )
            
            # 触发通知（这里可以集成邮件、Slack等）
            await self._notify_new_feedback(feedback)
            
            return {
                "success": True,
                "feedback_id": feedback.id,
                "message": "感谢您的反馈，我们会尽快处理"
            }
            
        except Exception as e:
            logger.error(f"提交反馈失败: {e}")
            return {
                "success": False,
                "error": f"提交反馈失败: {str(e)}"
            }
    
    async def get_feedback(
        self,
        feedback_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取反馈详情"""
        feedback = self.feedback_store.get(feedback_id)
        if not feedback:
            return None
        
        return self._feedback_to_dict(feedback)
    
    async def list_feedback(
        self,
        user_id: Optional[str] = None,
        feedback_type: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        列出反馈
        
        Args:
            user_id: 用户ID过滤
            feedback_type: 反馈类型过滤
            status: 状态过滤
            priority: 优先级过滤
            category: 分类过滤
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            反馈列表
        """
        filtered_feedbacks = self.feedback_history
        
        # 应用过滤条件
        if user_id:
            filtered_feedbacks = [
                f for f in filtered_feedbacks
                if f.user_id == user_id
            ]
        
        if feedback_type:
            filtered_feedbacks = [
                f for f in filtered_feedbacks
                if f.type.value == feedback_type
            ]
        
        if status:
            filtered_feedbacks = [
                f for f in filtered_feedbacks
                if f.status.value == status
            ]
        
        if priority:
            filtered_feedbacks = [
                f for f in filtered_feedbacks
                if f.priority.value == priority
            ]
        
        if category:
            filtered_feedbacks = [
                f for f in filtered_feedbacks
                if f.category == category
            ]
        
        # 排序（按创建时间倒序）
        filtered_feedbacks.sort(
            key=lambda x: x.created_at,
            reverse=True
        )
        
        # 分页
        total = len(filtered_feedbacks)
        feedbacks = filtered_feedbacks[offset:offset + limit]
        
        return {
            "success": True,
            "total": total,
            "offset": offset,
            "limit": limit,
            "feedbacks": [
                self._feedback_to_dict(f)
                for f in feedbacks
            ]
        }
    
    async def update_feedback_status(
        self,
        feedback_id: str,
        status: str,
        resolution: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新反馈状态
        
        Args:
            feedback_id: 反馈ID
            status: 新状态
            resolution: 解决方案说明
        
        Returns:
            更新结果
        """
        feedback = self.feedback_store.get(feedback_id)
        if not feedback:
            return {
                "success": False,
                "error": "反馈不存在"
            }
        
        try:
            feedback.status = FeedbackStatus(status)
            feedback.updated_at = datetime.utcnow()
            
            if status == "resolved" and resolution:
                feedback.resolution = resolution
                feedback.resolved_at = datetime.utcnow()
            
            logger.info(
                f"反馈状态更新: {feedback_id} -> {status}"
            )
            
            # 通知用户
            await self._notify_status_update(feedback)
            
            return {
                "success": True,
                "message": "反馈状态已更新"
            }
            
        except Exception as e:
            logger.error(f"更新反馈状态失败: {e}")
            return {
                "success": False,
                "error": f"更新失败: {str(e)}"
            }
    
    async def get_feedback_statistics(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取反馈统计信息
        
        Args:
            days: 统计天数
        
        Returns:
            统计信息
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_feedbacks = [
            f for f in self.feedback_history
            if f.created_at >= cutoff_date
        ]
        
        # 按类型统计
        by_type = {}
        for feedback in recent_feedbacks:
            type_name = feedback.type.value
            if type_name not in by_type:
                by_type[type_name] = 0
            by_type[type_name] += 1
        
        # 按状态统计
        by_status = {}
        for feedback in recent_feedbacks:
            status_name = feedback.status.value
            if status_name not in by_status:
                by_status[status_name] = 0
            by_status[status_name] += 1
        
        # 按优先级统计
        by_priority = {}
        for feedback in recent_feedbacks:
            priority_name = feedback.priority.value
            if priority_name not in by_priority:
                by_priority[priority_name] = 0
            by_priority[priority_name] += 1
        
        # 按分类统计
        by_category = {}
        for feedback in recent_feedbacks:
            category = feedback.category or "other"
            if category not in by_category:
                by_category[category] = 0
            by_category[category] += 1
        
        # 计算解决率
        resolved_count = sum(
            1 for f in recent_feedbacks
            if f.status == FeedbackStatus.RESOLVED
        )
        resolution_rate = resolved_count / len(recent_feedbacks) if recent_feedbacks else 0
        
        return {
            "success": True,
            "period_days": days,
            "total_feedbacks": len(recent_feedbacks),
            "by_type": by_type,
            "by_status": by_status,
            "by_priority": by_priority,
            "by_category": by_category,
            "resolution_rate": resolution_rate
        }
    
    async def get_feedback_trends(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取反馈趋势
        
        Args:
            days: 统计天数
        
        Returns:
            趋势数据
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 按天统计
        daily_counts = {}
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            daily_counts[date.isoformat()] = 0
        
        for feedback in self.feedback_history:
            if feedback.created_at >= cutoff_date:
                date = feedback.created_at.date().isoformat()
                if date in daily_counts:
                    daily_counts[date] += 1
        
        # 按类型趋势
        type_trends = {}
        for feedback in self.feedback_history:
            if feedback.created_at >= cutoff_date:
                type_name = feedback.type.value
                if type_name not in type_trends:
                    type_trends[type_name] = 0
                type_trends[type_name] += 1
        
        return {
            "success": True,
            "period_days": days,
            "daily_counts": daily_counts,
            "type_trends": type_trends
        }
    
    def _generate_feedback_id(self) -> str:
        """生成反馈ID"""
        import uuid
        return f"feedback_{uuid.uuid4().hex[:12]}"
    
    def _feedback_to_dict(self, feedback: Feedback) -> Dict[str, Any]:
        """将反馈对象转换为字典"""
        return {
            "id": feedback.id,
            "user_id": feedback.user_id,
            "type": feedback.type.value,
            "title": feedback.title,
            "description": feedback.description,
            "status": feedback.status.value,
            "priority": feedback.priority.value,
            "category": feedback.category,
            "tags": feedback.tags,
            "screenshots": feedback.screenshots,
            "device_info": feedback.device_info,
            "app_version": feedback.app_version,
            "created_at": feedback.created_at.isoformat(),
            "updated_at": feedback.updated_at.isoformat(),
            "resolved_at": feedback.resolved_at.isoformat() if feedback.resolved_at else None,
            "resolution": feedback.resolution,
            "metadata": feedback.metadata
        }
    
    async def _notify_new_feedback(self, feedback: Feedback):
        """通知新反馈"""
        # 这里可以集成邮件、Slack、钉钉等通知方式
        logger.info(f"新反馈通知: {feedback.id} - {feedback.title}")
    
    async def _notify_status_update(self, feedback: Feedback):
        """通知状态更新"""
        # 这里可以通知用户反馈状态已更新
        logger.info(f"反馈状态更新通知: {feedback.id} -> {feedback.status.value}")


# 全局反馈服务实例
feedback_service = FeedbackService()