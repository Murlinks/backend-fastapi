#!/usr/bin/env python3
"""
检查项目依赖是否可用
"""
import sys

def check_package(package_name, import_name=None):
    """检查包是否可导入"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✓ {package_name} 可用")
        return True
    except ImportError:
        print(f"✗ {package_name} 未安装")
        return False

def main():
    """主函数"""
    print("检查项目依赖...")
    print("=" * 40)
    
    # 核心依赖
    packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        ("pydantic-settings", "pydantic_settings"),
        ("sqlalchemy", "sqlalchemy"),
        ("asyncpg", "asyncpg"),
        ("redis", "redis"),
        ("python-jose", "jose"),
        ("passlib", "passlib"),
        ("python-multipart", "multipart"),
    ]
    
    available = 0
    total = len(packages)
    
    for package_name, import_name in packages:
        if check_package(package_name, import_name):
            available += 1
    
    print("=" * 40)
    print(f"依赖检查完成: {available}/{total} 个包可用")
    
    if available == total:
        print("✓ 所有依赖都已安装")
        return True
    else:
        print("✗ 部分依赖缺失，请运行: pip install -r requirements.txt")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)