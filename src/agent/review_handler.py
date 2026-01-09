from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage

from src.models.enums import Mode
from src.models.events import EventType
from src.models.provider import ChatModel
from src.prompt.registry import get_prompt_text


@dataclass(frozen=True)
class PlanItem:
    id: str
    title: str


@dataclass(frozen=True)
class ReviewService:
    model: ChatModel
    max_chars_per_chunk: int = 3000

    async def review(
        self,
        mode: Mode,
        language: str,
        document: str,
        emit: Callable[[EventType, str], Awaitable[None]] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> str:
        async def _noop_emit(_type: EventType, _message: str) -> None:
            return

        def _never_cancel() -> bool:
            return False

        emit_ = emit or _noop_emit
        should_cancel_ = should_cancel or _never_cancel
        prompt = get_prompt_text(mode)
        await emit_(EventType.info, "planning")
        plan = await self._plan(system_prompt=prompt, language=language, document=document)
        plan_by_id = {p.id: p for p in plan}
        completed: set[str] = set()
        for plan_item in plan:
            await emit_(EventType.todo, f"[pending] {plan_item.id} {plan_item.title}")
        if should_cancel_():
            raise ValueError("canceled")
        chunks = self._chunk(document)
        partials: list[str] = []
        for idx, chunk in enumerate(chunks):
            if should_cancel_():
                raise ValueError("canceled")
            await emit_(EventType.info, f"executing {idx + 1}/{len(chunks)}")
            covered_ids, markdown = await self._review_chunk(
                system_prompt=prompt,
                language=language,
                plan=plan,
                chunk=chunk,
                chunk_index=idx + 1,
                chunk_count=len(chunks),
            )
            partials.append(markdown)
            for cid in covered_ids:
                if cid in completed:
                    continue
                done_item = plan_by_id.get(cid)
                if not done_item:
                    continue
                completed.add(cid)
                await emit_(EventType.todo, f"[done] {done_item.id} {done_item.title}")
        if should_cancel_():
            raise ValueError("canceled")
        await emit_(EventType.info, "producing")
        return await self._finalize(
            system_prompt=prompt,
            language=language,
            plan=plan,
            completed=completed,
            partials=partials,
        )

    def _chunk(self, text: str) -> list[str]:
        if len(text) <= self.max_chars_per_chunk:
            return [text]
        parts = text.split("\n\n")
        out: list[str] = []
        buf: list[str] = []
        size = 0
        for part in parts:
            part_ = part
            if not part_:
                continue
            sep = "\n\n" if buf else ""
            new_size = size + len(sep) + len(part_)
            if new_size <= self.max_chars_per_chunk:
                buf.append(part_)
                size = new_size
                continue
            if buf:
                out.append("\n\n".join(buf))
                buf = []
                size = 0
            if len(part_) <= self.max_chars_per_chunk:
                buf.append(part_)
                size = len(part_)
                continue
            start = 0
            while start < len(part_):
                end = min(len(part_), start + self.max_chars_per_chunk)
                out.append(part_[start:end])
                start = end
        if buf:
            out.append("\n\n".join(buf))
        return out

    async def _plan(self, system_prompt: str, language: str, document: str) -> list[PlanItem]:
        system = SystemMessage(
            content=(
                f"{system_prompt}\n\n"
                "你现在的任务是先为后续评审生成一个计划列表。"
                "请根据输入文档，输出一个 JSON 数组。"
                "数组元素为对象：{\"id\":\"T1\",\"title\":\"...\"}。"
                "id 必须唯一且简短（如 T1/T2）。title 为简短评审待办。"
                "只输出 JSON，不要输出其它内容。"
            )
        )
        human = HumanMessage(content=f"Language: {language}\n\nDocument:\n{document[:6000]}")
        result = await self.model.ainvoke([system, human])
        content = getattr(result, "content", "")
        if not isinstance(content, str):
            content = str(content)
        try:
            data = json.loads(content)
            if isinstance(data, list):
                items: list[PlanItem] = []
                for idx, x in enumerate(data, start=1):
                    if isinstance(x, str):
                        items.append(PlanItem(id=f"T{idx}", title=x.strip()))
                        continue
                    if isinstance(x, dict):
                        rid = x.get("id")
                        title = x.get("title")
                        if isinstance(rid, str) and isinstance(title, str):
                            items.append(PlanItem(id=rid.strip(), title=title.strip()))
                items = [p for p in items if p.id and p.title]
                if items:
                    return items
        except Exception:
            pass
        lines = [ln.strip("- ") for ln in content.splitlines() if ln.strip()]
        return [PlanItem(id=f"T{i}", title=title) for i, title in enumerate(lines[:10], start=1)]

    async def _review_chunk(
        self,
        system_prompt: str,
        language: str,
        plan: list[PlanItem],
        chunk: str,
        chunk_index: int,
        chunk_count: int,
    ) -> tuple[list[str], str]:
        plan_text = "\n".join([f"- {p.id} {p.title}" for p in plan])
        system = SystemMessage(content=f"{system_prompt}\n\nLanguage: {language}")
        human = HumanMessage(
            content=(
                f"这是文档的一部分（{chunk_index}/{chunk_count}）。"
                "以下是整体评审待办列表，请重点围绕这些待办在当前片段中发现问题与建议。"
                "请只输出 JSON：{\"covered\":[\"T1\"],\"markdown\":\"...\"}。"
                "covered 为你在本片段中实际覆盖到的待办 id 列表。markdown 为本片段发现。\n\n"
                f"Todo:\n{plan_text}\n\n"
                f"Content:\n{chunk}"
            )
        )
        result = await self.model.ainvoke([system, human])
        content = getattr(result, "content", "")
        if not isinstance(content, str):
            return ([], str(result))
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                covered = data.get("covered")
                markdown = data.get("markdown")
                if isinstance(markdown, str):
                    if isinstance(covered, list):
                        covered_ids = [x for x in covered if isinstance(x, str)]
                    else:
                        covered_ids = []
                    return (covered_ids, markdown)
        except Exception:
            pass
        return ([], content)

    async def _finalize(
        self,
        system_prompt: str,
        language: str,
        plan: list[PlanItem],
        completed: set[str],
        partials: list[str],
    ) -> str:
        system = SystemMessage(content=f"{system_prompt}\n\nLanguage: {language}")
        plan_text = "\n".join(
            [
                f"- [{'x' if p.id in completed else ' '}] {p.id} {p.title}"
                for p in plan
            ]
        )
        findings = "\n\n".join(partials)
        human = HumanMessage(
            content=(
                "请基于评审待办和分段发现，输出最终的评审 Markdown。"
                "必须符合 system prompt 的要求。\n\n"
                f"Todo:\n{plan_text}\n\n"
                f"Findings:\n{findings}"
            )
        )
        result = await self.model.ainvoke([system, human])
        content = getattr(result, "content", "")
        if isinstance(content, str):
            return content
        return str(result)
