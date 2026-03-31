#!/usr/bin/env python3
"""
测试基础架构设置
"""
import sys
import os

def test_imports():
    """测试基础模块导入"""
    try:
        # 测试FastAPI相关导入
        from fastapi import FastAPI
        print("✓ FastAPI 导入成功")
        
        # 测试Pydantic导入
        from pydantic import BaseModel
        print("✓ Pydantic 导入成功")
        
        # 测试应用模块导入
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from app.core.config import settings
        print("✓ 配置模块导入成功")
        
        from app.api.v1.router import api_router
        print("✓ API路由模块导入成功")
        
        from app.middleware.auth import AuthMiddleware
        print("✓ 认证中间件导入成功")
        
        from app.middleware.logging import LoggingMiddleware
        print("✓ 日志中间件导入成功")
        
        return True
        
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_config():
    """测试配置"""
    try:
        from app.core.config import settings
        
        print(f"✓ DEBUG模式: {settings.DEBUG}")
        print(f"✓ 数据库URL: {settings.DATABASE_URL}")
        print(f"✓ Redis URL: {settings.REDIS_URL}")
        
        return True
        
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        return False

def test_app_creation():
    """测试应用创建"""
    try:
        from main import create_app
        
        app = create_app()
        print(f"✓ FastAPI应用创建成功: {app.title}")
        
        return True
        
    except Exception as e:
        print(f"✗ 应用创建失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试基础架构设置...")
    print("=" * 50)
    
    success = True
    
    print("\n1. 测试模块导入:")
    success &= test_imports()
    
    print("\n2. 测试配置:")
    success &= test_config()
    
    print("\n3. 测试应用创建:")
    success &= test_app_creation()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ 所有测试通过！基础架构设置成功")
        sys.exit(0)
    else:
        print("✗ 部分测试失败，请检查配置")
        sys.exit(1)