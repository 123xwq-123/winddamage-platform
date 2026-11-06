"""
风电塔灾损测算软件 — 历史记录模块

SQLite 存储，支持保存检测记录、查询历史、回看详情。
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表。"""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL,
            image_name  TEXT    NOT NULL,
            image_path  TEXT,
            high_risk   INTEGER DEFAULT 0,
            has_damage  TEXT,
            damage_type TEXT,
            component   TEXT,
            priority    TEXT,
            confidence  TEXT,
            json_report TEXT    NOT NULL,
            infer_time  REAL
        )
    """)
    conn.commit()
    conn.close()


def save_record(image_name: str, json_report: dict, infer_time: float = 0,
                image_path: str = "") -> int:
    """保存一条检测记录，返回记录 ID。"""
    from formatter import is_high_risk
    from parser import get_field

    report = json_report or {}
    high_risk = 1 if is_high_risk(report) else 0
    has_damage = get_field(report, "2. 损伤判定", "是否存在损伤")
    damage_type = get_field(report, "2. 损伤判定", "损伤类型")
    component = get_field(report, "1. 构件识别", "构件名称")
    priority = get_field(report, "6. 结论建议", "巡检优先级")
    confidence = get_field(report, "6. 结论建议", "本次判断的置信度")

    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO detections
            (timestamp, image_name, image_path, high_risk, has_damage,
             damage_type, component, priority, confidence, json_report, infer_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        image_name, image_path, high_risk, has_damage,
        damage_type, component, priority, confidence,
        json.dumps(report, ensure_ascii=False), round(infer_time, 1),
    ))
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def list_records(limit: int = 50) -> List[Dict]:
    """查询最近 N 条记录（摘要信息，不含完整 JSON）。"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT id, timestamp, image_name, high_risk, has_damage,
               damage_type, component, priority, confidence, infer_time
        FROM detections
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_record(record_id: int) -> Optional[Dict]:
    """根据 ID 查询单条记录详情（含完整 JSON）。"""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM detections WHERE id = ?", (record_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def clear_all():
    """清空所有历史记录。"""
    conn = get_conn()
    conn.execute("DELETE FROM detections")
    conn.commit()
    conn.close()


def get_stats() -> Dict:
    """返回统计摘要。"""
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
    high = conn.execute("SELECT COUNT(*) FROM detections WHERE high_risk=1").fetchone()[0]
    damaged = conn.execute(
        "SELECT COUNT(*) FROM detections WHERE has_damage='是'"
    ).fetchone()[0]
    avg_time = conn.execute(
        "SELECT AVG(infer_time) FROM detections WHERE infer_time > 0"
    ).fetchone()[0]
    conn.close()
    return {
        "total": total,
        "high_risk": high,
        "damaged": damaged,
        "normal": total - damaged,
        "avg_time": round(avg_time, 1) if avg_time else 0,
    }
