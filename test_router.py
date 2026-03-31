"""
测试路由配置文件导入
"""
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 测试路由配置文件导入
    import importlib
    router_module = importlib.import_module('app.api路由.v1.router（路由配置）')
    api_router = router_module.api_router
    print("✓ 路由配置文件导入成功")
    print(f"路由数量: {len(api_router.routes)}")
except Exception as e:
    print(f"✗ 路由配置文件导入失败: {e}")
    import traceback
    traceback.print_exc()

print("测试完成")