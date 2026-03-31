"""
财务预测服务测试
测试支出预测、异常检测、消费模式分析等功能
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.services.financial_prediction_service import (
    financial_prediction_service,
    anomaly_detection_service,
    consumption_pattern_analyzer
)


class TestFinancialPredictionService:
    """财务预测服务测试"""
    
    @pytest.mark.asyncio
    async def test_predict_monthly_expense_success(self):
        """测试成功预测月度支出"""
        expense_history = [
            {
                "id": "1",
                "user_id": "test_user",
                "amount": 50.0,
                "category": "dining",
                "description": "午餐",
                "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
            },
            {
                "id": "2",
                "user_id": "test_user",
                "amount": 30.0,
                "category": "transportation",
                "description": "地铁",
                "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat()
            },
            {
                "id": "3",
                "user_id": "test_user",
                "amount": 100.0,
                "category": "shopping",
                "description": "购物",
                "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat()
            },
            {
                "id": "4",
                "user_id": "test_user",
                "amount": 45.0,
                "category": "dining",
                "description": "晚餐",
                "created_at": (datetime.utcnow() - timedelta(days=4)).isoformat()
            },
            {
                "id": "5",
                "user_id": "test_user",
                "amount": 25.0,
                "category": "transportation",
                "description": "公交",
                "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat()
            },
        ]
        
        result = await financial_prediction_service.predict_monthly_expense(
            expense_history=expense_history,
            user_profile=None
        )
        
        assert result["success"] is True
        assert "prediction" in result
        assert "total_amount" in result["prediction"]
        assert result["prediction"]["total_amount"] > 0
        assert "by_category" in result["prediction"]
        assert "confidence" in result["prediction"]
        assert 0 <= result["prediction"]["confidence"] <= 1
    
    @pytest.mark.asyncio
    async def test_predict_monthly_expense_insufficient_data(self):
        """测试数据不足时的预测"""
        expense_history = [
            {
                "id": "1",
                "user_id": "test_user",
                "amount": 50.0,
                "category": "dining",
                "description": "午餐",
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        
        result = await financial_prediction_service.predict_monthly_expense(
            expense_history=expense_history,
            user_profile=None
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "历史数据不足" in result["error"]
    
    @pytest.mark.asyncio
    async def test_predict_monthly_expense_empty_history(self):
        """测试空历史记录"""
        result = await financial_prediction_service.predict_monthly_expense(
            expense_history=[],
            user_profile=None
        )
        
        assert result["success"] is False
        assert "error" in result


class TestAnomalyDetectionService:
    """异常检测服务测试"""
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_success(self):
        """测试成功检测异常"""
        expense_history = [
            {
                "id": str(i),
                "user_id": "test_user",
                "amount": 50.0,
                "category": "dining",
                "description": f"支出{i}",
                "created_at": (datetime.utcnow() - timedelta(days=i)).isoformat()
            }
            for i in range(1, 11)
        ]
        
        # 添加一个异常支出
        expense_history.append({
            "id": "999",
            "user_id": "test_user",
            "amount": 5000.0,  # 异常高的金额
            "category": "shopping",
            "description": "异常支出",
            "created_at": datetime.utcnow().isoformat()
        })
        
        result = await anomaly_detection_service.detect_anomalies(
            expense_history=expense_history
        )
        
        assert result["success"] is True
        assert "risk_level" in result
        assert result["risk_level"] in ["low", "medium", "high"]
        assert "anomalies" in result
        assert len(result["anomalies"]) >= 1
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_insufficient_data(self):
        """测试数据不足时的异常检测"""
        expense_history = [
            {
                "id": "1",
                "user_id": "test_user",
                "amount": 50.0,
                "category": "dining",
                "description": "午餐",
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        
        result = await anomaly_detection_service.detect_anomalies(
            expense_history=expense_history
        )
        
        assert result["success"] is True
        assert result["has_anomalies"] is False
        assert "message" in result
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_with_new_expense(self):
        """测试检测新支出异常"""
        expense_history = [
            {
                "id": str(i),
                "user_id": "test_user",
                "amount": 50.0,
                "category": "dining",
                "description": f"支出{i}",
                "created_at": (datetime.utcnow() - timedelta(days=i)).isoformat()
            }
            for i in range(1, 11)
        ]
        
        new_expense = {
            "id": "999",
            "user_id": "test_user",
            "amount": 500.0,
            "category": "dining",
            "description": "新支出",
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = await anomaly_detection_service.detect_anomalies(
            expense_history=expense_history,
            new_expense=new_expense
        )
        
        assert result["success"] is True
        assert "has_anomalies" in result
        if result["has_anomalies"]:
            assert len(result["anomalies"]) >= 1


class TestConsumptionPatternAnalyzer:
    """消费模式分析服务测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_consumption_pattern_success(self):
        """测试成功分析消费模式"""
        expense_history = []
        
        # 创建不同类别的支出
        categories = ["dining", "transportation", "shopping", "entertainment"]
        for i in range(20):
            expense_history.append({
                "id": str(i),
                "user_id": "test_user",
                "amount": 50.0 + i * 10,
                "category": categories[i % len(categories)],
                "description": f"支出{i}",
                "created_at": (datetime.utcnow() - timedelta(days=i)).isoformat()
            })
        
        result = await consumption_pattern_analyzer.analyze_consumption_pattern(
            expense_history=expense_history,
            user_profile=None
        )
        
        assert result["success"] is True
        assert "time_pattern" in result
        assert "periodicity" in result
        assert "habits" in result
        assert "profile" in result
        assert "suggestions" in result
    
    @pytest.mark.asyncio
    async def test_analyze_consumption_pattern_empty_history(self):
        """测试空历史记录"""
        result = await consumption_pattern_analyzer.analyze_consumption_pattern(
            expense_history=[],
            user_profile=None
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_analyze_time_pattern(self):
        """测试时间模式分析"""
        expense_history = []
        
        # 创建在不同时间的支出
        for i in range(30):
            expense_history.append({
                "id": str(i),
                "user_id": "test_user",
                "amount": 50.0,
                "category": "dining",
                "description": f"支出{i}",
                "created_at": (datetime.utcnow() - timedelta(days=i, hours=i % 24)).isoformat()
            })
        
        result = await consumption_pattern_analyzer.analyze_consumption_pattern(
            expense_history=expense_history,
            user_profile=None
        )
        
        assert result["success"] is True
        assert "peak_hours" in result["time_pattern"]
        assert "peak_days" in result["time_pattern"]
        assert len(result["time_pattern"]["peak_hours"]) > 0
        assert len(result["time_pattern"]["peak_days"]) > 0


class TestIntegrationFinancialServices:
    """财务服务集成测试"""
    
    @pytest.mark.asyncio
    async def test_comprehensive_financial_analysis(self):
        """测试综合财务分析"""
        expense_history = []
        
        # 创建多样化的支出数据
        for i in range(30):
            categories = ["dining", "transportation", "shopping", "entertainment", "emergency"]
            expense_history.append({
                "id": str(i),
                "user_id": "test_user",
                "amount": 50.0 + (i % 10) * 20,
                "category": categories[i % len(categories)],
                "description": f"支出{i}",
                "created_at": (datetime.utcnow() - timedelta(days=i)).isoformat()
            })
        
        # 执行预测
        prediction_result = await financial_prediction_service.predict_monthly_expense(
            expense_history=expense_history,
            user_profile=None
        )
        
        # 执行异常检测
        anomaly_result = await anomaly_detection_service.detect_anomalies(
            expense_history=expense_history
        )
        
        # 执行消费模式分析
        pattern_result = await consumption_pattern_analyzer.analyze_consumption_pattern(
            expense_history=expense_history,
            user_profile=None
        )
        
        # 验证所有分析都成功
        assert prediction_result["success"] is True
        assert anomaly_result["success"] is True
        assert pattern_result["success"] is True
        
        # 验证数据一致性
        assert "prediction" in prediction_result
        assert "risk_level" in anomaly_result
        assert "profile" in pattern_result