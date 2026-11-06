# HANDOFF — 项目交接文档

> **新会话恢复指南**: 每次新会话先读此文件 + PROJECT.md + TASKS.md

---

## 1. 当前项目状态 (2026-08-03)

**阶段**: 四模型实验序列完成。Exp-3（9B）全量跑通，对比分析就绪；Exp-4（4B）训练与推理完成，评估报告待生成。

### 已完成
- ✅ **Exp-1: Qwen3-VL-2B 基线**（Loss=0.2338, Macro Acc=88.70%, 损伤F1=49.04%）
- ✅ **Exp-2: Qwen3-VL-8B 服务器微调**（2×4090，推理评估完成）
- ✅ **Exp-3: Qwen3.5-9B**（训练→vLLM推理→JSON 100%→评估报告→对比分析）
  - 12字段 Macro Acc: **89.57%**, 4字段 QWK: **+0.7571**, 损伤类型 Macro-F1: **52.81%**
  - 对比分析: `Results4reports/qwen35_9b/compare_9b_vs_8b.md`
  - 9B 全面超越 8B/2B，稀有类（腐蚀/裂纹/断裂）F1 提升 10~17pp
- ✅ **Exp-4: Qwen3.5-4B**（训练→合并→vLLM推理完成，JSON 100%）
  - 配置: `qwen35-4b_server/`（基于 9B 复制改造）
  - 待评估报告

### 进行中 / 待办
- ⬜ **4B 评估报告**: 服务器上 `python eval_report.py`（默认路径已改为相对路径）
- ⬜ **4B 对比分析**: 与 9B/8B/2B 同口径对比，评估本地部署可行性
- ⬜ 稀有类别合并实验（原 Phase 5）
- ⬜ 困难样本加权实验
- ⬜ 论文撰写（第四章：模型实验对比）

---

## 2. 重要文件位置

### 本地 macOS（SFT/ 目录下的文档与结果）

| 文件 | 说明 |
|------|------|
| `PROJECT.md` | 项目总纲（硬件、模型实验序列、数据集、评估方法） |
| `HANDOFF.md` | 本文件 — 会话交接 |
| `TASKS.md` | 任务追踪（含四模型详细结果） |
| `PROGRESS.md` | 研究日志（调研、设计、实验结果） |
| `CHANGELOG.md` | 代码变更日志（倒序） |
| `Results4reports/qwen35_9b/compare_9b_vs_8b.md` | 9B vs 8B 对比分析报告 |
| `Results4reports/qwen35_9b/report.md` | 9B 评估报告（eval_report.py 生成） |
| `Results4reports/qwen3vl8b/report.md` | 8B 评估报告 |
| `qwen3.5-9b_server/` | 9B 微调配置（train/merge/eval/README） |
| `qwen35-4b_server/` | 4B 微调配置（同上，复制改造版） |

### 云服务器 `/root/shared-nvme/finetune/`

| 目录 | 说明 |
|------|------|
| `models/qwen3.5-4b/` | 4B 基座模型（ModelScope 下载，9.34GB） |
| `data/` | 数据集（dataset_train.json + dataset_test.json + images/） |
| `output/qwen3.5-4b/` | 4B 训练输出（LoRA 权重 + 训练日志） |
| `merged_model/qwen3.5-4b/` | 4B 合并后完整模型 |
| `eval_results/test/` | 4B 推理结果 + 评估报告输出 |
| `qwen3.5-9b_server/` | 9B 配置（历史，已执行） |
| `qwen35-4b_server/` | 4B 配置（当前） |

---

## 3. 服务器环境速查

| 项 | 值 |
|----|-----|
| 环境 | `conda activate lma`（训练）/ `vllm-qwen`（推理） |
| PyTorch | 2.11.0 + cu130（需 triton==3.6.0） |
| LLaMA-Factory | main 分支 0.9.6.dev0+（`pip install "git+https://github.com/hiyouga/LLaMA-Factory.git@main"`） |
| transformers | main 分支（`pip install "transformers @ git+https://github.com/huggingface/transformers.git@main"`） |
| 推理引擎 | vLLM 0.26.0（TP=2, maxlen=16384, chunk=32, gpu_mem=0.90） |
| 禁装 | nvidia 驱动（overlayfs 会坏） |

### 关键命令

```bash
# 训练
conda activate lma
CUDA_VISIBLE_DEVICES=0,1 llamafactory-cli train qwen35-4b_server/train_4b.yaml

# 合并
llamafactory-cli export qwen35-4b_server/merge_4b.yaml

# chat_template 自检（merge 后必跑）
python qwen35-4b_server/verify_chat_template.py

# vLLM 推理（双卡全量）
conda activate vllm-qwen
python qwen35-4b_server/eval_model_35_4b_vllm.py \
    --model merged_model/qwen3.5-4b \
    --tensor-parallel-size 2 --max-model-len 16384 --chunk-size 32 \
    --eval-report --output eval_results/test

# 评估报告
conda activate lma
python qwen35-4b_server/eval_report.py
```

---

## 4. 四模型结果速查

| 指标 | 2B（旧代） | 8B（旧代） | 9B（新代） | 4B（新代，待测） |
|------|:--------:|:--------:|:--------:|:--------------:|
| 12 字段 Macro Acc | 88.70% | 89.22% | **89.57%** | 待测 |
| 4 字段 Macro QWK | +0.7344 | +0.7458 | **+0.7571** | 待测 |
| 损伤类型 Macro-F1 | 49.04% | 46.88% | **52.81%** | 待测 |
| 推理方案 | transformers 逐条 | transformers 批量 | **vLLM 批量** | vLLM 批量 |
| 吞吐 | ~16s/条 | ~1-2s/条 | **~0.3s/条** | 待测 |
| 部署显存（4bit） | ~2GB | ~6GB | ~7GB | **~3-4GB** |

---

## 5. 已知注意事项

- **MiniMax 补丁**：vLLM 0.26.0 的 `kernel_warmup.py` 需打补丁跳过 MiniMax warmup（重建容器后重打）
- **chat_template 检验**：Qwen3.5 系列合并后 `tokenizer_config.json` 的 chat_template 可能为空 → vLLM 回退 thinking 模板；merge 后跑 `verify_chat_template.py` 自检修复
- **推理时 enable_thinking=False**：eval 脚本中已内置 `chat_template_kwargs={"enable_thinking": False}`，勿删
- **图片格式三层规范**：OpenAI 兼容 `image_url` + `Path.as_uri()` file:// 协议 + `allowed_local_media_path` 白名单
- **训练 batch 固定**：2×4090 上 QLoRA 训练每卡只能 batch 4（有效 batch 16），视觉激活占显存大头，参数少 ≠ 能放大 batch
- **BERTScore 下载**：首次运行需下载 ~400MB 中文模型，国内服务器可能慢，可设 `--hf-endpoint https://hf-mirror.com`

---

## 6. 当前会话下一步

1. 服务器上跑 `python eval_report.py` 出 4B 评估报告
2. 进行 4B vs 9B/8B/2B 同口径对比分析
3. 确定 4B 是否适合本地部署（量化后 ~3-4GB）
4. 整理三模型对比数据，撰写论文第四章

---

## 7. 平台开发（2026-08-03 新增）

平台开发方案与计划见 `WindDamagePlatform/DEPLOYMENT_PLAN.md`，概述：

- **目标**: 将 Qwen3.5-4B 部署到本地（M1 Pro 16GB）+ Gradio 前端界面，形成风电损伤检测专用平台
- **当前进度**: 方案已定，未开始编码（模型在服务器，需下载）
- **推理框架**: 首选 transformers+MPS（零转换），备选 MLX（性能优化）
- **前端**: Gradio MVP（单图上传 → 结构化展示 → JSON 查看）
- **新会话第一步**: 读 `DEPLOYMENT_PLAN.md` → 执行 Phase 0（下载模型 → 建环境 → 冒烟）