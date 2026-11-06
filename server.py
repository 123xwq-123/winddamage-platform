#!/usr/bin/env python3
"""
风电塔灾损测算软件 — Web 服务组装（FastAPI + Gradio 挂载）

职责：
  - 组装 FastAPI 应用：独立路由（/history/{id} 详情页等）+ Gradio 主应用挂载
  - 独立详情页服务端渲染（复用 ui_components 设计令牌与 app 的报告构建）
  - 后续认证中间件、登录/注册页在本文件扩展

启动：python server.py（等价于原 python app.py，端口 GRADIO_SERVER_PORT，默认 7860）
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import i18n
from i18n import t as tr, tr_value
import ui_components as uc
from history import get_record, can_access

# app.py 顶部会依据 --lang/UI_LANG 设置语言；导入其构建函数
import app as app_module


def _error_page(msg: str, status_code: int):
    from fastapi.responses import HTMLResponse
    body = uc.page_shell(tr("app_title"),
                         f'<div class="wd-page-head">{uc.empty_state(msg, "")}</div>')
    return HTMLResponse(body, status_code=status_code)


def create_app():
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, RedirectResponse
    import gradio as gr

    fastapp = FastAPI(title=tr("app_title"), docs_url=None, redoc_url=None)

    # ─── 独立详情页 /history/{id}（§9.2）────────────────────
    @fastapp.get("/history/{record_id}")
    def history_detail_page(record_id: int, request: Request):
        # 权限：登录用户仅本人记录；admin 全量（阶段3接入会话后强制）
        user_id, is_admin = app_module._current_scope()
        record = get_record(record_id)
        if not record:
            return _error_page(tr("msg_record_not_found", id=record_id), 404)
        if not can_access(record, user_id, is_admin):
            return _error_page(tr("msg_record_no_access"), 403)

        report = json.loads(record["json_report"])
        detail_html, _formatted = app_module._build_result_html(report, meta={
            "record_id": record["id"],
            "timestamp": record["timestamp"],
            "infer_time": record["infer_time"] or 0,
        })

        back = (f'<div class="wd-page-head">'
                f'<a class="wd-backlink" href="/">← {tr("tab_history")} / {tr("app_title")}</a>'
                f"</div>")
        body = f"{back}{detail_html}"
        return HTMLResponse(uc.page_shell(f'#{record_id} · {tr("app_title")}', body))

    # ─── Gradio 主应用挂载 ──────────────────────────────────
    demo = app_module.build_ui()
    gr.mount_gradio_app(
        fastapp, demo, path="/",
        theme=gr.themes.Soft(primary_hue="blue"),
        css=uc.BASE_CSS,
        show_error=True,
    )
    return fastapp


if __name__ == "__main__":
    import uvicorn
    from history import init_db

    init_db()
    port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    print("=" * 60)
    print(f"  {tr('app_title')}  [UI: {i18n.LANG}]  http://0.0.0.0:{port}")
    print("=" * 60)
    uvicorn.run(create_app(), host="0.0.0.0", port=port, log_level="info")
