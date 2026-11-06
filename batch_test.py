#!/usr/bin/env python3
"""批量验证脚本 — 通过 HTTP API 调用 Gradio 后端测试 5 张图片。"""

import json, os, time, sys
from gradio_client import Client

# 加载测试样本
with open("/tmp/test_samples.json") as f:
    samples = json.load(f)

print(f"开始批量验证 ({len(samples)} 张图片)")
print("=" * 70)

results = []
client = Client("http://localhost:7860", verbose=False)

from gradio_client import handle_file

for i, s in enumerate(samples):
    print(f"\n[{i+1}/{len(samples)}] {s['image_name']} (期望: 损伤={s['has_damage']}, 类型={s['damage_type']})")
    t0 = time.time()
    try:
        result = client.predict(
            image=handle_file(s["image"]),
            api_name="/analyze_image",
        )
        elapsed = time.time() - t0
        # result = (summary, detail_html, json_str, status)
        summary, detail_html, json_str, status = result
        print(f"  耗时: {elapsed:.1f}s")
        print(f"  状态: {status}")

        # 解析 JSON 结果
        if json_str:
            try:
                pred = json.loads(json_str)
                pred_damage = pred.get("2. 损伤判定", {}).get("是否存在损伤", "?")
                pred_type = pred.get("2. 损伤判定", {}).get("损伤类型", "?")
                pred_component = pred.get("1. 构件识别", {}).get("构件名称", "?")
                pred_priority = pred.get("6. 结论建议", {}).get("巡检优先级", "?")
                print(f"  预测: 损伤={pred_damage} | 类型={pred_type} | 构件={pred_component} | 优先级={pred_priority}")

                # 与 label 对比
                match_damage = "✅" if pred_damage == s["has_damage"] else "❌"
                match_priority = "✅" if pred_priority == s["label_priority"] else "❌"
                print(f"  对比: 损伤 {match_damage} (label={s['has_damage']}, pred={pred_damage}) | 优先级 {match_priority} (label={s['label_priority']}, pred={pred_priority})")

                results.append({
                    "image": s["image_name"],
                    "elapsed": round(elapsed, 1),
                    "damage_match": pred_damage == s["has_damage"],
                    "priority_match": pred_priority == s["label_priority"],
                    "json_valid": True,
                })
            except json.JSONDecodeError:
                print(f"  ⚠️ JSON 解析失败")
                results.append({"image": s["image_name"], "elapsed": round(elapsed, 1), "json_valid": False})
        else:
            print(f"  ⚠️ 无 JSON 输出")
            results.append({"image": s["image_name"], "elapsed": round(elapsed, 1), "json_valid": False})

    except Exception as e:
        print(f"  ❌ 错误: {e}")
        results.append({"image": s["image_name"], "error": str(e)})

# 总结
print("\n" + "=" * 70)
print("验证总结")
print("=" * 70)
total = len(results)
json_ok = sum(1 for r in results if r.get("json_valid"))
damage_ok = sum(1 for r in results if r.get("damage_match"))
priority_ok = sum(1 for r in results if r.get("priority_match"))
avg_time = sum(r.get("elapsed", 0) for r in results) / total if total else 0

print(f"  JSON 解析率: {json_ok}/{total} ({json_ok/total*100:.0f}%)")
print(f"  损伤判定正确: {damage_ok}/{total} ({damage_ok/total*100:.0f}%)")
print(f"  优先级正确: {priority_ok}/{total} ({priority_ok/total*100:.0f}%)")
print(f"  平均推理时间: {avg_time:.1f}s")

with open("/tmp/batch_test_results.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存: /tmp/batch_test_results.json")
