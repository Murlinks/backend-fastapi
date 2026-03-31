"""
性能和负载测试
Requirements: 8.3, 8.4

测试系统在高负载下的性能表现和稳定性
"""
import pytest
import asyncio
import time
from httpx import AsyncClient
from datetime import datetime, timedelta
import uuid
from typing import List, Dict, Any
import statistics


@pytest.mark.slow
@pytest.mark.asyncio
async def test_api_response_time_benchmarks(client: AsyncClient):
    """测试API响应时间基准"""
    # 创建测试用户
    user_data = {
        "phone_number": "+8613800138100",
        "identity": "student",
        "preferences": {"currency": "CNY"}
    }
    
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    
    # 测试各个API端点的响应时间
    endpoints_to_test = [
        ("GET", f"/api/v1/expenses/?user_id={user_id}", None),
        ("GET", f"/api/v1/budgets/?user_id={user_id}", None),
        ("GET", "/api/v1/budgets/templates/identities", None),
        ("POST", "/api/v1/ai/analyze", {"text": "买咖啡15元"}),
    ]
    
    response_times = {}
    
    for method, endpoint, data in endpoints_to_test:
        times = []
        
        # 每个端点测试10次
        for _ in range(10):
            start_time = time.time()
            
            if method == "GET":
                response = await client.get(endpoint)
            elif method == "POST":
                response = await client.post(endpoint, json=data)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            
            assert response.status_code in [200, 201]
            times.append(response_time)
        
        response_times[endpoint] = {
            "avg": statistics.mean(times),
            "min": min(times),
            "max": max(times),
            "median": statistics.median(times)
        }
    
    # 验证响应时间在合理范围内（< 1000ms）
    for endpoint, metrics in response_times.items():
        assert metrics["avg"] < 1000, f"{endpoint} 平均响应时间过长: {metrics['avg']:.2f}ms"
        assert metrics["max"] < 2000, f"{endpoint} 最大响应时间过长: {metrics['max']:.2f}ms"
    
    print("\n=== API响应时间基准测试结果 ===")
    for endpoint, metrics in response_times.items():
        print(f"{endpoint}:")
        print(f"  平均: {metrics['avg']:.2f}ms")
        print(f"  最小: {metrics['min']:.2f}ms")
        print(f"  最大: {metrics['max']:.2f}ms")
        print(f"  中位数: {metrics['median']:.2f}ms")


@pytest.mark.slow
@pytest.mark.asyncio
async def test_concurrent_user_load(client: AsyncClient):
    """测试并发用户负载"""
    num_concurrent_users = 20
    operations_per_user = 5
    
    async def simulate_user_operations(user_index: int) -> Dict[str, Any]:
        """模拟单个用户的操作"""
        user_data = {
            "phone_number": f"+861380013{user_index:04d}",
            "identity": "student",
            "preferences": {"currency": "CNY"}
        }
        
        start_time = time.time()
        
        try:
            # 1. 注册用户
            user_response = await client.post("/api/v1/auth/register", json=user_data)
            if user_response.status_code != 201:
                return {"success": False, "error": "registration_failed"}
            
            user_id = user_response.json()["id"]
            
            # 2. 创建预算
            now = datetime.utcnow()
            budget_data = {
                "user_id": user_id,
                "category": "dining",
                "total_amount": 1000.00,
                "period_start": now.isoformat(),
                "period_end": (now + timedelta(days=30)).isoformat()
            }
            
            budget_response = await client.post("/api/v1/budgets/", json=budget_data)
            if budget_response.status_code != 201:
                return {"success": False, "error": "budget_creation_failed"}
            
            # 3. 添加多个支出记录
            for i in range(operations_per_user):
                expense_data = {
                    "user_id": user_id,
                    "amount": 20.0 + i * 5,
                    "category": "dining",
                    "description": f"支出{i}",
                    "is_emergency": False
                }
                
                expense_response = await client.post("/api/v1/expenses/", json=expense_data)
                if expense_response.status_code != 201:
                    return {"success": False, "error": f"expense_creation_failed_{i}"}
            
            # 4. 查询数据
            expenses_response = await client.get(f"/api/v1/expenses/?user_id={user_id}")
            if expenses_response.status_code != 200:
                return {"success": False, "error": "expenses_query_failed"}
            
            end_time = time.time()
            total_time = (end_time - start_time) * 1000
            
            return {
                "success": True,
                "user_id": user_id,
                "total_time": total_time,
                "operations_completed": operations_per_user + 3  # 注册 + 预算 + 查询 + N个支出
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # 并发执行所有用户操作
    start_time = time.time()
    tasks = [simulate_user_operations(i) for i in range(num_concurrent_users)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    total_test_time = (end_time - start_time) * 1000
    
    # 分析结果
    successful_operations = [r for r in results if isinstance(r, dict) and r.get("success")]
    failed_operations = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
    
    success_rate = len(successful_operations) / len(results) * 100
    
    if successful_operations:
        avg_operation_time = statistics.mean([r["total_time"] for r in successful_operations])
        total_operations = sum([r["operations_completed"] for r in successful_operations])
        throughput = total_operations / (total_test_time / 1000)  # 操作/秒
    else:
        avg_operation_time = 0
        throughput = 0
    
    print(f"\n=== 并发负载测试结果 ===")
    print(f"并发用户数: {num_concurrent_users}")
    print(f"每用户操作数: {operations_per_user + 3}")
    print(f"成功率: {success_rate:.1f}%")
    print(f"平均用户操作时间: {avg_operation_time:.2f}ms")
    print(f"总测试时间: {total_test_time:.2f}ms")
    print(f"系统吞吐量: {throughput:.2f} 操作/秒")
    
    # 验证性能指标
    assert success_rate >= 95, f"成功率过低: {success_rate:.1f}%"
    assert avg_operation_time < 5000, f"平均操作时间过长: {avg_operation_time:.2f}ms"
    
    if failed_operations:
        print(f"失败操作详情: {failed_operations[:5]}")  # 只显示前5个失败


@pytest.mark.slow
@pytest.mark.asyncio
async def test_database_performance_under_load(client: AsyncClient):
    """测试数据库在高负载下的性能"""
    # 创建测试用户
    user_data = {
        "phone_number": "+8613800138200",
        "identity": "office_worker",
        "preferences": {"currency": "CNY"}
    }
    
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    
    # 创建大量数据
    num_expenses = 100
    batch_size = 10
    
    async def create_expense_batch(batch_index: int) -> List[float]:
        """创建一批支出记录并测量时间"""
        batch_times = []
        
        for i in range(batch_size):
            expense_data = {
                "user_id": user_id,
                "amount": 10.0 + (batch_index * batch_size + i),
                "category": ["dining", "transportation", "entertainment", "shopping"][i % 4],
                "description": f"批次{batch_index}_支出{i}",
                "is_emergency": False
            }
            
            start_time = time.time()
            response = await client.post("/api/v1/expenses/", json=expense_data)
            end_time = time.time()
            
            assert response.status_code == 201
            batch_times.append((end_time - start_time) * 1000)
        
        return batch_times
    
    # 分批创建数据
    all_times = []
    num_batches = num_expenses // batch_size
    
    for batch_index in range(num_batches):
        batch_times = await create_expense_batch(batch_index)
        all_times.extend(batch_times)
        
        # 每10批检查一次性能
        if (batch_index + 1) % 10 == 0:
            recent_times = all_times[-100:]  # 最近100个操作
            avg_recent_time = statistics.mean(recent_times)
            print(f"批次 {batch_index + 1}/{num_batches}, 最近平均时间: {avg_recent_time:.2f}ms")
    
    # 测试查询性能
    query_start_time = time.time()
    expenses_response = await client.get(f"/api/v1/expenses/?user_id={user_id}")
    query_end_time = time.time()
    
    assert expenses_response.status_code == 200
    expenses_data = expenses_response.json()
    assert len(expenses_data) == num_expenses
    
    query_time = (query_end_time - query_start_time) * 1000
    
    # 分析性能指标
    avg_create_time = statistics.mean(all_times)
    max_create_time = max(all_times)
    min_create_time = min(all_times)
    
    print(f"\n=== 数据库性能测试结果 ===")
    print(f"创建记录数: {num_expenses}")
    print(f"平均创建时间: {avg_create_time:.2f}ms")
    print(f"最大创建时间: {max_create_time:.2f}ms")
    print(f"最小创建时间: {min_create_time:.2f}ms")
    print(f"查询{num_expenses}条记录时间: {query_time:.2f}ms")
    
    # 验证性能指标
    assert avg_create_time < 500, f"平均创建时间过长: {avg_create_time:.2f}ms"
    assert query_time < 1000, f"查询时间过长: {query_time:.2f}ms"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_ai_service_performance(client: AsyncClient):
    """测试AI服务性能"""
    test_texts = [
        "买奶茶15元",
        "午餐花了25.5",
        "地铁票3元",
        "看电影60块",
        "买书籍80元",
        "咖啡店消费18元",
        "超市购物120元",
        "打车费用35元",
        "健身房月费200元",
        "手机话费50元"
    ]
    
    # 测试AI分析性能
    ai_times = []
    
    for text in test_texts:
        # 每个文本测试3次
        for _ in range(3):
            start_time = time.time()
            
            response = await client.post(
                "/api/v1/ai/analyze",
                json={"text": text}
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            assert response.status_code == 200
            ai_times.append(response_time)
    
    # 测试并发AI请求
    async def ai_analyze_request(text: str) -> float:
        start_time = time.time()
        response = await client.post("/api/v1/ai/analyze", json={"text": text})
        end_time = time.time()
        assert response.status_code == 200
        return (end_time - start_time) * 1000
    
    # 并发发送10个AI请求
    concurrent_start_time = time.time()
    concurrent_tasks = [ai_analyze_request(text) for text in test_texts]
    concurrent_times = await asyncio.gather(*concurrent_tasks)
    concurrent_end_time = time.time()
    
    concurrent_total_time = (concurrent_end_time - concurrent_start_time) * 1000
    
    # 分析结果
    avg_ai_time = statistics.mean(ai_times)
    max_ai_time = max(ai_times)
    avg_concurrent_time = statistics.mean(concurrent_times)
    
    print(f"\n=== AI服务性能测试结果 ===")
    print(f"单个请求平均时间: {avg_ai_time:.2f}ms")
    print(f"单个请求最大时间: {max_ai_time:.2f}ms")
    print(f"并发请求平均时间: {avg_concurrent_time:.2f}ms")
    print(f"并发请求总时间: {concurrent_total_time:.2f}ms")
    
    # 验证AI服务性能
    assert avg_ai_time < 2000, f"AI分析平均时间过长: {avg_ai_time:.2f}ms"
    assert max_ai_time < 5000, f"AI分析最大时间过长: {max_ai_time:.2f}ms"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_memory_usage_under_load(client: AsyncClient):
    """测试内存使用情况"""
    import psutil
    import os
    
    # 获取当前进程
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # 创建大量数据
    user_data = {
        "phone_number": "+8613800138300",
        "identity": "freelancer",
        "preferences": {"currency": "CNY"}
    }
    
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    
    # 创建大量支出记录
    num_operations = 200
    memory_samples = []
    
    for i in range(num_operations):
        expense_data = {
            "user_id": user_id,
            "amount": 10.0 + i,
            "category": ["dining", "transportation", "entertainment", "shopping"][i % 4],
            "description": f"内存测试支出{i}",
            "is_emergency": False
        }
        
        await client.post("/api/v1/expenses/", json=expense_data)
        
        # 每20个操作采样一次内存使用
        if i % 20 == 0:
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
    
    final_memory = process.memory_info().rss / 1024 / 1024
    memory_increase = final_memory - initial_memory
    max_memory = max(memory_samples) if memory_samples else final_memory
    
    print(f"\n=== 内存使用测试结果 ===")
    print(f"初始内存: {initial_memory:.2f}MB")
    print(f"最终内存: {final_memory:.2f}MB")
    print(f"最大内存: {max_memory:.2f}MB")
    print(f"内存增长: {memory_increase:.2f}MB")
    print(f"操作数量: {num_operations}")
    print(f"平均每操作内存增长: {memory_increase/num_operations:.4f}MB")
    
    # 验证内存使用合理
    assert memory_increase < 100, f"内存增长过多: {memory_increase:.2f}MB"
    assert max_memory < initial_memory + 150, f"最大内存使用过多: {max_memory:.2f}MB"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_stress_test_budget_calculations(client: AsyncClient):
    """压力测试预算计算功能"""
    # 创建用户
    user_data = {
        "phone_number": "+8613800138400",
        "identity": "student",
        "preferences": {"currency": "CNY"}
    }
    
    user_response = await client.post("/api/v1/auth/register", json=user_data)
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    
    # 创建多个预算
    categories = ["dining", "transportation", "entertainment", "shopping"]
    budget_ids = []
    
    now = datetime.utcnow()
    for category in categories:
        budget_data = {
            "user_id": user_id,
            "category": category,
            "total_amount": 1000.00,
            "period_start": now.isoformat(),
            "period_end": (now + timedelta(days=30)).isoformat(),
            "is_flexible": True,
            "flexibility_percentage": 10.0
        }
        
        budget_response = await client.post("/api/v1/budgets/", json=budget_data)
        assert budget_response.status_code == 201
        budget_ids.append(budget_response.json()["id"])
    
    # 大量并发预算查询
    async def query_budget_remaining(budget_id: str) -> float:
        start_time = time.time()
        response = await client.get(f"/api/v1/budgets/{budget_id}/remaining")
        end_time = time.time()
        
        assert response.status_code == 200
        return (end_time - start_time) * 1000
    
    # 并发查询所有预算，重复50次
    all_query_times = []
    num_rounds = 50
    
    for round_num in range(num_rounds):
        round_start_time = time.time()
        
        # 并发查询所有预算
        tasks = [query_budget_remaining(budget_id) for budget_id in budget_ids]
        round_times = await asyncio.gather(*tasks)
        
        round_end_time = time.time()
        round_total_time = (round_end_time - round_start_time) * 1000
        
        all_query_times.extend(round_times)
        
        if round_num % 10 == 0:
            avg_round_time = statistics.mean(round_times)
            print(f"轮次 {round_num + 1}/{num_rounds}, 平均查询时间: {avg_round_time:.2f}ms, 轮次总时间: {round_total_time:.2f}ms")
    
    # 分析结果
    avg_query_time = statistics.mean(all_query_times)
    max_query_time = max(all_query_times)
    min_query_time = min(all_query_times)
    
    print(f"\n=== 预算计算压力测试结果 ===")
    print(f"总查询次数: {len(all_query_times)}")
    print(f"平均查询时间: {avg_query_time:.2f}ms")
    print(f"最大查询时间: {max_query_time:.2f}ms")
    print(f"最小查询时间: {min_query_time:.2f}ms")
    
    # 验证性能稳定性
    assert avg_query_time < 200, f"平均查询时间过长: {avg_query_time:.2f}ms"
    assert max_query_time < 1000, f"最大查询时间过长: {max_query_time:.2f}ms"
    
    # 验证性能一致性（标准差不应过大）
    std_dev = statistics.stdev(all_query_times)
    assert std_dev < avg_query_time * 0.5, f"查询时间波动过大，标准差: {std_dev:.2f}ms"