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
@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return _page("<h1>screen home placeholder</h1>")


@router.get("/batch", response_class=HTMLResponse)
async def batch_page(request: Request):
    return _page("<h1>screen batch placeholder</h1>")


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return _page("<h1>screen history placeholder</h1>")


@router.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):
    return _page("<h1>screen account placeholder</h1>")


# ─── JSON API ─────────────────────────────────────────────────
@router.get("/api/me")
async def api_me(request: Request):
    user = _current_user(request)
    if not user:
        return JSONResponse({"username": None, "role": None})
    return JSONResponse({"username": user["username"], "role": user.get("role")})


@router.get("/api/overview")
async def api_overview(request: Request):
    return JSONResponse({"detail": "not implemented"}, status_code=501)


@router.post("/api/analyze")
async def api_analyze(request: Request):
    return JSONResponse({"detail": "not implemented"}, status_code=501)


@router.get("/api/records")
async def api_records(request: Request):
    return JSONResponse({"detail": "not implemented"}, status_code=501)
