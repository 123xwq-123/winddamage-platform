"""新版大屏 /screen 路由层：页面服务端渲染 + JSON API。

设计文档：OUTPUT/设计文档.md；实施计划：OUTPUT/实施计划.md。
原则：复用 auth/history/app 推理层，旧界面（/ 入口）零改动。
"""
import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

import auth

router = APIRouter(prefix="/screen")

SCREEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "screen")

# 迭代期静态资源不缓存（皮肤迭代教训：浏览器缓存造成"改了没生效"假象）
_NO_CACHE = {"Cache-Control": "no-cache"}


def _page(html: str) -> HTMLResponse:
    return HTMLResponse(html, headers=_NO_CACHE)


def _current_user(request: Request):
    """当前会话用户（复用 wd_session Cookie，与旧入口通用）。"""
    return auth.user_for_request(request)


# ─── 登录 ─────────────────────────────────────────────────────
def _login_page_html(error: str = "") -> str:
    err = f'<div class="sc-form-error">{error}</div>' if error else ""
    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>登录 · 智慧风电检测监管平台</title>'
        '<link rel="stylesheet" href="/screen-assets/screen.css"></head>'
        '<body class="sc-page sc-login">'
        '<div class="sc-login-box sc-panel">'
        '<div class="sc-login-title">智慧风电检测监管平台</div>'
        '<div class="sc-login-sub">WIND POWER INSPECTION PLATFORM</div>'
        + err +
        '<form method="post" action="/screen/login">'
        '<label>账号<input name="username" autocomplete="username" required></label>'
        '<label>密码<input name="password" type="password" autocomplete="current-password" required></label>'
        '<button class="sc-btn primary" type="submit">登 录</button>'
        '</form></div></body></html>')


@router.get("/login", response_class=HTMLResponse)
async def login_page(error: str = ""):
    return _page(_login_page_html("账号或密码错误" if error else ""))


@router.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    status, payload = auth.authenticate(str(form.get("username") or ""),
                                        str(form.get("password") or ""))
    if status == "ok":
        resp = RedirectResponse("/screen", status_code=302)
        resp.set_cookie(
            auth.SESSION_COOKIE, auth.create_session(payload["id"]),
            httponly=True, samesite="lax",
            max_age=auth.SESSION_TTL_HOURS * 3600, path="/")
        return resp
    if status == "locked":
        return _page(_login_page_html(f"尝试过多，已锁定，请 {payload} 分钟后重试"))
    return _page(_login_page_html("账号或密码错误"))


# ─── 页面（骨架占位；Task 4-7 逐页充实） ──────────────────────
@router.get("", response_class=HTMLResponse)
async def home_page(request: Request):
    with open(os.path.join(SCREEN_DIR, "home.html"), encoding="utf-8") as f:
        return _page(f.read())


@router.get("/batch", response_class=HTMLResponse)
async def batch_page(request: Request):
    with open(os.path.join(SCREEN_DIR, "batch.html"), encoding="utf-8") as f:
        return _page(f.read())


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    with open(os.path.join(SCREEN_DIR, "history.html"), encoding="utf-8") as f:
        return _page(f.read())


@router.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):
    return _page("<h1>screen account placeholder</h1>")


# ─── JSON API ─────────────────────────────────────────────────
import json as _json
import shutil as _shutil
import tempfile as _tempfile
import time as _time
from datetime import date as _date, timedelta as _timedelta

import history


@router.get("/api/me")
async def api_me(request: Request):
    user = _current_user(request)
    if not user:
        return JSONResponse({"username": None, "role": None})
    return JSONResponse({"username": user["username"], "role": user.get("role")})


def _scope(user):
    """(owner_scope, is_admin)：admin 见全量，普通用户仅本人。"""
    if not user:
        return 0, False
    return (None, True) if user.get("role") == "admin" else (user["id"], False)


def _row_item(row):
    """history 行 → 大屏历史/快查 JSON。"""
    return {
        "id": row["id"], "timestamp": row["timestamp"], "image_name": row["image_name"],
        "high_risk": bool(row["high_risk"]), "has_damage": row["has_damage"],
        "damage_type": row["damage_type"], "component": row["component"],
        "priority": row["priority"], "confidence": row["confidence"],
        "infer_time": row["infer_time"], "note": row.get("note", ""),
    }


def _overview_payload(owner_scope, week, recheck):
    stats = history.get_stats(owner_scope)
    total = stats["total"]
    completion = round(100 * min(total, 120) / 120) if total else 0
    return {"total": total, "week": week, "high_risk": stats["high_risk"],
            "recheck": recheck, "completion": completion}


def _report_payload(parsed, record_id, infer_time, image_info, recent):
    """模型报告 → 大屏右列完整报告 JSON（设计文档 §5）。"""
    from app import _damage_locator_payload, format_summary
    from parser import get_field
    import i18n
    level = get_field(parsed, i18n.SECTION_CONCLUSION, "巡检优先级") or "低"
    dtype = get_field(parsed, i18n.SECTION_DAMAGE, "损伤类型")
    conf = get_field(parsed, i18n.SECTION_CONCLUSION, "本次判断的置信度")
    advice = {"高": "72 小时内停机复检", "中": "纳入例行巡检计划"}.get(level.strip(), "保持常规观察")
    return {
        "record_id": record_id,
        "summary": format_summary(parsed),
        "risk": {"level": level.strip(), "type": dtype, "confidence": conf},
        "kv": {
            "component": get_field(parsed, i18n.SECTION_COMPONENT, "构件名称"),
            "location": get_field(parsed, i18n.SECTION_DAMAGE, "损伤分布位置与范围"),
            "size": (get_field(parsed, i18n.SECTION_DAMAGE, "损伤程度")
                     or get_field(parsed, i18n.SECTION_DAMAGE, "损伤尺寸")
                     or dtype),
            "advice": advice,
            "model": "多模态大模型 v3",
            "time": _time.strftime("%Y-%m-%d %H:%M:%S"),
            "report_no": f"RPT-{_time.strftime('%Y%m%d')}-{record_id:04d}",
        },
        "locator": _damage_locator_payload(parsed),
        "image_info": image_info,
        "recent": recent,
    }


def _week_count(owner_scope):
    monday = (_date.today() - _timedelta(days=_date.today().weekday())).strftime("%Y-%m-%d")
    _, total = history.query_records(limit=1, offset=0, owner_user_id=owner_scope,
                                     date_from=monday)
    return total


@router.get("/api/overview")
async def api_overview(request: Request):
    user = _current_user(request)
    scope, _is_admin = _scope(user)
    return JSONResponse(_overview_payload(scope, _week_count(scope),
                                          history.get_stats(scope)["high_risk"]))


@router.post("/api/analyze")
async def api_analyze(request: Request):
    user = _current_user(request)
    if not user:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    form = await request.form()
    up = form.get("file")
    if up is None or not getattr(up, "filename", ""):
        return JSONResponse({"detail": "no file"}, status_code=400)
    from app import _do_inference, get_image_info
    tmpd = _tempfile.mkdtemp(prefix="sc_")
    path = os.path.join(tmpd, os.path.basename(up.filename))
    with open(path, "wb") as f:
        f.write(await up.read())
    try:
        parsed, raw, infer_time = _do_inference(path)
        if parsed is None:
            return JSONResponse({"detail": "inference failed", "raw": str(raw)[:500]},
                                status_code=400)
        owner_scope, _ = _scope(user)
        rid = history.save_record(os.path.basename(up.filename), parsed, infer_time,
                                  path, source="screen", persist_image=True,
                                  owner_user_id=user["id"],
                                  created_by=user["username"])
        rows, _total = history.query_records(limit=6, offset=0, owner_user_id=owner_scope)
        image_info = {"filename": os.path.basename(up.filename),
                      "meta": get_image_info(path) or ""}
        payload = _report_payload(parsed, rid, infer_time, image_info,
                                  [_row_item(r) for r in rows])
        return JSONResponse(payload)
    finally:
        _shutil.rmtree(tmpd, ignore_errors=True)


@router.get("/api/records")
async def api_records(request: Request, page: int = 1, page_size: int = 15,
                      search: str = "", risk: str = "", date_from: str = "",
                      date_to: str = "", sort: str = "time_desc"):
    user = _current_user(request)
    if not user:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    scope, _is_admin = _scope(user)
    rows, total = history.query_records(
        limit=page_size, offset=max(0, (page - 1) * page_size),
        owner_user_id=scope, search=search.strip(),
        risk={"high": "high", "normal": "normal"}.get(risk.strip(), ""),
        date_from=date_from.strip(), date_to=date_to.strip(), sort=sort.strip())
    return JSONResponse({"rows": [_row_item(r) for r in rows], "total": total,
                         "stats": history.get_stats(scope)})


@router.post("/api/batch")
async def api_batch(request: Request):
    """批量分析：逐张推理+入库（失败不中断），返回逐行结果与汇总。

    批量图片不持久化（persist_image=False）避免配额压力；详情可回看报告文本。
    """
    user = _current_user(request)
    if not user:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    form = await request.form()
    uploads = [u for u in form.getlist("files") if getattr(u, "filename", "")]
    if not uploads:
        return JSONResponse({"detail": "no files"}, status_code=400)
    from app import _do_inference
    from parser import get_field
    import i18n
    scope, _ = _scope(user)
    results, high = [], 0
    tmpd = _tempfile.mkdtemp(prefix="scb_")
    try:
        for up in uploads:
            name = os.path.basename(up.filename)
            path = os.path.join(tmpd, name)
            with open(path, "wb") as f:
                f.write(await up.read())
            try:
                parsed, raw, infer_time = _do_inference(path)
                if parsed is None:
                    raise RuntimeError(str(raw)[:200] or "inference failed")
                rid = history.save_record(name, parsed, infer_time, path,
                                          source="screen", persist_image=False,
                                          owner_user_id=user["id"],
                                          created_by=user["username"])
                is_high = bool(history.get_record(rid)["high_risk"])
                high += 1 if is_high else 0
                results.append({
                    "ok": True, "filename": name, "record_id": rid,
                    "component": get_field(parsed, i18n.SECTION_COMPONENT, "构件名称"),
                    "damage_type": get_field(parsed, i18n.SECTION_DAMAGE, "损伤类型"),
                    "priority": get_field(parsed, i18n.SECTION_CONCLUSION, "巡检优先级"),
                    "high_risk": is_high, "infer_time": infer_time,
                })
            except Exception as exc:                       # 单张失败不影响整批
                results.append({"ok": False, "filename": name,
                                "record_id": None, "error": str(exc)[:300]})
    finally:
        _shutil.rmtree(tmpd, ignore_errors=True)
    return JSONResponse({"results": results, "total": len(results),
                         "ok_count": sum(1 for r in results if r["ok"]),
                         "high_risk": high})


@router.get("/api/records/{record_id}")
async def api_record_detail(request: Request, record_id: int):
    user = _current_user(request)
    if not user:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    rec = history.get_record(record_id)
    if not rec:
        return JSONResponse({"detail": "not found"}, status_code=404)
    if not history.can_access(rec, user["id"], user.get("role") == "admin"):
        return JSONResponse({"detail": "forbidden"}, status_code=403)
    import json as _j
    detail = dict(rec)
    try:
        detail["json_report"] = (_j.loads(rec["json_report"])
                                 if isinstance(rec.get("json_report"), str)
                                 else rec.get("json_report"))
    except (ValueError, TypeError):
        pass
    return JSONResponse(detail)


@router.post("/api/records/{record_id}/note")
async def api_record_note(request: Request, record_id: int):
    user = _current_user(request)
    if not user:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    rec = history.get_record(record_id)
    if not rec:
        return JSONResponse({"detail": "not found"}, status_code=404)
    if not history.can_access(rec, user["id"], user.get("role") == "admin"):
        return JSONResponse({"detail": "forbidden"}, status_code=403)
    body = await request.json()
    history.update_note(record_id, str(body.get("note") or ""))
    return JSONResponse({"ok": True})


@router.delete("/api/records/{record_id}")
async def api_record_delete(request: Request, record_id: int):
    user = _current_user(request)
    if not user:
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
    rec = history.get_record(record_id)
    if not rec:
        return JSONResponse({"detail": "not found"}, status_code=404)
    if not history.can_access(rec, user["id"], user.get("role") == "admin"):
        return JSONResponse({"detail": "forbidden"}, status_code=403)
    history.delete_record(record_id)
    return JSONResponse({"ok": True})
