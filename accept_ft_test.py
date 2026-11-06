#!/usr/bin/env python3
"""微调权重到位后的 3 条测试集验收（直接推理，不依赖 Gradio 服务）。"""

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from config import TEST_JSON, IMAGE_DIR
from inference import WindDamageModel

with open(TEST_JSON, encoding="utf-8") as f:
    data = json.load(f)

# 找出本地已有图片的样本
local = []
for d in data:
    imgs = d.get("images") or []
    if imgs:
        name = os.path.basename(imgs[0])
        p = os.path.join(IMAGE_DIR, name)
        if os.path.exists(p):
            label = json.loads(d["messages"][-1]["content"])
            local.append((name, p, label))

print(f"本地带标注样本: {len(local)} 条")

model = WindDamageModel()
model.load()

results = []
for name, path, label in local:
    t0 = time.time()
    parsed, raw, _ = model.infer(path)
    elapsed = time.time() - t0

    def gt(section, key):
        return label.get(section, {}).get(key, "?")

    def pr(section, key):
        return (parsed or {}).get(section, {}).get(key, "?")

    ok_json = parsed is not None
    d_match = ok_json and pr("2. 损伤判定", "是否存在损伤") == gt("2. 损伤判定", "是否存在损伤")
    t_match = ok_json and pr("2. 损伤判定", "损伤类型") == gt("2. 损伤判定", "损伤类型")
    p_match = ok_json and pr("6. 结论建议", "巡检优先级") == gt("6. 结论建议", "巡检优先级")

    print(f"\n[{name}] {elapsed:.1f}s  JSON={'✅' if ok_json else '❌'}  "
          f"损伤={'✅' if d_match else '❌'}  类型={'✅' if t_match else '❌'}  优先级={'✅' if p_match else '❌'}")
    print(f"  label: 损伤={gt('2. 损伤判定', '是否存在损伤')} 类型={gt('2. 损伤判定', '损伤类型')} "
          f"优先级={gt('6. 结论建议', '巡检优先级')}")
    print(f"  pred : 损伤={pr('2. 损伤判定', '是否存在损伤')} 类型={pr('2. 损伤判定', '损伤类型')} "
          f"优先级={pr('6. 结论建议', '巡检优先级')}")

    results.append({
        "image": name, "elapsed_s": round(elapsed, 1), "json_ok": ok_json,
        "damage_match": d_match, "type_match": t_match, "priority_match": p_match,
    })

n = len(results)
summary = {
    "total": n,
    "json_rate": sum(r["json_ok"] for r in results) / n,
    "damage_acc": sum(r["damage_match"] for r in results) / n,
    "type_acc": sum(r["type_match"] for r in results) / n,
    "priority_acc": sum(r["priority_match"] for r in results) / n,
    "avg_time_s": round(sum(r["elapsed_s"] for r in results) / n, 1),
    "details": results,
}
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accept_ft_result.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 60)
print(f"JSON 解析率: {summary['json_rate']*100:.0f}%  损伤判定: {summary['damage_acc']*100:.0f}%  "
      f"损伤类型: {summary['type_acc']*100:.0f}%  优先级: {summary['priority_acc']*100:.0f}%  "
      f"平均 {summary['avg_time_s']}s/条")
print(f"结果已保存: {out}")
