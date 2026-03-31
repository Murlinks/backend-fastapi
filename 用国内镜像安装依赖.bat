@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [提示] 未找到 .venv，请先在本目录执行: python -m venv .venv
    pause
    exit /b 1
)
echo 使用清华大学 PyPI 镜像安装（缓解连接被重置）...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
echo 先安装 setuptools / wheel（修复 Cannot import setuptools.build_meta）...
python -m pip install --upgrade setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
echo 先单独安装 numpy（仅 wheel，避免中文路径下源码编译失败）...
python -m pip install "numpy==2.1.3" --only-binary numpy -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --default-timeout=120
echo 再装 pydantic（Python 3.13 需新版 pydantic-core 的 wheel，避免下载 Rust）...
python -m pip install "pydantic==2.10.6" "pydantic-settings==2.7.0" --only-binary pydantic-core -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --default-timeout=120
python -m pip install -r "其他被提及的\requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --default-timeout=120 --prefer-binary
echo.
if %ERRORLEVEL% EQU 0 (
    echo [完成] 若上面无红色 ERROR，可执行: python main.py
) else (
    echo [失败] 可多试几次，或换手机热点 / 检查代理与防火墙
)
pause
