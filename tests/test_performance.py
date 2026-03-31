"""
性能测试
测试系统的性能指标，包括响应时间、并发能力、资源使用等
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any


class TestAPIPerformance:
    """API性能测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_expense_creation_performance(self, client, auth_headers):
        """测试支出创建性能"""
        iterations = 100
        start_time = time.time()
        
        for i in range(iterations):
            response = await client.post(
                "/api/v1/expenses/",
                json={
                    "amount": 50.0,
                    "category": "dining",
                    "description": f"性能测试支出{i}"
                },
                headers=auth_headers
            )
            assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        # 断言平均响应时间小于100ms
        assert avg_time < 0.1, f"平均响应时间{avg_time*1000:.2f}ms超过100ms"
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_expense_query_performance(self, client, auth_headers):
        """测试支出查询性能"""
        # 先创建一些测试数据
        for i in range(50):
            await client.post(
                "/api/v1/expenses/",
                json={
                    "amount": 50.0 + i,
                    "category": ["dining", "transportation", "shopping"][i % 3],
                    "description": f"测试支出{i}"
                },
                headers=auth_headers
            )
        
        # 测试查询性能
        iterations = 100
        start_time = time.time()
        
        for i in range(iterations):
            response = await client.get(
                "/api/v1/expenses/",
                headers=auth_headers
            )
            assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        # 断言平均响应时间小于50ms
        assert avg_time < 0.05, f"平均响应时间{avg_time*1000:.2f}ms超过50ms"
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_budget_query_performance(self, client, auth_headers):
        """测试预算查询性能"""
        iterations = 100
        start_time = time.time()
        
        for i in range(iterations):
            response = await client.get(
                "/api/v1/budgets/",
                headers=auth_headers
            )
            assert response.status_code in [200, 404]
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        # 断言平均响应时间小于30ms
        assert avg_time < 0.03, f"平均响应时间{avg_time*1000:.2f}ms超过30ms"


class TestConcurrentPerformance:
    """并发性能测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_concurrent_expense_creation(self, client, auth_headers):
        """测试并发创建支出"""
        concurrent_requests = 50
        
        async def create_expense(i: int):
            return await client.post(
                "/api/v1/expenses/",
                json={
                    "amount": 50.0 + i,
                    "category": "dining",
                    "description": f"并发测试支出{i}"
                },
                headers=auth_headers
            )
        
        start_time = time.time()
        
        # 并发执行
        tasks = [create_expense(i) for i in range(concurrent_requests)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 验证所有请求都成功
        successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
        assert successful >= concurrent_requests * 0.95, f"成功率{successful/concurrent_requests*100:.1f}%低于95%"
        
        # 验证总时间合理
        assert total_time < 5.0, f"总时间{total_time:.2f}s超过5s"
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_concurrent_query_performance(self, client, auth_headers):
        """测试并发查询性能"""
        concurrent_requests = 100
        
        async def query_expenses():
            return await client.get(
                "/api/v1/expenses/",
                headers=auth_headers
            )
        
        start_time = time.time()
        
        # 并发执行
        tasks = [query_expenses() for _ in range(concurrent_requests)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 验证所有请求都成功
        successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
        assert successful >= concurrent_requests * 0.98, f"成功率{successful/concurrent_requests*100:.1f}%低于98%"
        
        # 验证平均响应时间
        avg_time = total_time / concurrent_requests
        assert avg_time < 0.1, f"平均响应时间{avg_time*1000:.2f}ms超过100ms"


class TestCachePerformance:
    """缓存性能测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_cache_hit_performance(self, client, auth_headers):
        """测试缓存命中性能"""
        # 先执行一次查询，填充缓存
        await client.get("/api/v1/expenses/", headers=auth_headers)
        
        # 测试缓存命中性能
        iterations = 100
        start_time = time.time()
        
        for i in range(iterations):
            response = await client.get(
                "/api/v1/expenses/",
                headers=auth_headers
            )
            assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        # 缓存命中应该非常快，小于10ms
        assert avg_time < 0.01, f"缓存命中平均响应时间{avg_time*1000:.2f}ms超过10ms"
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_cache_miss_performance(self, client, auth_headers):
        """测试缓存未命中性能"""
        iterations = 50
        start_time = time.time()
        
        for i in range(iterations):
            # 每次使用不同的查询参数，避免缓存命中
            response = await client.get(
                f"/api/v1/expenses/?limit={10 + i}",
                headers=auth_headers
            )
            assert response.status_code == 200
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        # 缓存未命中应该仍然保持良好性能，小于100ms
        assert avg_time < 0.1, f"缓存未命中平均响应时间{avg_time*1000:.2f}ms超过100ms"


class TestDatabasePerformance:
    """数据库性能测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_batch_insert_performance(self, db_session, test_user):
        """测试批量插入性能"""
        from app.models.expense import Expense
        
        batch_size = 100
        expenses = []
        
        start_time = time.time()
        
        for i in range(batch_size):
            expense = Expense(
                user_id=test_user.id,
                amount=Decimal(str(50.0 + i)),
                category=["dining", "transportation", "shopping"][i % 3],
                description=f"批量测试支出{i}",
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            expenses.append(expense)
        
        db_session.add_all(expenses)
        await db_session.commit()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 批量插入100条记录应该在1秒内完成
        assert total_time < 1.0, f"批量插入{batch_size}条记录耗时{total_time:.2f}s超过1s"
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_complex_query_performance(self, db_session, test_user):
        """测试复杂查询性能"""
        from app.models.expense import Expense
        from sqlalchemy import select, func, and_
        
        # 先创建测试数据
        for i in range(100):
            expense = Expense(
                user_id=test_user.id,
                amount=Decimal(str(50.0 + i)),
                category=["dining", "transportation", "shopping", "entertainment"][i % 4],
                description=f"复杂查询测试{i}",
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            db_session.add(expense)
        
        await db_session.commit()
        
        # 测试复杂查询性能
        iterations = 50
        start_time = time.time()
        
        for i in range(iterations):
            # 执行复杂查询：按类别分组、统计、排序
            query = select(
                Expense.category,
                func.count(Expense.id).label('count'),
                func.sum(Expense.amount).label('total'),
                func.avg(Expense.amount).label('average')
            ).where(
                and_(
                    Expense.user_id == test_user.id,
                    Expense.created_at >= datetime.utcnow() - timedelta(days=30)
                )
            ).group_by(Expense.category).order_by(func.count(Expense.id).desc())
            
            result = await db_session.execute(query)
            rows = result.all()
            assert len(rows) > 0
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        # 复杂查询应该在100ms内完成
        assert avg_time < 0.1, f"复杂查询平均响应时间{avg_time*1000:.2f}ms超过100ms"


class TestMemoryAndResourceUsage:
    """内存和资源使用测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_memory_leak_detection(self, client, auth_headers):
        """测试内存泄漏"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行大量操作
        for i in range(100):
            await client.post(
                "/api/v1/expenses/",
                json={
                    "amount": 50.0 + i,
                    "category": "dining",
                    "description": f"内存测试{i}"
                },
                headers=auth_headers
            )
            
            await client.get("/api/v1/expenses/", headers=auth_headers)
        
        # 强制垃圾回收
        import gc
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # 内存增长应该小于50MB
        assert memory_increase < 50, f"内存增长{memory_increase:.2f}MB超过50MB，可能存在内存泄漏"
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_connection_pool_efficiency(self, client, auth_headers):
        """测试连接池效率"""
        from app.core.database import engine
        
        initial_pool_size = engine.pool.size()
        
        # 执行大量并发请求
        concurrent_requests = 50
        
        async def make_request():
            return await client.get("/api/v1/expenses/", headers=auth_headers)
        
        await asyncio.gather(*[make_request() for _ in range(concurrent_requests)])
        
        final_pool_size = engine.pool.size()
        
        # 连接池应该被有效利用
        assert final_pool_size >= initial_pool_size, "连接池未被有效利用"
        assert final_pool_size <= 20, f"连接池大小{final_pool_size}超过配置的最大值20"


class TestScalabilityPerformance:
    """可扩展性性能测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_data_volume_scaling(self, db_session, test_user):
        """测试数据量扩展性能"""
        from app.models.expense import Expense
        from sqlalchemy import select
        
        # 测试不同数据量下的查询性能
        data_sizes = [100, 500, 1000]
        performance_results = []
        
        for size in data_sizes:
            # 清理现有数据
            await db_session.execute(select(Expense).where(Expense.user_id == test_user.id))
            await db_session.commit()
            
            # 插入指定数量的数据
            start_time = time.time()
            for i in range(size):
                expense = Expense(
                    user_id=test_user.id,
                    amount=Decimal(str(50.0 + i)),
                    category="dining",
                    description=f"扩展性测试{i}",
                    created_at=datetime.utcnow() - timedelta(days=i)
                )
                db_session.add(expense)
            await db_session.commit()
            insert_time = time.time() - start_time
            
            # 测试查询性能
            start_time = time.time()
            query = select(Expense).where(Expense.user_id == test_user.id)
            result = await db_session.execute(query)
            expenses = result.scalars().all()
            query_time = time.time() - start_time
            
            performance_results.append({
                "size": size,
                "insert_time": insert_time,
                "query_time": query_time,
                "query_per_record": query_time / size
            })
        
        # 验证性能扩展性
        # 查询时间应该接近线性增长，不应该指数增长
        for i in range(1, len(performance_results)):
            current = performance_results[i]
            previous = performance_results[i-1]
            
            size_ratio = current["size"] / previous["size"]
            time_ratio = current["query_time"] / previous["query_time"]
            
            # 时间增长不应该超过数据量增长的1.5倍
            assert time_ratio < size_ratio * 1.5, \
                f"数据量从{previous['size']}增长到{current['size']}时，查询时间增长{time_ratio:.2f}倍超过预期"


class TestStressPerformance:
    """压力测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_high_concurrent_load(self, client, auth_headers):
        """测试高并发负载"""
        concurrent_requests = 200
        
        async def make_request(i):
            try:
                return await client.get("/api/v1/expenses/", headers=auth_headers)
            except Exception as e:
                return e
        
        start_time = time.time()
        
        # 并发执行大量请求
        tasks = [make_request(i) for i in range(concurrent_requests)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 统计成功率
        successful = sum(1 for r in responses if not isinstance(r, Exception) and hasattr(r, 'status_code') and r.status_code == 200)
        success_rate = successful / concurrent_requests
        
        # 在高并发下，成功率应该保持在95%以上
        assert success_rate >= 0.95, f"高并发下成功率{success_rate*100:.1f}%低于95%"
        
        # 总时间应该在合理范围内
        assert total_time < 10.0, f"高并发总时间{total_time:.2f}s超过10s"