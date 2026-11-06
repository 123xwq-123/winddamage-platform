# 风电结构损伤检测大模型智能平台 — 项目总纲

> **文档用途**: 项目全景索引。新会话先读 `DEPLOYMENT_PLAN.md` + 本文件 + `TASKS.md`，即可掌握全部上下文。
> **创建日期**: 2026-08-03 ｜ **状态**: Phase 0 准备中
> **项目目录**: `WindDamagePlatform/`

---

## 1. 一句话定位

将已微调完成的 **Qwen3.5-4B 风电损伤检测模型**部署到本地 Mac（M1 Pro 16GB），用 Gradio 构建面向巡检人员的「图片上传 → 智能损伤检测 → 结构化报告展示」专用平台。

---

## 2. 上游研究成果

本项目是 SFT/（微调实验）的下游部署环节。上游已完成四组模型实验：

| Exp | 模型 | 12字段 Macro Acc | 损伤类型 Macro-F1 | 状态 |
|:---:|------|:---:|:---:|:---:|
| Exp-1 | Qwen3-VL-2B | 88.70% | 49.04% | ✅ |
| Exp-2 | Qwen3-VL-8B | 89.22% | 46.88% | ✅ |
| Exp-3 | Qwen3.5-9B | **89.57%** | **52.81%** | ✅ |
| **Exp-4** | **Qwen3.5-4B** | 89.04% | — | ✅ 选定部署 |

**选定 4B 的原因**: 与 9B 同代架构、4bit 量化后 ~3-4GB 可在 16GB M1 Pro 上运行、输出严格 JSON。

上游详情见 `HANDOFF.md`。

---

## 3. 技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| 模型 | Qwen3.5-4B（Qwen3_5ForConditionalGeneration） | 4.66B 参数，32 层 Gated DeltaNet 混合注意力 + ViT 视觉编码器 |
| 推理框架 | transformers + MPS（首选） | 零格式转换；备选 MLX（性能优化）/ GGUF（兼容性） |
| 前端 | Gradio | MVP 快速开发；备选 FastAPI + Vue/React |
| 运行环境 | macOS 15.x, Apple M1 Pro 16GB | 统一内存架构，无独立 GPU |
| Python | 3.11 | conda 环境 `winddamage` |

---

## 4. 模型架构详情

```
Qwen3_5ForConditionalGeneration
├── vision_config (ViT)
│   ├── depth: 24 层
│   ├── hidden_size: 1024 → out_hidden_size: 2560
│   ├── patch_size: 16, spatial_merge_size: 2
│   └── processor: Qwen3VLProcessor
└── text_config
    ├── 32 层（每 4 层 1 个 full_attention + 3 个 linear_attention）
    ├── hidden_size: 2560
    ├── num_attention_heads: 16, num_key_value_heads: 4
    ├── Gated DeltaNet: linear_conv_kernel_dim=4, linear_key_head_dim=128
    ├── vocab_size: 248,320
    └── rope: mrope_interleaved, mrope_section=[11,11,10]
```

**关键约束**: Gated DeltaNet 层需要特定的 kernel 实现。服务器端用 vLLM 内置 kernel；本地 transformers 需依赖 `fla` + `triton` 或回退实现，MPS 兼容性待验证。

---

## 5. 数据集

| 项 | 值 |
|----|-----|
| 测试集 | `data/dataset_test.json`（2168 条） |
| 图片目录 | `data/images/`（当前仅 20 张，冒烟够用） |
| 样本结构 | system prompt + user(`<image>` + 指令) + assistant(JSON 回答) + images 路径 |
| 输出 Schema | 6 大类、23 个叶子字段的嵌套 JSON |

### System Prompt

```
你是风电结构损伤检测领域的顶尖专家。请根据输入的巡检图像，对风电结构构件进行识别和损伤评估。
输出必须为完整的JSON格式，每个描述字段不超过50字，是/否类问题只填是或否，置信度填高/中/低。
```

### User Prompt

```
请分析这张风电结构巡检图像，输出标准化的损伤评估JSON报告。
```

### 输出 JSON 结构（6 大类 / 23 字段）

```
{
  "图像Caption": { "简要": "...", "图像质量评价": "清晰/一般/模糊" },
  "1. 构件识别": { "构件名称": "...", "构件所属系统": "..." },
  "2. 损伤判定": {
    "是否可判定": "是/否", "是否存在损伤": "是/否",
    "损伤类型": "无损伤/涂层破损/腐蚀/裂纹/断裂/结构变形/...",
    "不可判定原因": "...", "损伤分布位置与范围": "...",
    "关键视觉证据描述": "...", "可能的成因推测": "...",
    "损伤发展趋势": "稳定/恶化/..."
  },
  "3. 潜在风险影响分析": {
    "对结构安全性的影响程度": "无/低/中/高",
    "是否对机组运行可靠性影响": "是/否",
    "是否对长期服役寿命的影响": "是/否"
  },
  "4. 运维与处置建议": {
    "是否建议停机、限功率运行或重点监测": "是/否",
    "短期处置建议": "...", "中长期修复或改进建议": "...",
    "后续巡检建议关注的问题": "..."
  },
  "5. 不确定性说明与调查建议": {
    "是否建议补充获取更高分辨率或多角度图像": "是/否",
    "是否建议结合现场巡检或历史运维数据进行综合判断": "是/否",
    "当前是否建议仅基于该图像做出维修或停机决策": "是/否"
  },
  "6. 结论建议": { "本次判断的置信度": "高/中/低", "巡检优先级": "低/中/高" }
}
```

---

## 6. 部署验收基准

| 验收项 | 标准 | 来源 |
|--------|------|------|
| 模型加载 | 启动 ≤ 60s，内存 ≤ 8GB | DEPLOYMENT_PLAN §3.4 |
| 单图推理 | ≤ 60s | DEPLOYMENT_PLAN §3.4 |
| JSON 解析率 | 20 条测试 ≥ 95%（目标 100%） | DEPLOYMENT_PLAN §3.4 |
| 结果一致性 | 与服务器结果主要指标差距 ≤ 2pp | DEPLOYMENT_PLAN §3.4 |
| 4B 服务器基准 | Macro Acc 89.04%, QWK 0.7471 | `SFT/Results4reports/qwen35_4b/report.md` |

---

## 7. 关键约束清单（从上游继承）

1. **nothink 模式**: 模型用 `qwen3_5_nothink` 微调，推理必须关闭 thinking（`enable_thinking=False`），否则输出 ` PWM` 破坏 JSON
2. **chat_template 校验**: tokenizer_config.json 含官方 thinking 模板；推理时通过 `chat_template_kwargs` 关闭
3. **JSON 兜底解析**: 解析失败时 `re.search(r"\{.*\}", raw, re.DOTALL)` 提取
4. **图像预处理**: 按训练一致参数（qwen-vl-utils 的 `process_vision_info`）
5. **温度=0**: `SamplingParams(temperature=0.0, top_p=1.0)` 保证可复现

---

## 8. 文件索引

### 本项目（WindDamagePlatform/）

| 文件 | 说明 |
|------|------|
| `DEPLOYMENT_PLAN.md` | 部署方案主文档（需求、选型、风险、分阶段计划） |
| `PROJECT.md` | 本文件 — 项目总纲 |
| `TASKS.md` | 任务追踪（分阶段任务、验收标准、问题日志） |
| `HANDOFF.md` | 上游实验交接（四模型结果、服务器环境、已知坑） |
| `qwen3.5-4b/` | 模型权重（bf16, 8.4GB） |
| `data/dataset_test.json` | 测试集（2168 条） |
| `data/images/` | 测试图片（当前 20 张） |

### 上游参考（SFT/）

| 文件 | 说明 |
|------|------|
| `SFT/qwen35-4b_server/eval_model_35_4b_vllm.py` | vLLM 推理脚本（含完整 prompt/解析/防护逻辑，本地推理蓝本） |
| `SFT/qwen35-4b_server/verify_chat_template.py` | chat_template 自检脚本参考 |
| `SFT/qwen35-4b_server/eval_report.py` | 评估报告生成脚本 |
| `SFT/Results4reports/qwen35_4b/report.md` | 4B 完整评估报告（验收基准） |
| `SFT/Results4reports/qwen35_9b/compare_9b_vs_8b.md` | 9B vs 8B 对比分析 |

### 服务器（容器云 `/root/shared-nvme/finetune/`）

| 路径 | 说明 |
|------|------|
| `merged_model/qwen3.5-4b/` | 4B 合并后完整模型（已下载到本地） |
| `data/dataset_test.json` | 测试集（已下载到本地） |
| `data/images/` | 全量测试图片（2168 张，本地仅 20 张） |
