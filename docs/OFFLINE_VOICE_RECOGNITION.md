# 离线语音识别模型配置指南

## 概述

本项目集成了Vosk离线语音识别模型，支持在无网络环境下进行语音识别。离线识别准确率约为75%，适合网络不稳定或需要隐私保护的场景。

## 模型下载

### 1. 访问Vosk模型库

访问 [Vosk官方模型库](https://alphacephei.com/vosk/models) 下载适合的模型。

### 2. 选择模型

推荐以下模型：

- **vosk-model-small-cn-0.22** (约50MB)
  - 适合资源受限的环境
  - 准确率：70-75%
  - 识别速度快
  
- **vosk-model-cn-0.22** (约1.2GB)
  - 适合对准确率要求较高的场景
  - 准确率：75-80%
  - 识别速度中等

- **vosk-model-small-cn-0.5** (约40MB)
  - 最新版本
  - 准确率：72-77%
  - 识别速度快

### 3. 下载模型

```bash
# 使用wget下载（Linux/Mac）
wget https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip

# 使用curl下载
curl -L -o vosk-model-small-cn-0.22.zip https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip

# Windows用户可以直接在浏览器中下载
```

## 模型安装

### 1. 解压模型

```bash
# 解压下载的模型文件
unzip vosk-model-small-cn-0.22.zip

# Windows用户可以使用WinRAR或7-Zip解压
```

### 2. 放置模型文件

将解压后的模型文件夹重命名为 `vosk-model`，并放置到以下位置：

```
后端服务 (FastAPI)/app/models/vosk-model/
```

目录结构应该是：

```
后端服务 (FastAPI)/
├── app/
│   ├── models/
│   │   └── vosk-model/
│   │       ├── am/
│   │       ├── conf/
│   │       ├── graph/
│   │       ├── ivector/
│   │       └── ...
```

### 3. 创建models目录

如果 `models` 目录不存在，需要先创建：

```bash
# Linux/Mac
mkdir -p "后端服务 (FastAPI)/app/models"

# Windows PowerShell
New-Item -ItemType Directory -Force -Path "后端服务 (FastAPI)\app\models"

# 然后将模型文件夹移动到该目录
mv vosk-model-small-cn-0.22 "后端服务 (FastAPI)/app/models/vosk-model"
```

## 依赖安装

安装离线语音识别所需的依赖：

```bash
pip install vosk pydub numpy
```

或者在项目根目录运行：

```bash
pip install -r "后端服务 (FastAPI)/其他被提及的/requirements.txt"
```

## 配置验证

### 1. 启动服务

启动后端服务，查看日志输出：

```bash
cd "后端服务 (FastAPI)"
python -m app.main
```

如果模型加载成功，会看到以下日志：

```
离线语音识别模型加载成功: /path/to/vosk-model
```

如果模型未找到，会看到：

```
离线语音识别模型不存在: /path/to/vosk-model
请下载模型文件并放置到指定目录
模型下载地址: https://alphacephei.com/vosk/models
```

### 2. 测试离线识别

使用API测试离线识别功能：

```bash
curl -X POST http://localhost:8000/api/v1/voice/recognize \
  -H "Content-Type: application/json" \
  -d '{
    "audio_data": "base64_encoded_audio_data",
    "provider": "offline",
    "enable_noise_reduction": true
  }'
```

## 使用场景

### 1. 无网络环境

在地铁、飞机等无网络环境下，用户仍可使用语音记账功能。

### 2. 隐私保护

对于敏感的财务信息，用户可以选择使用离线识别，避免数据上传到云端。

### 3. 降级策略

当在线识别服务不可用时，系统会自动降级到离线识别，确保服务可用性。

## 性能优化

### 1. 模型选择

- **资源受限环境**：使用small模型（约50MB）
- **高准确率需求**：使用完整模型（约1.2GB）
- **平衡选择**：使用medium模型（约300MB）

### 2. 音频预处理

系统会自动进行以下预处理：

- 降噪处理
- 音量归一化
- 频率滤波（300Hz-3000Hz）

### 3. 批量识别

对于批量语音识别，可以考虑：

- 使用多线程处理
- 缓存识别结果
- 异步处理

## 常见问题

### 1. 模型加载失败

**问题**：启动时报错"离线语音识别模型不存在"

**解决方案**：
- 检查模型文件是否放置在正确位置
- 确认模型文件夹名称为 `vosk-model`
- 检查文件权限

### 2. 识别准确率低

**问题**：离线识别准确率低于预期

**解决方案**：
- 使用更大的模型
- 确保音频质量良好
- 启用降噪功能
- 调整采样率（推荐16kHz）

### 3. 识别速度慢

**问题**：离线识别速度较慢

**解决方案**：
- 使用small模型
- 减少音频长度
- 优化系统资源

### 4. 内存占用高

**问题**：加载模型后内存占用过高

**解决方案**：
- 使用small模型
- 关闭其他占用内存的程序
- 增加系统内存

## 技术支持

如有问题，请参考：

- [Vosk官方文档](https://alphacephei.com/vosk/)
- [Vosk Python API文档](https://alphacephei.com/vosk/api)
- 项目GitHub Issues

## 更新日志

- 2024-02-26: 初始版本，集成Vosk离线语音识别
- 支持降噪和音频预处理
- 支持自动降级策略