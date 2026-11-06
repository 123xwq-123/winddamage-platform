#!/usr/bin/env python3
"""
风电损伤检测平台 — Phase 0 冒烟测试脚本

验证内容：
  1. 模型能否成功加载（MPS / CPU）
  2. chat_template 自检（enable_thinking=False 是否生效）
  3. 单张图片推理能否产出合法 JSON
  4. 推理延迟和内存占用记录

用法:
  /Users/jianzewang/miniforge3/envs/winddamage/bin/python smoke_test.py
  /Users/jianzewang/miniforge3/envs/winddamage/bin/python smoke_test.py --device cpu
  /Users/jianzewang/miniforge3/envs/winddamage/bin/python smoke_test.py --image data/images/000006.jpg
"""

import sys
import os
import json
import time
import argparse
import traceback
from pathlib import Path

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MODEL_PATH, TEST_JSON, IMAGE_DIR, SYSTEM_PROMPT
from inference import WindDamageModel
from parser import parse_json_pred, validate_report


def run_smoke_test(device: str, image_path: str):
    """执行冒烟测试。"""
    print("=" * 70)
    print("  风电损伤检测平台 — Phase 0 冒烟测试")
    print("=" * 70)
    print(f"  模型路径: {MODEL_PATH}")
    print(f"  测试图片: {image_path}")
    print(f"  目标设备: {device}")
    print("=" * 70)

    results = {
        "model_load": {"ok": False, "time_s": 0, "mem_gb": 0, "error": None},
        "template_check": {"ok": False, "has_template": False, "is_thinking": False, "error": None},
        "inference": {"ok": False, "time_s": 0, "json_parsed": False, "error": None},
        "output_quality": {"ok": False, "valid_report": False, "missing": [], "error": None},
    }

    # ─── Step 1: 加载模型 ────────────────────────────────
    print("\n[Step 1] 加载模型...")
    t0 = time.time()
    try:
        model = WindDamageModel(device=device)
        load_time, load_info = model.load()
        results["model_load"]["ok"] = True
        results["model_load"]["time_s"] = round(load_time, 1)

        # 记录内存
        import torch
        if device == "mps":
            mem = torch.mps.current_allocated_memory() / 1024**3
        elif device == "cuda":
            mem = torch.cuda.memory_allocated() / 1024**3
        else:
            # CPU: 估算模型参数内存
            mem = sum(p.nelement() * p.element_size() for p in model.model.parameters()) / 1024**3
        results["model_load"]["mem_gb"] = round(mem, 2)
        print(f"  ✅ {load_info}")
    except Exception as e:
        results["model_load"]["error"] = str(e)
        print(f"  ❌ 加载失败: {e}")
        traceback.print_exc()
        return results

    # ─── Step 2: chat_template 自检 ────────────────────────
    print("\n[Step 2] chat_template 自检...")
    try:
        check = model.chat_template_check()
        results["template_check"]["ok"] = check["enable_thinking_false_works"]
        results["template_check"]["has_template"] = check["has_template"]
        results["template_check"]["is_thinking"] = check["is_thinking_template"]

        if check["has_template"]:
            print(f"  模板存在: ✅")
            print(f"  含 thinking 逻辑: {'是 (需关闭)' if check['is_thinking_template'] else '否'}")
        else:
            print(f"  ⚠️ 模板为空，vLLM/transformers 会回退默认模板")

        if check["enable_thinking_false_works"]:
            print(f"  enable_thinking=False 生效: ✅")
            print(f"  生成前缀尾80字符: ...{repr(check['sample_prefix'])}")
        else:
            print(f"  ❌ enable_thinking=False 不生效: {check['sample_prefix']}")
    except Exception as e:
        results["template_check"]["error"] = str(e)
        print(f"  ❌ 自检失败: {e}")
        traceback.print_exc()

    # ─── Step 3: 单图推理 ────────────────────────────────
    print(f"\n[Step 3] 推理测试: {image_path}")
    try:
        parsed, raw, infer_time = model.infer(image_path)
        results["inference"]["time_s"] = round(infer_time, 1)

        if parsed is not None:
            results["inference"]["ok"] = True
            results["inference"]["json_parsed"] = True
            print(f"  ✅ 推理成功 ({infer_time:.1f}s)")
            print(f"  JSON 解析: ✅")

            # 展示关键字段
            print(f"\n  --- 推理结果摘要 ---")
            for section in ["1. 构件识别", "2. 损伤判定", "6. 结论建议"]:
                if section in parsed:
                    for k, v in parsed[section].items():
                        print(f"  {section}/{k}: {v}")

            # 校验报告完整性
            val = validate_report(parsed)
            results["output_quality"]["ok"] = val["valid"]
            results["output_quality"]["valid_report"] = val["valid"]
            results["output_quality"]["missing"] = val["missing"]
            if val["valid"]:
                print(f"\n  报告完整性: ✅ (全部字段就位)")
            else:
                print(f"\n  ⚠️ 报告缺字段: {val['missing']}")
        else:
            print(f"  ⚠️ 推理完成但 JSON 解析失败 ({infer_time:.1f}s)")
            print(f"  原始输出前 500 字符:")
            print(f"  {raw[:500]}")
            results["inference"]["error"] = "JSON 解析失败"

        print(f"\n  --- 原始输出前 300 字符 ---")
        print(f"  {raw[:300]}")

    except Exception as e:
        results["inference"]["error"] = str(e)
        print(f"  ❌ 推理失败: {e}")
        traceback.print_exc()

        # 尝试检测是否是 MPS 不兼容
        error_str = str(e).lower()
        if "mps" in error_str or "metal" in error_str or "fallback" in error_str:
            print(f"\n  ⚠️ 检测到 MPS 不兼容错误！建议: python smoke_test.py --device cpu")

    # ─── 总结 ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  冒烟测试总结")
    print("=" * 70)
    all_ok = True
    for step, result in results.items():
        ok = result.get("ok", False)
        status = "✅" if ok else "❌"
        print(f"  {status} {step}")
        if not ok:
            all_ok = False

    if all_ok:
        print(f"\n  ✅ Phase 0 冒烟测试通过！可进入 Phase 1 (MVP 开发)")
    else:
        print(f"\n  ⚠️ 部分测试未通过，需排查后重试")
    print("=" * 70)

    # 保存结果
    result_path = os.path.join(os.path.dirname(__file__), "smoke_test_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  结果已保存: {result_path}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 0 冒烟测试")
    parser.add_argument("--device", default=None,
                        help="推理设备: cuda (默认) / cpu")
    parser.add_argument("--image", default=None,
                        help="测试图片路径 (默认用 data/images/000006.jpg)")
    args = parser.parse_args()

    device = args.device or "cuda"
    image = args.image or os.path.join(IMAGE_DIR, "000006.jpg")

    if not os.path.exists(image):
        # 找一张存在的图片
        if os.path.exists(IMAGE_DIR):
            imgs = sorted(Path(IMAGE_DIR).glob("*.jpg"))
            if imgs:
                image = str(imgs[0])
                print(f"[INFO] 指定图片不存在，使用: {image}")
            else:
                print(f"[ERROR] images/ 目录下没有图片")
                sys.exit(1)
        else:
            print(f"[ERROR] 图片目录不存在: {IMAGE_DIR}")
            sys.exit(1)

    run_smoke_test(device, image)
