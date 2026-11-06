# 风电结构损伤检测智能平台

基于 Qwen3.5-4B 微调模型的风电巡检图像损伤检测平台。

## 快速启动

### Windows（本机，RTX 4090）

```bash
# 1. 创建环境
conda create -n winddamage python=3.11 -y
conda activate winddamage

# 2. 安装依赖（CUDA 版 PyTorch）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt

# 3. 一键启动
start.bat
# 或手动启动
python app.py
```

### macOS / Apple Silicon（原开发机）

```bash
conda create -n winddamage python=3.11 -y
conda activate winddamage
pip install -r requirements.txt
./start.sh
```

浏览器打开 `http://localhost:7860` 即可使用。

## 项目结构

```
WindDamagePlatform/
├── app.py              # Gradio 前端入口
├── inference.py         # 模型加载与推理封装
├── parser.py            # 输出清理（strip_thinking + JSON 解析）
├── formatter.py         # JSON → 展示数据结构
├── config.py            # 路径、量化、阈值配置
├── start.sh             # 一键启动脚本
├── requirements.txt     # 依赖清单
├── qwen3.5-4b/          # 模型权重（8.4GB, bf16）
│   ├── model-00001-of-00002.safetensors
│   ├── model-00002-of-00002.safetensors
│   ├── config.json
│   ├── tokenizer.json
│   ├── tokenizer_config.json
│   ├── chat_template.jinja
│   ├── processor_config.json
│   └── generation_config.json
├── data/                # 测试数据
│   ├── dataset_test.json    # 2168 条测试样本
│   └── images/              # 测试图片
├── DEPLOYMENT_PLAN.md   # 部署方案
├── PROJECT.md           # 项目总纲
├── TASKS.md             # 任务追踪
└── HANDOFF.md           # 上游交接
```

## 使用方法

1. 启动平台后，在左侧上传风电巡检图片
2. 点击「开始分析」
3. 右侧展示结构化损伤评估报告（14 字段分栏 + 描述文本 + JSON 折叠）

## 中英双语界面

界面、报告字段、图表、导出报告均支持中 / 英切换：

```bash
python app.py             # 中文界面（默认）
python app.py --lang en   # 英文界面
# 或
start_en.bat              # 英文界面一键启动
# 或
UI_LANG=en python app.py
```

说明：
- 模型输出保持训练时的中文 JSON（内部键值不变），英文界面在展示层翻译：
  枚举值（是/否/高/中/低、损伤类型等）精确映射，自由文本按 840+ 词条词素组合尽力翻译，少数未覆盖字符保留原文。
- 模型内部逻辑（风险判定、完整性校验）基于中文原始值，与界面语言无关。
- Markdown 导出跟随界面语言；JSON 导出保持模型原始输出。

## 模型信息

| 项 | 值 |
|----|-----|
| 基座模型 | Qwen3.5-4B（Qwen3_5ForConditionalGeneration） |
| 微调方式 | QLoRA 4-bit, 3 epochs, 有效 batch 16 |
| 模板 | qwen3_5_nothink（推理时关闭 thinking） |
| 输出格式 | 6 大类 23 字段嵌套 JSON |
| 服务器基准 | Macro Acc 89.04%, QWK 0.7471 |

## 硬件要求

- Windows + NVIDIA GPU（≥8GB 显存，已适配 CUDA，RTX 4090 实测加载 7s、推理 ~13s/条）
- 或 Apple Silicon Mac（M1 Pro+ 推荐），16GB+ 内存（MPS，实测加载 13s、推理 ~63s/条）

## ✅ 模型权重说明

当前 `qwen3.5-4b/` 目录中为 **服务器 LLaMA-Factory 合并导出的微调权重**（bf16，9.08GB，Macro Acc 89.04% 基准）。冒烟测试 4/4 通过，输出严格符合训练 Schema（6 大类 23 字段齐全）。基座模型备份在 `qwen3.5-4b-base-backup/`（确认无需后可删除）。

## 开发状态

详见 `TASKS.md`。Phase 0-3 均已完成（3.4 打包按需跳过）。本地验收：JSON 解析率 100%、损伤判定 100%、巡检优先级 100%，RTX 4090 推理 ~13s/条。
