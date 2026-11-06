"""
风电结构损伤检测平台 — 输出解析模块

复刻上游 eval_model_35_4b_vllm.py 中的解析逻辑：
  1. strip_thinking: 剥离 Qwen3.5 thinking 内容
  2. parse_json_pred: JSON 容错解析
  3. validate_report: 字段完整性校验
"""

import re
import json
from typing import Optional, Dict, Any


def strip_thinking(raw: str) -> str:
    """剥离 Qwen3.5 thinking 内容（若模型意外输出 <think>...</think>）。

    处理三种情况：
    1. 完整 <think>...</think> 标签
    2. <|think|> 变体标签
    3. 模板注入的 <think> 开头，raw 以 CoT 文本开头、仅 </think> 结尾
    """
    if not raw:
        return raw
    # 情况 1: 完整 <think>...</think> 标签
    stripped = re.sub(r"<think>.*?</think>\s*", "", raw, flags=re.DOTALL)
    # 情况 2: <|think|> 变体标签
    stripped = re.sub(r"<\|think\|>.*?</\|think\|>\s*", "", stripped, flags=re.DOTALL)
    # 情况 3: 模板已注入 <think> 开头, raw 以 CoT 文本开头、仅含 </think> 结尾
    # (Qwen3.5 默认模板行为: 输出 = 推理内容 + </think> + JSON)
    stripped = re.sub(r"^.*?</think>\s*", "", stripped, flags=re.DOTALL)
    return stripped.strip()


def parse_json_pred(raw: str) -> Optional[Dict[str, Any]]:
    """解析预测输出为 JSON，自动剥离 think 内容，支持 {…} 提取兜底。"""
    if raw is None:
        return None
    cleaned = strip_thinking(raw)
    # 尝试直接解析
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass
    # 兜底：提取第一个 { ... } 块
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def get_field(report: Dict, section: str, field: str, default: str = "") -> str:
    """从嵌套 JSON 报告中安全提取字段值。"""
    try:
        return str(report.get(section, {}).get(field, default)).strip()
    except (AttributeError, TypeError):
        return default


def validate_report(report: Optional[Dict]) -> dict:
    """校验 JSON 报告的字段完整性，返回校验结果。"""
    if report is None:
        return {"valid": False, "missing": ["all"], "message": "JSON 解析失败"}

    required_sections = [
        "图像Caption", "1. 构件识别", "2. 损伤判定",
        "3. 潜在风险影响分析", "4. 运维与处置建议",
        "5. 不确定性说明与调查建议", "6. 结论建议"
    ]
    missing = [s for s in required_sections if s not in report]

    return {
        "valid": len(missing) == 0,
        "missing": missing,
        "message": "OK" if not missing else f"缺少: {', '.join(missing)}"
    }
