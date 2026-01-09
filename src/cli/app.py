from __future__ import annotations

import asyncio
from typing import Literal

import solara

from src.api import deps
from src.models.entities import Message
from src.models.enums import Mode

ModeLiteral = Literal["chat", "prd_review", "trd_review", "tc_review"]


@solara.component
def Page() -> None:
    # 状态保持不变
    mode, set_mode = solara.use_state("chat")
    language, set_language = solara.use_state("中文")
    input_text, set_input_text = solara.use_state("")
    session_id, set_session_id = solara.use_state("")
    messages, set_messages = solara.use_state([])
    uploading, set_uploading = solara.use_state(False)
    document_id, set_document_id = solara.use_state("")
    reviewing, set_reviewing = solara.use_state(False)
    run_id, set_run_id = solara.use_state("")
    run_events, set_run_events = solara.use_state([])
    review_artifact_url, set_review_artifact_url = solara.use_state("")

    def on_mode_change(new_mode: ModeLiteral) -> None:
        # 保持原逻辑：切换模式时清理会话与评审状态
        set_mode(new_mode)
        set_session_id("")
        set_messages([])
        set_document_id("")
        set_run_id("")
        set_run_events([])
        set_review_artifact_url("")

    # 顶部区域：RA Chat 标题 + byline + GitHub 链接
    with solara.Column(gap="1rem", align="stretch"):
        with solara.Row(justify="space-between", style={"alignItems": "center"}):
            with solara.Column(gap="0.25rem"):
                # 主标题 / 品牌
                solara.Markdown("## RA Chat")
                # 副标题 / byline
                solara.Markdown("_by siry_")
            # 右侧 GitHub 链接（你可以替换为自己的仓库地址）
            solara.Markdown("[GitHub](https://github.com/)")

        # 中央主卡片，模仿 RA Chat 中央聊天卡片
        with solara.Card():
            with solara.Column(gap="1rem"):
                # 卡片顶部：对话标题 + 当前模式信息
                with solara.Row(justify="space-between", style={"alignItems": "center"}):
                    solara.Markdown("### 对话")
                    solara.Markdown(f"`模式: {mode}` · `{language}`")

                # 模式 / 语言选择行（与 RA Chat 的模式切换保持一致）
                with solara.Row():
                    solara.Select(
                        label="模式",
                        values=["chat", "prd_review", "trd_review", "tc_review"],
                        value=mode,
                        on_value=on_mode_change,
                    )
                    solara.Select(
                        label="语言",
                        values=["中文", "English"],
                        value=language,
                        on_value=set_language,
                    )

                # 模式对应的主体内容
                if mode == "chat":
                    _render_chat(
                        mode,
                        language,
                        input_text,
                        set_input_text,
                        session_id,
                        set_session_id,
                        messages,
                        set_messages,
                    )
                else:
                    _render_review_mode(
                        mode,
                        language,
                        input_text,
                        set_input_text,
                        session_id,
                        set_session_id,
                        document_id,
                        set_document_id,
                        uploading,
                        set_uploading,
                        reviewing,
                        set_reviewing,
                        run_id,
                        set_run_id,
                        run_events,
                        set_run_events,
                        review_artifact_url,
                        set_review_artifact_url,
                    )

        # 底部说明文字，类似 RA Chat 页脚提示
        solara.Markdown(
            "⚠️ _上传文件默认同意授权文档权限  ----------------- 文档保存一天后自动删除 _"
            "_----------------ICP备案号: 123456789012345678-----------------_"
        )


@solara.component
def _render_chat(
    mode: ModeLiteral,
    language: str,
    input_text: str,
    set_input_text,
    session_id: str,
    set_session_id,
    messages,
    set_messages,
) -> None:
    # 去掉原来的 “## 聊天模式” 标题，由外层卡片统一负责标题
    send_trigger, set_send_trigger = solara.use_state(0)
    pending_text, set_pending_text = solara.use_state("")
    error, set_error = solara.use_state("")

    async def _send() -> None:
        nonlocal session_id
        if send_trigger == 0:
            return
        if not pending_text.strip():
            return
        try:
            store = deps.get_session_store()
            if not session_id:
                session = store.create_session(mode=Mode.chat, language=language)
                set_session_id(session.id)
                session_id = session.id
            store.append_message(session_id, Message(role="user", content=pending_text))
            chat_service = deps.get_chat_service()
            updated = store.get_session(session_id)
            if not updated:
                raise ValueError("session not found")
            assistant = await chat_service.reply(updated.language, updated.messages)
            store.append_message(
                session_id, Message(role="assistant", content=assistant)
            )
            updated = store.get_session(session_id)
            if not updated:
                raise ValueError("session not found")
            set_messages([m.model_dump() for m in updated.messages])
            set_error("")
        except Exception as e:
            set_error(str(e))

    solara.tasks.use_task(_send, dependencies=[send_trigger])

    # 主体布局：上方是消息历史，底部是输入区，贴近 RA Chat 的结构
    with solara.Column(gap="0.75rem"):
        # 会话状态提示
        if not session_id:
            solara.Text("尚未创建会话，输入内容并点击发送开始聊天。")

        # 消息历史区域
        for m in messages:
            role = m.get("role", "user")
            prefix = "用户" if role == "user" else "助手"
            with solara.Card():
                solara.Markdown(f"**{prefix}:**\n\n{m.get('content','')}")

        def send_message() -> None:
            if not input_text.strip():
                return
            set_pending_text(input_text)
            set_input_text("")
            set_send_trigger(send_trigger + 1)

        # 输入区 + 发送按钮（视觉上在卡片底部，类似 RA Chat）
        solara.InputTextArea(
            label="输入",
            value=input_text,
            on_value=set_input_text,
            rows=4,
        )
        with solara.Row():
            solara.Button("发送", on_click=send_message)
            # 根据需要可以在这里补充一个“清空对话”按钮，逻辑保持自行管理 messages

        if error:
            solara.Error(error)


@solara.component
def _render_review_mode(
    mode: ModeLiteral,
    language: str,
    input_text: str,
    set_input_text,
    session_id: str,
    set_session_id,
    document_id: str,
    set_document_id,
    uploading: bool,
    set_uploading,
    reviewing: bool,
    set_reviewing,
    run_id: str,
    set_run_id,
    run_events,
    set_run_events,
    review_artifact_url: str,
    set_review_artifact_url,
) -> None:
    # 去掉原始 “## 评审模式” 标题，由外层卡片负责统一标题
    review_trigger, set_review_trigger = solara.use_state(0)
    cancel_trigger, set_cancel_trigger = solara.use_state(0)
    error, set_error = solara.use_state("")

    with solara.Column(gap="1rem"):
        solara.Markdown(
            "上传文档或直接粘贴文本，系统会进行评审并生成 Markdown 结果。"
        )

        def on_file(file_info) -> None:
            set_uploading(True)
            try:
                store = deps.get_file_store()
                if isinstance(file_info, list):
                    file_info = file_info[0] if file_info else {}

                if isinstance(file_info, dict):
                    file_obj = file_info.get("file_obj")
                    filename = str(file_info.get("name") or "")
                else:
                    file_obj = getattr(file_info, "file_obj", None)
                    filename = str(getattr(file_info, "name", ""))

                if not file_obj or not filename:
                    raise ValueError("invalid file")

                try:
                    file_obj.seek(0)
                except Exception:
                    pass

                import mimetypes

                content_type, _ = mimetypes.guess_type(filename)
                result = store.save_document(file_obj, filename, content_type)
                set_document_id(result.manifest.id)
                set_error("")
            finally:
                set_uploading(False)

        solara.FileDrop("拖拽文档到此处上传", on_file=on_file)
        if uploading:
            solara.Text("上传中...")
        if document_id:
            solara.Text(f"已上传文档: {document_id}")

        solara.InputTextArea(
            label="或直接输入待评审文本",
            value=input_text,
            on_value=set_input_text,
            rows=8,
        )

        async def _run_review() -> None:
            nonlocal session_id
            if review_trigger == 0:
                return
            run_store = deps.get_run_store()
            from src.models.events import EventType, RunEvent
            from src.models.run import RunStatus

            run_id_local: str | None = None

            async def emit(event_type: EventType, message: str) -> None:
                if not run_id_local:
                    return
                run_store.add_event(
                    RunEvent(run_id=run_id_local, type=event_type, message=message)
                )

            def should_cancel() -> bool:
                if not run_id_local:
                    return False
                item = run_store.get(run_id_local)
                return bool(item and item.run.status == RunStatus.canceled)

            try:
                store = deps.get_session_store()
                if not session_id:
                    session = store.create_session(mode=Mode(mode), language=language)
                    set_session_id(session.id)
                    session_id = session.id
                text = input_text.strip()
                doc_id = document_id or None
                run = run_store.create(
                    session_id=session_id, mode=Mode(mode), document_id=doc_id
                )
                run_id_local = run.id
                set_run_id(run.id)
                set_run_events([])
                set_reviewing(True)
                set_review_artifact_url("")

                await emit(EventType.info, "received")
                if not text:
                    if not doc_id:
                        raise ValueError("no document or text")
                    file_store = deps.get_file_store()
                    manifest = file_store.get_manifest("document", doc_id)
                    if not manifest:
                        raise ValueError("document not found")
                    from pathlib import Path

                    path = Path(manifest.path)
                    parsed = await deps.get_document_parser().parse(path)
                    text = parsed
                service = deps.get_review_service()
                result = await service.review(
                    mode=Mode(mode),
                    language=language,
                    document=text,
                    emit=emit,
                    should_cancel=should_cancel,
                )
                file_store = deps.get_file_store()
                artifact = file_store.save_review(
                    result,
                    f"{mode}.md",
                    session_id=session_id,
                    run_id=run.id,
                    source_document_id=doc_id,
                )
                run_store.set_artifact(run.id, artifact.manifest.id)
                if should_cancel():
                    run_store.set_status(run.id, RunStatus.canceled)
                    await emit(EventType.info, "canceled")
                    return
                run_store.set_status(run.id, RunStatus.succeeded)
                await emit(EventType.info, "succeeded")
                set_review_artifact_url(
                    f"/api/artifacts/{artifact.manifest.id}/download"
                )
                set_error("")
            except Exception as e:
                if run_id_local:
                    if str(e) == "canceled" or should_cancel():
                        run_store.set_status(run_id_local, RunStatus.canceled)
                        run_store.add_event(
                            RunEvent(
                                run_id=run_id_local,
                                type=EventType.info,
                                message="canceled",
                            )
                        )
                    else:
                        run_store.set_status(
                            run_id_local, RunStatus.failed, error=str(e)
                        )
                        run_store.add_event(
                            RunEvent(
                                run_id=run_id_local,
                                type=EventType.error,
                                message=str(e),
                            )
                        )
                set_error(str(e))
            finally:
                set_reviewing(False)

        solara.tasks.use_task(_run_review, dependencies=[review_trigger])

        async def _poll_events() -> None:
            if not run_id:
                return
            run_store = deps.get_run_store()
            from src.models.run import RunStatus

            while True:
                item = run_store.get(run_id)
                if not item:
                    break
                set_run_events([e.model_dump() for e in item.events])
                if item.run.status != RunStatus.running:
                    break
                await asyncio.sleep(0.5)

        solara.tasks.use_task(_poll_events, dependencies=[run_id])

        def start_review() -> None:
            if reviewing:
                return
            set_review_trigger(review_trigger + 1)

        def cancel_review() -> None:
            if not run_id:
                return
            run_store = deps.get_run_store()
            from src.models.events import EventType, RunEvent
            from src.models.run import RunStatus

            run_store.set_status(run_id, status=RunStatus.canceled)
            run_store.add_event(
                RunEvent(run_id=run_id, type=EventType.info, message="canceled")
            )
            set_cancel_trigger(cancel_trigger + 1)

        with solara.Row():
            solara.Button("开始评审", on_click=start_review, disabled=reviewing)
            solara.Button("中断", on_click=cancel_review, disabled=(not reviewing))

        if reviewing:
            solara.Text("评审中...")
        if run_events:
            with solara.Card():
                solara.Markdown(
                    "\n".join(
                        [f"- {e.get('type')}: {e.get('message')}" for e in run_events]
                    )
                )

        if review_artifact_url:
            solara.HTML(
                tag="a",
                unsafe_innerHTML="下载评审结果",
                attributes={
                    "href": review_artifact_url,
                    "target": "_blank",
                    "rel": "noopener noreferrer",
                },
            )
        if error:
            solara.Error(error)
