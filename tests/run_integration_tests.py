"""
集成测试运行器
Requirements: 8.3, 8.4, 8.5

运行完整的系统集成测试套件
"""
import asyncio
import sys
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class IntegrationTestRunner:
    """集成测试运行器"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    def run_test_suite(self, test_type: str = "all") -> Dict[str, Any]:
        """运行测试套件"""
        self.start_time = time.time()
        
        print("=" * 60)
        print("移动端AI财务助手 - 系统集成测试")
        print("=" * 60)
        
        # 检查环境
        if not self._check_environment():
            return {"success": False, "error": "环境检查失败"}
        
        # 运行不同类型的测试
        if test_type in ["all", "unit"]:
            self._run_unit_tests()
        
        if test_type in ["all", "integration"]:
            self._run_integration_tests()
        
        if test_type in ["all", "performance"]:
            self._run_performance_tests()
        
        if test_type in ["all", "security"]:
            self._run_security_tests()
        
        self.end_time = time.time()
        
        # 生成报告
        return self._generate_report()
    
    def _check_environment(self) -> bool:
        """检查测试环境"""
        print("\n🔍 检查测试环境...")
        
        # 检查Python版本
        python_version = sys.version_info
        if python_version.major < 3 or python_version.minor < 8:
            print(f"❌ Python版本过低: {python_version.major}.{python_version.minor}")
            return False
        print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # 检查必要的包
        required_packages = [
            "pytest", "httpx", "sqlalchemy", "fastapi",
            "redis", "asyncpg", "hypothesis"
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
                print(f"✅ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"❌ {package} 未安装")
        
        if missing_packages:
            print(f"\n请安装缺失的包: pip install {' '.join(missing_packages)}")
            return False
        
        # 检查数据库连接
        try:
            from app.core.config import settings
            print(f"✅ 配置加载成功")
            print(f"   数据库: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'localhost'}")
        except Exception as e:
            print(f"❌ 配置加载失败: {e}")
            return False
        
        return True
    
    def _run_unit_tests(self):
        """运行单元测试"""
        print("\n🧪 运行单元测试...")
        
        unit_test_files = [
            "test_ai_service.py",
            "test_budgets.py", 
            "test_expenses.py",
            "test_sync_service.py"
        ]
        
        for test_file in unit_test_files:
            if os.path.exists(f"tests/{test_file}"):
                result = self._run_pytest_file(test_file, "unit")
                self.test_results[f"unit_{test_file}"] = result
            else:
                print(f"⚠️  测试文件不存在: {test_file}")
    
    def _run_integration_tests(self):
        """运行集成测试"""
        print("\n🔗 运行集成测试...")
        
        integration_test_files = [
            "test_integration_e2e.py"
        ]
        
        for test_file in integration_test_files:
            if os.path.exists(f"tests/{test_file}"):
                result = self._run_pytest_file(test_file, "integration")
                self.test_results[f"integration_{test_file}"] = result
            else:
                print(f"⚠️  测试文件不存在: {test_file}")
    
    def _run_performance_tests(self):
        """运行性能测试"""
        print("\n⚡ 运行性能测试...")
        
        performance_test_files = [
            "test_performance_load.py"
        ]
        
        for test_file in performance_test_files:
            if os.path.exists(f"tests/{test_file}"):
                result = self._run_pytest_file(test_file, "performance")
                self.test_results[f"performance_{test_file}"] = result
            else:
                print(f"⚠️  测试文件不存在: {test_file}")
    
    def _run_security_tests(self):
        """运行安全测试"""
        print("\n🔒 运行安全测试...")
        
        security_test_files = [
            "test_security_data_protection.py"
        ]
        
        for test_file in security_test_files:
            if os.path.exists(f"tests/{test_file}"):
                result = self._run_pytest_file(test_file, "security")
                self.test_results[f"security_{test_file}"] = result
            else:
                print(f"⚠️  测试文件不存在: {test_file}")
    
    def _run_pytest_file(self, test_file: str, test_type: str) -> Dict[str, Any]:
        """运行单个pytest文件"""
        print(f"\n  📋 运行 {test_file}...")
        
        # 构建pytest命令
        cmd = [
            "python", "-m", "pytest",
            f"tests/{test_file}",
            "-v",
            "--tb=short",
            "--disable-warnings"
        ]
        
        # 根据测试类型添加标记
        if test_type == "unit":
            cmd.extend(["-m", "unit"])
        elif test_type == "integration":
            cmd.extend(["-m", "integration"])
        elif test_type == "performance":
            cmd.extend(["-m", "slow"])
        elif test_type == "security":
            cmd.extend(["-m", "security"])
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 解析pytest输出
            output_lines = result.stdout.split('\n')
            
            # 查找测试结果摘要
            passed = failed = skipped = 0
            for line in output_lines:
                if "passed" in line and "failed" in line:
                    # 解析类似 "5 passed, 2 failed, 1 skipped" 的行
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed" and i > 0:
                            passed = int(parts[i-1])
                        elif part == "failed" and i > 0:
                            failed = int(parts[i-1])
                        elif part == "skipped" and i > 0:
                            skipped = int(parts[i-1])
                    break
            
            success = result.returncode == 0
            
            if success:
                print(f"    ✅ 通过 ({duration:.2f}s)")
            else:
                print(f"    ❌ 失败 ({duration:.2f}s)")
                if result.stderr:
                    print(f"    错误: {result.stderr[:200]}...")
            
            return {
                "success": success,
                "duration": duration,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            print(f"    ⏰ 超时 (>300s)")
            return {
                "success": False,
                "duration": 300,
                "error": "timeout",
                "passed": 0,
                "failed": 1,
                "skipped": 0
            }
        except Exception as e:
            print(f"    💥 异常: {e}")
            return {
                "success": False,
                "duration": 0,
                "error": str(e),
                "passed": 0,
                "failed": 1,
                "skipped": 0
            }
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total_duration = self.end_time - self.start_time
        
        # 统计总体结果
        total_passed = sum(result.get("passed", 0) for result in self.test_results.values())
        total_failed = sum(result.get("failed", 0) for result in self.test_results.values())
        total_skipped = sum(result.get("skipped", 0) for result in self.test_results.values())
        total_tests = total_passed + total_failed + total_skipped
        
        successful_files = sum(1 for result in self.test_results.values() if result.get("success", False))
        total_files = len(self.test_results)
        
        # 按类型分组统计
        type_stats = {}
        for test_name, result in self.test_results.items():
            test_type = test_name.split('_')[0]
            if test_type not in type_stats:
                type_stats[test_type] = {
                    "files": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "duration": 0
                }
            
            type_stats[test_type]["files"] += 1
            type_stats[test_type]["passed"] += result.get("passed", 0)
            type_stats[test_type]["failed"] += result.get("failed", 0)
            type_stats[test_type]["skipped"] += result.get("skipped", 0)
            type_stats[test_type]["duration"] += result.get("duration", 0)
        
        # 生成报告
        report = {
            "summary": {
                "total_duration": total_duration,
                "total_files": total_files,
                "successful_files": successful_files,
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0
            },
            "by_type": type_stats,
            "details": self.test_results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 打印报告
        self._print_report(report)
        
        # 保存报告到文件
        self._save_report(report)
        
        return report
    
    def _print_report(self, report: Dict[str, Any]):
        """打印测试报告"""
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)
        
        summary = report["summary"]
        print(f"总耗时: {summary['total_duration']:.2f}s")
        print(f"测试文件: {summary['successful_files']}/{summary['total_files']} 成功")
        print(f"测试用例: {summary['passed']} 通过, {summary['failed']} 失败, {summary['skipped']} 跳过")
        print(f"成功率: {summary['success_rate']:.1f}%")
        
        # 按类型显示结果
        print(f"\n按类型统计:")
        for test_type, stats in report["by_type"].items():
            print(f"  {test_type.upper()}:")
            print(f"    文件: {stats['files']}")
            print(f"    用例: {stats['passed']} 通过, {stats['failed']} 失败, {stats['skipped']} 跳过")
            print(f"    耗时: {stats['duration']:.2f}s")
        
        # 显示失败的测试
        failed_tests = [name for name, result in report["details"].items() if not result.get("success", False)]
        if failed_tests:
            print(f"\n❌ 失败的测试:")
            for test_name in failed_tests:
                result = report["details"][test_name]
                error = result.get("error", "未知错误")
                print(f"  - {test_name}: {error}")
        
        # 总体结果
        if summary["failed"] == 0:
            print(f"\n🎉 所有测试通过！")
        else:
            print(f"\n⚠️  有 {summary['failed']} 个测试失败")
    
    def _save_report(self, report: Dict[str, Any]):
        """保存测试报告到文件"""
        report_file = f"tests/integration_test_report_{int(time.time())}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n📄 详细报告已保存到: {report_file}")
        except Exception as e:
            print(f"\n⚠️  保存报告失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="运行系统集成测试")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "performance", "security"],
        default="all",
        help="测试类型 (默认: all)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner()
    report = runner.run_test_suite(args.type)
    
    # 根据测试结果设置退出码
    if report["summary"]["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()