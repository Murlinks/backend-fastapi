"""
财务预测和智能分析服务
提供支出预测、预算建议、消费模式分析等高级AI功能
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class FinancialPredictionService:
    """财务预测服务"""
    
    def __init__(self):
        self.prediction_window_days = 30  # 预测未来30天
        self.min_data_points = 5  # 最少需要5条数据才能进行预测
    
    async def predict_monthly_expense(
        self,
        expense_history: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        预测月度支出
        
        Args:
            expense_history: 历史支出记录
            user_profile: 用户画像信息
        
        Returns:
            包含预测结果的字典
        """
        try:
            if len(expense_history) < self.min_data_points:
                return {
                    "success": False,
                    "error": "历史数据不足，无法进行准确预测",
                    "min_required": self.min_data_points,
                    "current_count": len(expense_history)
                }
            
            # 按类别分组统计
            category_stats = self._analyze_by_category(expense_history)
            
            # 计算趋势
            trend_analysis = self._analyze_trend(expense_history)
            
            # 预测下月支出
            monthly_prediction = self._predict_next_month(expense_history, category_stats)
            
            # 生成建议
            recommendations = self._generate_budget_recommendations(
                category_stats,
                monthly_prediction,
                user_profile
            )
            
            return {
                "success": True,
                "prediction": {
                    "total_amount": monthly_prediction["total"],
                    "by_category": monthly_prediction["by_category"],
                    "confidence": monthly_prediction["confidence"],
                    "trend": trend_analysis["trend"],
                    "trend_percentage": trend_analysis["percentage"]
                },
                "category_analysis": category_stats,
                "recommendations": recommendations,
                "prediction_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"预测月度支出失败: {e}")
            return {
                "success": False,
                "error": f"预测失败: {str(e)}"
            }
    
    def _analyze_by_category(self, expenses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """按类别分析支出"""
        category_data = defaultdict(lambda: {
            "amounts": [],
            "count": 0,
            "recent": []
        })
        
        for expense in expenses:
            category = expense.get("category", "shopping")
            amount = Decimal(str(expense.get("amount", 0)))
            date = expense.get("created_at")
            
            category_data[category]["amounts"].append(amount)
            category_data[category]["count"] += 1
            if date:
                category_data[category]["recent"].append({
                    "amount": amount,
                    "date": date
                })
        
        # 计算统计信息
        result = {}
        for category, data in category_data.items():
            amounts = data["amounts"]
            if amounts:
                result[category] = {
                    "total": float(sum(amounts)),
                    "average": float(statistics.mean(amounts)),
                    "median": float(statistics.median(amounts)),
                    "min": float(min(amounts)),
                    "max": float(max(amounts)),
                    "std_dev": float(statistics.stdev(amounts)) if len(amounts) > 1 else 0,
                    "count": data["count"],
                    "volatility": self._calculate_volatility(amounts)
                }
        
        return result
    
    def _analyze_trend(self, expenses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析支出趋势"""
        # 按日期分组
        daily_totals = defaultdict(Decimal)
        for expense in expenses:
            date = expense.get("created_at", "").split("T")[0]
            amount = Decimal(str(expense.get("amount", 0)))
            daily_totals[date] += amount
        
        # 按时间排序
        sorted_dates = sorted(daily_totals.keys())
        if len(sorted_dates) < 2:
            return {"trend": "stable", "percentage": 0}
        
        # 计算趋势
        first_half = sum(daily_totals[date] for date in sorted_dates[:len(sorted_dates)//2])
        second_half = sum(daily_totals[date] for date in sorted_dates[len(sorted_dates)//2:])
        
        if first_half == 0:
            trend = "increasing"
            percentage = 100
        else:
            change = ((second_half - first_half) / first_half) * 100
            if change > 10:
                trend = "increasing"
            elif change < -10:
                trend = "decreasing"
            else:
                trend = "stable"
            percentage = float(change)
        
        return {
            "trend": trend,
            "percentage": percentage
        }
    
    def _predict_next_month(
        self,
        expenses: List[Dict[str, Any]],
        category_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """预测下月支出"""
        # 计算总支出预测
        total_prediction = 0
        by_category = {}
        
        for category, stats in category_stats.items():
            # 使用加权平均：最近的数据权重更高
            avg = Decimal(str(stats["average"]))
            volatility = Decimal(str(stats["volatility"]))
            
            # 考虑波动性调整预测
            adjusted_prediction = avg * (1 + volatility * 0.1)
            
            by_category[category] = {
                "predicted_amount": float(adjusted_prediction),
                "confidence": max(0.5, 1 - volatility),
                "based_on": stats["count"]
            }
            
            total_prediction += adjusted_prediction
        
        # 计算总体置信度
        confidence = statistics.mean([cat["confidence"] for cat in by_category.values()])
        
        return {
            "total": float(total_prediction),
            "by_category": by_category,
            "confidence": float(confidence)
        }
    
    def _calculate_volatility(self, amounts: List[Decimal]) -> float:
        """计算波动性"""
        if len(amounts) < 2:
            return 0.0
        
        mean = statistics.mean(amounts)
        if mean == 0:
            return 0.0
        
        std_dev = statistics.stdev(amounts)
        return float(std_dev / mean)
    
    def _generate_budget_recommendations(
        self,
        category_stats: Dict[str, Any],
        prediction: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]]
    ) -> List[str]:
        """生成预算建议"""
        recommendations = []
        
        # 找出高波动性类别
        high_volatility = [
            cat for cat, stats in category_stats.items()
            if stats["volatility"] > 0.5
        ]
        if high_volatility:
            recommendations.append(
                f"建议关注{', '.join(high_volatility)}类别的支出，"
                f"这些类别的支出波动较大，可以考虑设置更严格的预算控制。"
            )
        
        # 找出高支出类别
        high_spending = sorted(
            category_stats.items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )[:2]
        if high_spending:
            top_category = high_spending[0][0]
            recommendations.append(
                f"{top_category}是您的最大支出类别，"
                f"建议检查是否可以优化相关消费。"
            )
        
        # 根据趋势给出建议
        if prediction["trend"] == "increasing":
            recommendations.append(
                "您的支出呈上升趋势，建议重新评估预算设置，"
                "考虑削减非必要开支。"
            )
        elif prediction["trend"] == "decreasing":
            recommendations.append(
                "您的支出呈下降趋势，继续保持良好的消费习惯！"
            )
        
        return recommendations


class AnomalyDetectionService:
    """异常支出检测服务"""
    
    def __init__(self):
        self.anomaly_threshold = 2.0  # 标准差倍数
        self.min_history = 10  # 最少历史记录数
    
    async def detect_anomalies(
        self,
        expense_history: List[Dict[str, Any]],
        new_expense: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        检测异常支出
        
        Args:
            expense_history: 历史支出记录
            new_expense: 新的支出记录（可选）
        
        Returns:
            包含异常检测结果和警告的字典
        """
        try:
            if len(expense_history) < self.min_history:
                return {
                    "success": True,
                    "has_anomalies": False,
                    "message": "历史数据不足，无法进行异常检测",
                    "anomalies": []
                }
            
            anomalies = []
            warnings = []
            
            # 检测历史记录中的异常
            historical_anomalies = self._detect_historical_anomalies(expense_history)
            anomalies.extend(historical_anomalies)
            
            # 如果有新支出，检测是否异常
            if new_expense:
                new_anomaly = self._check_new_expense(expense_history, new_expense)
                if new_anomaly:
                    anomalies.append(new_anomaly)
                    warnings.append(
                        f"检测到异常支出：{new_expense.get('description')} "
                        f"金额为{new_expense.get('amount')}元，"
                        f"超出该类别正常范围。"
                    )
            
            # 生成总体评估
            risk_level = self._assess_risk_level(anomalies, len(expense_history))
            
            return {
                "success": True,
                "has_anomalies": len(anomalies) > 0,
                "risk_level": risk_level,
                "anomalies": anomalies,
                "warnings": warnings,
                "total_expenses": len(expense_history),
                "anomaly_count": len(anomalies),
                "detection_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            return {
                "success": False,
                "error": f"检测失败: {str(e)}"
            }
    
    def _detect_historical_anomalies(self, expenses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测历史记录中的异常"""
        anomalies = []
        
        # 按类别分组
        category_expenses = defaultdict(list)
        for expense in expenses:
            category = expense.get("category", "shopping")
            amount = Decimal(str(expense.get("amount", 0)))
            category_expenses[category].append({
                "amount": amount,
                "description": expense.get("description", ""),
                "date": expense.get("created_at", "")
            })
        
        # 对每个类别进行异常检测
        for category, items in category_expenses.items():
            if len(items) < 3:
                continue
            
            amounts = [item["amount"] for item in items]
            mean = statistics.mean(amounts)
            std_dev = statistics.stdev(amounts) if len(amounts) > 1 else 0
            
            if std_dev == 0:
                continue
            
            threshold = mean + (std_dev * self.anomaly_threshold)
            
            for item in items:
                if item["amount"] > threshold:
                    anomalies.append({
                        "type": "high_amount",
                        "category": category,
                        "amount": float(item["amount"]),
                        "description": item["description"],
                        "date": item["date"],
                        "expected_range": f"{float(mean - std_dev):.2f} - {float(mean + std_dev):.2f}",
                        "deviation": float((item["amount"] - mean) / std_dev)
                    })
        
        return anomalies
    
    def _check_new_expense(
        self,
        expense_history: List[Dict[str, Any]],
        new_expense: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """检查新支出是否异常"""
        category = new_expense.get("category", "shopping")
        new_amount = Decimal(str(new_expense.get("amount", 0)))
        
        # 获取同类别的历史支出
        category_amounts = [
            Decimal(str(exp.get("amount", 0)))
            for exp in expense_history
            if exp.get("category") == category
        ]
        
        if len(category_amounts) < 3:
            return None
        
        mean = statistics.mean(category_amounts)
        std_dev = statistics.stdev(category_amounts) if len(category_amounts) > 1 else 0
        
        if std_dev == 0:
            return None
        
        # 检查是否超出阈值
        if new_amount > mean + (std_dev * self.anomaly_threshold):
            return {
                "type": "new_expense",
                "category": category,
                "amount": float(new_amount),
                "description": new_expense.get("description", ""),
                "expected_range": f"{float(mean - std_dev):.2f} - {float(mean + std_dev):.2f}",
                "deviation": float((new_amount - mean) / std_dev)
            }
        
        return None
    
    def _assess_risk_level(self, anomalies: List[Dict[str, Any]], total_expenses: int) -> str:
        """评估风险等级"""
        if not anomalies:
            return "low"
        
        anomaly_ratio = len(anomalies) / total_expenses
        
        if anomaly_ratio > 0.2:
            return "high"
        elif anomaly_ratio > 0.1:
            return "medium"
        else:
            return "low"


class ConsumptionPatternAnalyzer:
    """消费模式分析服务"""
    
    async def analyze_consumption_pattern(
        self,
        expense_history: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析消费模式
        
        Args:
            expense_history: 历史支出记录
            user_profile: 用户画像信息
        
        Returns:
            包含消费模式分析的字典
        """
        try:
            if not expense_history:
                return {
                    "success": False,
                    "error": "没有消费数据可供分析"
                }
            
            # 时间模式分析
            time_pattern = self._analyze_time_pattern(expense_history)
            
            # 周期性分析
            periodicity = self._analyze_periodicity(expense_history)
            
            # 消费习惯分析
            habits = self._analyze_habits(expense_history)
            
            # 消费画像
            profile = self._build_consumption_profile(expense_history, user_profile)
            
            # 优化建议
            suggestions = self._generate_optimization_suggestions(
                time_pattern,
                periodicity,
                habits,
                profile
            )
            
            return {
                "success": True,
                "time_pattern": time_pattern,
                "periodicity": periodicity,
                "habits": habits,
                "profile": profile,
                "suggestions": suggestions,
                "analysis_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"消费模式分析失败: {e}")
            return {
                "success": False,
                "error": f"分析失败: {str(e)}"
            }
    
    def _analyze_time_pattern(self, expenses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析时间模式"""
        # 按小时统计
        hourly_stats = defaultdict(lambda: {"count": 0, "amount": Decimal(0)})
        
        # 按星期几统计
        daily_stats = defaultdict(lambda: {"count": 0, "amount": Decimal(0)})
        
        for expense in expenses:
            try:
                date_str = expense.get("created_at", "")
                if not date_str:
                    continue
                
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                
                hour = date.hour
                weekday = date.weekday()  # 0=Monday, 6=Sunday
                
                amount = Decimal(str(expense.get("amount", 0)))
                
                hourly_stats[hour]["count"] += 1
                hourly_stats[hour]["amount"] += amount
                
                daily_stats[weekday]["count"] += 1
                daily_stats[weekday]["amount"] += amount
                
            except Exception as e:
                logger.warning(f"解析日期失败: {e}")
                continue
        
        # 找出高峰时段
        peak_hours = sorted(
            hourly_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:3]
        
        peak_days = sorted(
            daily_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:3]
        
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        
        return {
            "peak_hours": [
                {"hour": h, "count": d["count"], "amount": float(d["amount"])}
                for h, d in peak_hours
            ],
            "peak_days": [
                {"day": weekday_names[d], "count": s["count"], "amount": float(s["amount"])}
                for d, s in peak_days
            ],
            "hourly_distribution": {
                str(h): {"count": d["count"], "amount": float(d["amount"])}
                for h, d in hourly_stats.items()
            },
            "daily_distribution": {
                weekday_names[d]: {"count": s["count"], "amount": float(s["amount"])}
                for d, s in daily_stats.items()
            }
        }
    
    def _analyze_periodicity(self, expenses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析周期性"""
        # 按类别分析周期性
        category_patterns = {}
        
        for category in set(exp.get("category", "shopping") for exp in expenses):
            category_expenses = [
                exp for exp in expenses
                if exp.get("category") == category
            ]
            
            if len(category_expenses) < 3:
                continue
            
            # 分析支出间隔
            dates = []
            for exp in category_expenses:
                try:
                    date_str = exp.get("created_at", "")
                    if date_str:
                        dates.append(datetime.fromisoformat(date_str.replace("Z", "+00:00")))
                except:
                    continue
            
            if len(dates) < 2:
                continue
            
            dates.sort()
            intervals = []
            for i in range(1, len(dates)):
                interval = (dates[i] - dates[i-1]).days
                intervals.append(interval)
            
            if intervals:
                avg_interval = statistics.mean(intervals)
                std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
                
                # 判断周期性
                if std_interval / avg_interval < 0.3:  # 低变异度
                    period_type = "regular"
                elif std_interval / avg_interval < 0.6:
                    period_type = "semi_regular"
                else:
                    period_type = "irregular"
                
                category_patterns[category] = {
                    "average_interval_days": float(avg_interval),
                    "periodicity": period_type,
                    "frequency": len(category_expenses)
                }
        
        return category_patterns
    
    def _analyze_habits(self, expenses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析消费习惯"""
        # 类别偏好
        category_preference = defaultdict(lambda: {"count": 0, "amount": Decimal(0)})
        
        # 金额分布
        amount_ranges = {
            "small": (0, 50),
            "medium": (50, 200),
            "large": (200, 500),
            "extra_large": (500, float('inf'))
        }
        
        amount_distribution = defaultdict(int)
        
        for expense in expenses:
            category = expense.get("category", "shopping")
            amount = Decimal(str(expense.get("amount", 0)))
            
            category_preference[category]["count"] += 1
            category_preference[category]["amount"] += amount
            
            # 统计金额分布
            for range_name, (min_amt, max_amt) in amount_ranges.items():
                if min_amt <= float(amount) < max_amt:
                    amount_distribution[range_name] += 1
                    break
        
        # 计算类别偏好
        total_expenses = len(expenses)
        category_scores = {}
        for category, data in category_preference.items():
            score = (data["count"] / total_expenses) * 100
            category_scores[category] = {
                "frequency": float(score),
                "total_amount": float(data["amount"]),
                "average_amount": float(data["amount"] / data["count"]) if data["count"] > 0 else 0
            }
        
        return {
            "category_preference": category_scores,
            "amount_distribution": dict(amount_distribution),
            "most_frequent_category": max(category_scores.items(), key=lambda x: x[1]["frequency"])[0] if category_scores else None,
            "highest_spending_category": max(category_scores.items(), key=lambda x: x[1]["total_amount"])[0] if category_scores else None
        }
    
    def _build_consumption_profile(
        self,
        expenses: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """构建消费画像"""
        total_amount = sum(Decimal(str(exp.get("amount", 0))) for exp in expenses)
        avg_amount = total_amount / len(expenses) if expenses else 0
        
        # 消费类型
        category_types = set(exp.get("category", "shopping") for exp in expenses)
        
        # 消费多样性
        diversity_score = len(category_types) / 5.0  # 假设最多5个主要类别
        
        # 消费稳定性
        amounts = [Decimal(str(exp.get("amount", 0))) for exp in expenses]
        stability_score = 1.0
        if len(amounts) > 1:
            std_dev = statistics.stdev(amounts)
            mean = statistics.mean(amounts)
            if mean > 0:
                stability_score = 1.0 - min(1.0, std_dev / mean)
        
        return {
            "total_expenses": float(total_amount),
            "average_expense": float(avg_amount),
            "expense_count": len(expenses),
            "category_diversity": float(diversity_score),
            "stability_score": float(stability_score),
            "consumption_type": self._classify_consumption_type(diversity_score, stability_score)
        }
    
    def _classify_consumption_type(self, diversity: float, stability: float) -> str:
        """分类消费类型"""
        if diversity > 0.6 and stability > 0.7:
            return "balanced"
        elif diversity > 0.6:
            return "diverse"
        elif stability > 0.7:
            return "focused"
        else:
            return "irregular"
    
    def _generate_optimization_suggestions(
        self,
        time_pattern: Dict[str, Any],
        periodicity: Dict[str, Any],
        habits: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        # 基于时间模式的建议
        if time_pattern.get("peak_hours"):
            peak_hour = time_pattern["peak_hours"][0]["hour"]
            if 9 <= peak_hour <= 11:
                suggestions.append("您经常在上午9-11点消费，建议检查是否可以提前规划，避免冲动消费。")
            elif 12 <= peak_hour <= 14:
                suggestions.append("午餐时间是您的消费高峰，可以考虑自带午餐或选择更经济的餐饮选择。")
        
        # 基于周期性的建议
        regular_categories = [
            cat for cat, data in periodicity.items()
            if data.get("periodicity") == "regular"
        ]
        if regular_categories:
            suggestions.append(
                f"您在{', '.join(regular_categories)}类别上有规律的支出，"
                f"可以考虑设置自动预算提醒。"
            )
        
        # 基于消费习惯的建议
        if habits.get("most_frequent_category") == habits.get("highest_spending_category"):
            category = habits["most_frequent_category"]
            suggestions.append(
                f"{category}是您最频繁且支出最高的类别，"
                f"建议重点关注该类别的消费优化。"
            )
        
        # 基于消费画像的建议
        consumption_type = profile.get("consumption_type", "")
        if consumption_type == "diverse":
            suggestions.append("您的消费类别较为分散，建议集中管理，避免过度分散注意力。")
        elif consumption_type == "irregular":
            suggestions.append("您的消费模式不太规律，建议建立固定的消费计划，提高财务可控性。")
        
        return suggestions


# 全局服务实例
financial_prediction_service = FinancialPredictionService()
anomaly_detection_service = AnomalyDetectionService()
consumption_pattern_analyzer = ConsumptionPatternAnalyzer()