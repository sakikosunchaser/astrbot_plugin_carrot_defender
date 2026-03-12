from __future__ import annotations

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict

from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent

from .game import GameManager, CoopGameManager, PvpGameManager
from .render import (
    render_help,
    render_player_rankings,
    render_endless_rankings,
    render_room_rankings,
    render_player_stats,
    render_session_record,
    render_status,
    render_status_compact,
    render_coop_room,
    render_coop_status,
    render_coop_status_compact,
    render_coop_contributions,
    render_pvp_room,
    render_pvp_status,
    render_pvp_player_state,
    render_pvp_rankings,
)
from .storage import JsonStorage
from .utils import smart_compose, MAX_RANK_LINES, MAX_STATUS_LINES
from .image_render import (
    build_status_payload,
    build_rank_payload,
    build_player_stats_payload,
    build_session_record_payload,
    build_coop_room_payload,
    build_coop_status_payload,
    build_coop_contribution_payload,
    build_pvp_room_payload,
    build_pvp_status_payload,
    build_pvp_my_state_payload,
)


@register("carrot_defender", "sakikosunchaser", "随机路径版保卫萝卜文字小游戏", "0.8.0")
class CarrotDefenderPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.game_manager = GameManager()
        self.coop_game_manager = CoopGameManager()
        self.pvp_game_manager = PvpGameManager()
        self.session_locks: Dict[str, asyncio.Lock] = {}

        base_dir = Path(__file__).resolve().parent
        self.storage = JsonStorage(base_dir)

        self.game_manager.load_sessions(self.storage.load_sessions())
        self.coop_game_manager.load_sessions(self.storage.load_coop_sessions())
        self.pvp_game_manager.load_sessions(self.storage.load_pvp_sessions())

        self.render_mode = "image"

    def _get_session_id(self, event: AstrMessageEvent) -> str:
        try:
            group_id = event.get_group_id()
        except Exception:
            group_id = None

        try:
            sender_id = event.get_sender_id()
        except Exception:
            sender_id = None

        if group_id:
            return f"group_{group_id}"
        return f"user_{sender_id}"

    def _get_room_id(self, event: AstrMessageEvent) -> str:
        try:
            group_id = event.get_group_id()
            if group_id:
                return f"group_{group_id}"
        except Exception:
            pass

        try:
            sender_id = event.get_sender_id()
            return f"user_{sender_id}"
        except Exception:
            return "unknown"

    def _get_user_id(self, event: AstrMessageEvent) -> str:
        try:
            return str(event.get_sender_id())
        except Exception:
            return "unknown"

    def _get_user_name(self, event: AstrMessageEvent) -> str:
        try:
            sender = event.get_sender()
            if isinstance(sender, dict):
                return str(sender.get("nickname") or sender.get("card") or sender.get("user_id") or "")
        except Exception:
            pass
        return self._get_user_id(event)

    def _get_lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self.session_locks:
            self.session_locks[session_id] = asyncio.Lock()
        return self.session_locks[session_id]

    def _save_sessions(self):
        self.storage.save_sessions(self.game_manager.dump_sessions())
        self.storage.save_coop_sessions(self.coop_game_manager.dump_sessions())
        self.storage.save_pvp_sessions(self.pvp_game_manager.dump_sessions())

    def _touch_single_session(self, session_id: str):
        session = self.game_manager.get_session(session_id)
        if session:
            session.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _touch_coop_session(self, session_id: str):
        room = self.coop_game_manager.get_session(session_id)
        if room:
            room.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _touch_pvp_session(self, session_id: str):
        room = self.pvp_game_manager.get_session(session_id)
        if room:
            room.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _record_if_game_over(self, event: AstrMessageEvent, session_id: str):
        session = self.game_manager.get_session(session_id)
        if not session or session.status not in ("win", "lose"):
            return

        self.storage.record_result(
            user_id=self._get_user_id(event),
            room_id=self._get_room_id(event),
            result=session.status,
            mode=session.mode,
            wave=session.wave,
            turns=session.turn,
            kills=session.total_kills,
            gold_earned=session.total_gold_earned,
            heals=session.total_heals,
        )

    def _chunks(self, text: str, body_max_lines: int | None = None):
        return smart_compose(body=text, body_max_lines=body_max_lines, limit=1200)

    def _parse_coord(self, raw_row, raw_col) -> tuple[int | None, int | None]:
        try:
            row = int(str(raw_row).strip())
            col = int(str(raw_col).strip())
            return row, col
        except Exception:
            return None, None

    def _normalize_tower_type(self, raw_tower_type) -> str | None:
        if raw_tower_type is None:
            return None
        text = str(raw_tower_type).strip()
        mapping = {
            "弓": "弓箭",
            "弓箭": "弓箭",
            "弓箭塔": "弓箭",
            "箭塔": "弓箭",
            "炮": "炮塔",
            "炮塔": "炮塔",
            "大炮": "炮塔",
            "冰": "冰塔",
            "冰塔": "冰塔",
            "冰冻塔": "冰塔",
            "减速塔": "冰塔",
            "奶": "治疗塔",
            "奶塔": "治疗塔",
            "治疗": "治疗塔",
            "治疗塔": "治疗塔",
            "回复塔": "治疗塔",
        }
        return mapping.get(text)

    def _build_usage(self) -> str:
        return (
            "建造命令格式：/萝卜建造 塔类型 行 列\n"
            "示例：/萝卜建造 弓箭 2 3\n"
            "可用塔类型：弓箭 / 炮塔 / 冰塔 / 治疗塔\n"
            "注意：不能建在路径、起点、萝卜终点上"
        )

    def _coop_build_usage(self) -> str:
        return (
            "合作建造命令格式：/萝卜合作建造 塔类型 行 列\n"
            "示例：/萝卜合作建造 弓箭 2 3\n"
            "可用塔类型：弓箭 / 炮塔 / 冰塔 / 治疗塔"
        )

    def _pvp_build_usage(self) -> str:
        return (
            "PVP 建造命令格式：/萝卜PVP建造 塔类型 行 列\n"
            "示例：/萝卜PVP建造 弓箭 2 3\n"
            "可用塔类型：弓箭 / 炮塔 / 冰塔 / 治疗塔"
        )

    def _payload_to_plain_text(self, payload: dict) -> str:
        lines = []

        title = payload.get("title", "")
        subtitle = payload.get("subtitle", "")
        badge = payload.get("badge", "")

        if title:
            lines.append(str(title))
        if subtitle:
            lines.append(str(subtitle))
        if badge:
            lines.append(f"标签：{badge}")

        stats = payload.get("stats", [])
        if stats:
            lines.append("")
            lines.append("")
            for item in stats:
                lines.append(f"{item.get('label', '')}：{item.get('value', '')}")

        sections = payload.get("sections", [])
        for sec in sections:
            lines.append("")
            lines.append(f"")

            text_block = sec.get("text_block")
            if text_block:
                lines.append(str(text_block))
                continue

            kv = sec.get("kv", [])
            if kv:
                for row in kv:
                    lines.append(f"{row.get('label', '')}：{row.get('value', '')}")
                continue

            items = sec.get("items", [])
            if items:
                for item in items:
                    prefix = f"{item.get('no')}. " if item.get("no") else "- "
                    main = str(item.get("main", ""))
                    sub = str(item.get("sub", ""))
                    lines.append(prefix + main)
                    if sub:
                        lines.append(f"  {sub}")
            else:
                lines.append(sec.get("empty_text", "暂无内容"))

        return "\n".join(lines).strip()

    async def _try_text_to_image(self, text: str) -> tuple[bool, str]:
        try:
            url = await self.text_to_image(text)
            return True, url
        except Exception:
            return False, text

    async def _send_panel(self, event: AstrMessageEvent, payload: dict, body_max_lines: int | None = None):
        plain_text = self._payload_to_plain_text(payload)

        if self.render_mode == "image":
            ok, result = await self._try_text_to_image(plain_text)
            if ok:
                yield event.image_result(result)
                return

        for chunk in self._chunks(plain_text, body_max_lines=body_max_lines):
            yield event.plain_result(chunk)

    async def _send_text(self, event: AstrMessageEvent, text: str, body_max_lines: int | None = None):
        for chunk in self._chunks(text, body_max_lines=body_max_lines):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜帮助")
    async def carrot_help(self, event: AstrMessageEvent):
        help_text = render_help() + f"\n\n当前渲染模式：{self.render_mode}"
        async for result in self._send_text(event, help_text, body_max_lines=50):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜渲染")
    async def carrot_render_mode(self, event: AstrMessageEvent, mode=None):
        mode_text = str(mode).strip() if mode is not None else ""

        if mode_text in ("图片", "image", "img", "图"):
            self.render_mode = "image"
            yield event.plain_result("已切换为图片优先模式：先尝试 text_to_image，失败自动回退文本。")
            return

        if mode_text in ("文本", "text", "txt"):
            self.render_mode = "text"
            yield event.plain_result("已切换为纯文本模式：不再尝试图片渲染。")
            return

        yield event.plain_result(
            f"当前渲染模式：{self.render_mode}\n"
            "可用命令：\n"
            "/萝卜渲染 图片\n"
            "/萝卜渲染 文本"
        )

    # -------- 单人 --------

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜开始")
    async def carrot_start(self, event: AstrMessageEvent):
        session_id = self._get_session_id(event)
        user_id = self._get_user_id(event)
        lock = self._get_lock(session_id)

        async with lock:
            session = self.game_manager.create_or_reset_session(session_id, created_by=user_id, mode="normal")
            self._touch_single_session(session_id)
            self._save_sessions()

            payload = build_status_payload(session, compact=True)

            if self.render_mode == "image":
                plain_text = self._payload_to_plain_text(payload)
                plain_text += "\n\n提示：完整地图请使用：/萝卜状态文本"
                ok, result = await self._try_text_to_image(plain_text)
                if ok:
                    yield event.image_result(result)
                    return
                async for result in self._send_text(event, plain_text, body_max_lines=30):
                    yield result
                return

            async for result in self._send_panel(event, payload, body_max_lines=30):
                yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜无尽")
    async def carrot_endless(self, event: AstrMessageEvent):
        session_id = self._get_session_id(event)
        user_id = self._get_user_id(event)
        lock = self._get_lock(session_id)

        async with lock:
            session = self.game_manager.create_or_reset_session(session_id, created_by=user_id, mode="endless")
            self._touch_single_session(session_id)
            self._save_sessions()

            payload = build_status_payload(session, compact=True)

            if self.render_mode == "image":
                plain_text = self._payload_to_plain_text(payload)
                plain_text += "\n\n提示：完整地图请使用：/萝卜状态文本"
                ok, result = await self._try_text_to_image(plain_text)
                if ok:
                    yield event.image_result(result)
                    return
                async for result in self._send_text(event, plain_text, body_max_lines=30):
                    yield result
                return

            async for result in self._send_panel(event, payload, body_max_lines=30):
                yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜状态")
    async def carrot_status(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始")
            return

        payload = build_status_payload(session, compact=False)
        async for result in self._send_panel(event, payload, body_max_lines=MAX_STATUS_LINES):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜速览")
    async def carrot_status_quick(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始")
            return

        payload = build_status_payload(session, compact=True)

        if self.render_mode == "image":
            plain_text = self._payload_to_plain_text(payload)
            plain_text += "\n\n提示：完整地图请使用：/萝卜状态文本"
            ok, result = await self._try_text_to_image(plain_text)
            if ok:
                yield event.image_result(result)
                return

            async for chunk in self._send_text(event, plain_text, body_max_lines=30):
                yield chunk
            return

        async for result in self._send_panel(event, payload, body_max_lines=30):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜状态文本")
    async def carrot_status_text(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始")
            return

        async for result in self._send_text(event, render_status(session), body_max_lines=MAX_STATUS_LINES):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜速览文本")
    async def carrot_status_quick_text(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的��戏，请先使用 /萝卜开始")
            return

        async for result in self._send_text(event, render_status_compact(session), body_max_lines=30):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜建造")
    async def carrot_build(self, event: AstrMessageEvent, tower_type=None, row=None, col=None):
        session_id = self._get_session_id(event)
        lock = self._get_lock(session_id)

        tower_type = self._normalize_tower_type(tower_type)
        row, col = self._parse_coord(row, col)

        if tower_type is None or row is None or col is None:
            yield event.plain_result(self._build_usage())
            return

        async with lock:
            session = self.game_manager.get_session(session_id)
            if not session:
                yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始")
                return

            ok, msg = session.build_tower(tower_type, row, col)
            self._touch_single_session(session_id)
            self._save_sessions()

            if ok:
                payload = build_status_payload(session, compact=True)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"

                if self.render_mode == "image":
                    text += "\n\n提示：完整地图请使用：/萝卜状态文本"
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return

                async for result in self._send_text(event, text, body_max_lines=30):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜升级")
    async def carrot_upgrade(self, event: AstrMessageEvent, row=None, col=None):
        session_id = self._get_session_id(event)
        lock = self._get_lock(session_id)

        row, col = self._parse_coord(row, col)
        if row is None or col is None:
            yield event.plain_result("升级命令格式：/萝卜升级 行 列\n示例：/萝卜升级 2 3")
            return

        async with lock:
            session = self.game_manager.get_session(session_id)
            if not session:
                yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始")
                return

            ok, msg = session.upgrade_tower(row, col)
            self._touch_single_session(session_id)
            self._save_sessions()

            if ok:
                payload = build_status_payload(session, compact=True)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"

                if self.render_mode == "image":
                    text += "\n\n提示：完整地图请使用：/萝卜状态文本"
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return

                async for result in self._send_text(event, text, body_max_lines=30):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜拆除")
    async def carrot_remove(self, event: AstrMessageEvent, row=None, col=None):
        session_id = self._get_session_id(event)
        lock = self._get_lock(session_id)

        row, col = self._parse_coord(row, col)
        if row is None or col is None:
            yield event.plain_result("拆除命令格式：/萝卜拆除 行 列\n示例：/萝卜拆除 2 3")
            return

        async with lock:
            session = self.game_manager.get_session(session_id)
            if not session:
                yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始")
                return

            ok, msg = session.remove_tower(row, col)
            self._touch_single_session(session_id)
            self._save_sessions()

            if ok:
                payload = build_status_payload(session, compact=True)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"

                if self.render_mode == "image":
                    text += "\n\n提示：完整地图请使用：/萝卜状态文本"
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return

                async for result in self._send_text(event, text, body_max_lines=30):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜下一回合")
    async def carrot_next_turn(self, event: AstrMessageEvent):
        session_id = self._get_session_id(event)
        lock = self._get_lock(session_id)

        async with lock:
            session = self.game_manager.get_session(session_id)
            if not session:
                yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始")
                return

            ok, msg = session.step_turn()
            self._touch_single_session(session_id)
            self._record_if_game_over(event, session_id)
            self._save_sessions()

            if ok:
                payload = build_status_payload(session, compact=False)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"

                if self.render_mode == "image":
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return

                async for result in self._send_text(event, text, body_max_lines=MAX_STATUS_LINES):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜下一波")
    async def carrot_next_wave(self, event: AstrMessageEvent):
        session_id = self._get_session_id(event)
        lock = self._get_lock(session_id)

        async with lock:
            session = self.game_manager.get_session(session_id)
            if not session:
                yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始")
                return

            ok, msg = session.next_wave()
            self._touch_single_session(session_id)
            self._record_if_game_over(event, session_id)
            self._save_sessions()

            if ok:
                payload = build_status_payload(session, compact=False)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"

                if self.render_mode == "image":
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return

                async for result in self._send_text(event, text, body_max_lines=MAX_STATUS_LINES):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜记录")
    async def carrot_record(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前会话没有进行中的游戏记录")
            return

        payload = build_session_record_payload(session)
        async for result in self._send_panel(event, payload, body_max_lines=20):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜记录文本")
    async def carrot_record_text(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前会话没有进行中的游戏记录")
            return

        async for result in self._send_text(event, render_session_record(session), body_max_lines=20):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜排行")
    async def carrot_rank(self, event: AstrMessageEvent):
        rankings = self.storage.get_player_rankings()
        payload = build_rank_payload("玩家排行榜", rankings, kind="player")
        async for result in self._send_panel(event, payload, body_max_lines=MAX_RANK_LINES):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜无尽排行")
    async def carrot_endless_rank(self, event: AstrMessageEvent):
        rankings = self.storage.get_endless_rankings()
        payload = build_rank_payload("无尽排行榜", rankings, kind="endless")
        async for result in self._send_panel(event, payload, body_max_lines=MAX_RANK_LINES):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜群排行")
    async def carrot_room_rank(self, event: AstrMessageEvent):
        rankings = self.storage.get_room_rankings()
        payload = build_rank_payload("群排行榜", rankings, kind="room")
        async for result in self._send_panel(event, payload, body_max_lines=MAX_RANK_LINES):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜我的战绩")
    async def carrot_my_stats(self, event: AstrMessageEvent):
        user_id = self._get_user_id(event)
        stats = self.storage.get_player_stats(user_id)
        stats = dict(stats) if stats else {}
        if stats:
            games = int(stats.get("games", 0))
            wins = int(stats.get("wins", 0))
            stats["win_rate"] = round((wins / games * 100), 2) if games > 0 else 0.0

        payload = build_player_stats_payload(user_id, stats)
        async for result in self._send_panel(event, payload, body_max_lines=20):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜结束")
    async def carrot_end(self, event: AstrMessageEvent):
        session_id = self._get_session_id(event)
        lock = self._get_lock(session_id)

        async with lock:
            session = self.game_manager.get_session(session_id)
            if not session:
                yield event.plain_result("当前没有进行中的游戏")
                return

            self.storage.record_result(
                user_id=self._get_user_id(event),
                room_id=self._get_room_id(event),
                result="lose" if session.status == "running" else session.status,
                mode=session.mode,
                wave=session.wave,
                turns=session.turn,
                kills=session.total_kills,
                gold_earned=session.total_gold_earned,
                heals=session.total_heals,
            )

            self.game_manager.end_session(session_id)
            self._save_sessions()
            yield event.plain_result("当前游戏已结束，并已记录本局战绩")

    # -------- 合作 --------

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作创建")
    async def carrot_coop_create(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        name = self._get_user_name(event)
        lock = self._get_lock(sid)

        async with lock:
            ok, msg, room = self.coop_game_manager.create_room(sid, host_user_id=uid, nickname=name)
            self._touch_coop_session(sid)
            self._save_sessions()
            if not ok or room is None:
                yield event.plain_result(msg)
                return
            payload = build_coop_room_payload(room)
            async for result in self._send_panel(event, payload, body_max_lines=25):
                yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作加入")
    async def carrot_coop_join(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        name = self._get_user_name(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
                return
            ok, msg = room.add_player(uid, nickname=name)
            self._touch_coop_session(sid)
            self._save_sessions()
            if ok:
                payload = build_coop_room_payload(room)
                async for result in self._send_panel(event, payload, body_max_lines=25):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作退出")
    async def carrot_coop_leave(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间")
                return
            ok, msg = room.remove_player(uid)
            if ok and not room.players:
                self.coop_game_manager.remove_room(sid)
                self._save_sessions()
                yield event.plain_result("你已退出合作房间，房间已因无人而解散")
                return
            self._touch_coop_session(sid)
            self._save_sessions()
            if ok:
                payload = build_coop_room_payload(room)
                async for result in self._send_panel(event, payload, body_max_lines=25):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作房间")
    async def carrot_coop_room(self, event: AstrMessageEvent):
        room = self.coop_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
            return
        payload = build_coop_room_payload(room)
        async for result in self._send_panel(event, payload, body_max_lines=25):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作房间文本")
    async def carrot_coop_room_text(self, event: AstrMessageEvent):
        room = self.coop_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
            return
        async for result in self._send_text(event, render_coop_room(room), body_max_lines=25):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作开始")
    async def carrot_coop_start(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
                return
            ok, msg = room.start(uid)
            self._touch_coop_session(sid)
            self._save_sessions()
            if ok:
                payload = build_coop_status_payload(room, compact=True)
                if self.render_mode == "image":
                    plain_text = self._payload_to_plain_text(payload)
                    plain_text += "\n\n提示：完整共享地图请使用：/萝卜合作状态文本"
                    ok_img, result = await self._try_text_to_image(plain_text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                    async for result in self._send_text(event, plain_text, body_max_lines=35):
                        yield result
                    return
                async for result in self._send_panel(event, payload, body_max_lines=35):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作状态")
    async def carrot_coop_status(self, event: AstrMessageEvent):
        room = self.coop_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
            return
        payload = build_coop_status_payload(room, compact=False)
        async for result in self._send_panel(event, payload, body_max_lines=MAX_STATUS_LINES):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作速览")
    async def carrot_coop_quick(self, event: AstrMessageEvent):
        room = self.coop_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
            return
        payload = build_coop_status_payload(room, compact=True)

        if self.render_mode == "image":
            plain_text = self._payload_to_plain_text(payload)
            plain_text += "\n\n提示：完整共享地图请使用：/萝卜合作状态文本"
            ok_img, result = await self._try_text_to_image(plain_text)
            if ok_img:
                yield event.image_result(result)
                return
            async for result in self._send_text(event, plain_text, body_max_lines=35):
                yield result
            return

        async for result in self._send_panel(event, payload, body_max_lines=35):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作状态文本")
    async def carrot_coop_status_text(self, event: AstrMessageEvent):
        room = self.coop_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
            return
        async for result in self._send_text(event, render_coop_status(room), body_max_lines=MAX_STATUS_LINES):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作速览文本")
    async def carrot_coop_quick_text(self, event: AstrMessageEvent):
        room = self.coop_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
            return
        async for result in self._send_text(event, render_coop_status_compact(room), body_max_lines=35):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作建造")
    async def carrot_coop_build(self, event: AstrMessageEvent, tower_type=None, row=None, col=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        tower_type = self._normalize_tower_type(tower_type)
        row, col = self._parse_coord(row, col)
        if tower_type is None or row is None or col is None:
            yield event.plain_result(self._coop_build_usage())
            return

        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
                return
            ok, msg = room.build_tower(uid, tower_type, row, col)
            self._touch_coop_session(sid)
            self._save_sessions()
            if ok:
                payload = build_coop_status_payload(room, compact=True)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"
                if self.render_mode == "image":
                    text += "\n\n提示：完整共享地图请使用：/萝卜合作状态文本"
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                async for result in self._send_text(event, text, body_max_lines=35):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作升级")
    async def carrot_coop_upgrade(self, event: AstrMessageEvent, row=None, col=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        row, col = self._parse_coord(row, col)
        if row is None or col is None:
            yield event.plain_result("合作升级命令格式：/萝卜合作升级 行 列\n示例：/萝卜合作升级 2 3")
            return

        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
                return
            ok, msg = room.upgrade_tower(uid, row, col)
            self._touch_coop_session(sid)
            self._save_sessions()
            if ok:
                payload = build_coop_status_payload(room, compact=True)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"
                if self.render_mode == "image":
                    text += "\n\n提示：完整共享地图请使用：/萝卜合作状态文本"
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                async for result in self._send_text(event, text, body_max_lines=35):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作拆除")
    async def carrot_coop_remove(self, event: AstrMessageEvent, row=None, col=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        row, col = self._parse_coord(row, col)
        if row is None or col is None:
            yield event.plain_result("合作拆除命令格式：/萝卜合作拆除 行 列\n示例：/萝卜合作拆除 2 3")
            return

        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
                return
            ok, msg = room.remove_tower(uid, row, col)
            self._touch_coop_session(sid)
            self._save_sessions()
            if ok:
                payload = build_coop_status_payload(room, compact=True)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"
                if self.render_mode == "image":
                    text += "\n\n提示：完整共享地图请使用：/萝卜合作状态文本"
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                async for result in self._send_text(event, text, body_max_lines=35):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作下一回合")
    async def carrot_coop_next_turn(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
                return
            ok, msg = room.step_turn(uid)
            self._touch_coop_session(sid)
            self._save_sessions()
            if ok:
                payload = build_coop_status_payload(room, compact=False)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"
                if self.render_mode == "image":
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                async for result in self._send_text(event, text, body_max_lines=MAX_STATUS_LINES):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作下一波")
    async def carrot_coop_next_wave(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
                return
            ok, msg = room.next_wave(uid)
            self._touch_coop_session(sid)
            self._save_sessions()
            if ok:
                payload = build_coop_status_payload(room, compact=True)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"
                if self.render_mode == "image":
                    text += "\n\n提示：完整共享地图请使用：/萝卜合作状态文本"
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                async for result in self._send_text(event, text, body_max_lines=35):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作贡献")
    async def carrot_coop_contribution(self, event: AstrMessageEvent):
        room = self.coop_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
            return
        payload = build_coop_contribution_payload(room)
        async for result in self._send_panel(event, payload, body_max_lines=35):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作贡献文本")
    async def carrot_coop_contribution_text(self, event: AstrMessageEvent):
        room = self.coop_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
            return
        async for result in self._send_text(event, render_coop_contributions(room), body_max_lines=35):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作结束")
    async def carrot_coop_end(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间")
                return
            if uid != room.host_user_id:
                yield event.plain_result("只有房主可以结束合作房间")
                return
            self.coop_game_manager.remove_room(sid)
            self._save_sessions()
            yield event.plain_result("合作房间已结束并解散")

    # -------- PVP --------

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP创建")
    async def carrot_pvp_create(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        name = self._get_user_name(event)
        lock = self._get_lock(sid)

        async with lock:
            ok, msg, room = self.pvp_game_manager.create_room(sid, host_user_id=uid, nickname=name)
            self._touch_pvp_session(sid)
            self._save_sessions()
            if not ok or room is None:
                yield event.plain_result(msg)
                return
            payload = build_pvp_room_payload(room)
            async for result in self._send_panel(event, payload, body_max_lines=25):
                yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP加入")
    async def carrot_pvp_join(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        name = self._get_user_name(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
                return
            ok, msg = room.add_player(uid, nickname=name)
            self._touch_pvp_session(sid)
            self._save_sessions()
            if ok:
                payload = build_pvp_room_payload(room)
                async for result in self._send_panel(event, payload, body_max_lines=25):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP退出")
    async def carrot_pvp_leave(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间")
                return
            ok, msg = room.remove_player(uid)
            if ok and not room.players:
                self.pvp_game_manager.remove_room(sid)
                self._save_sessions()
                yield event.plain_result("你已退出 PVP 房间，房间已因无人而解散")
                return
            self._touch_pvp_session(sid)
            self._save_sessions()
            if ok:
                payload = build_pvp_room_payload(room)
                async for result in self._send_panel(event, payload, body_max_lines=25):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP房���")
    async def carrot_pvp_room(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        payload = build_pvp_room_payload(room)
        async for result in self._send_panel(event, payload, body_max_lines=25):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP房间文本")
    async def carrot_pvp_room_text(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        async for result in self._send_text(event, render_pvp_room(room), body_max_lines=25):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP开始")
    async def carrot_pvp_start(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
                return
            ok, msg = room.start(uid)
            self._touch_pvp_session(sid)
            self._save_sessions()
            if ok:
                payload = build_pvp_status_payload(room)
                if self.render_mode == "image":
                    plain_text = self._payload_to_plain_text(payload)
                    plain_text += "\n\n提示：查看个人完整地图请使用：/萝卜PVP我的状态文本"
                    ok_img, result = await self._try_text_to_image(plain_text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                    async for result in self._send_text(event, plain_text, body_max_lines=35):
                        yield result
                    return
                async for result in self._send_panel(event, payload, body_max_lines=35):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP状态")
    async def carrot_pvp_status(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        payload = build_pvp_status_payload(room)
        async for result in self._send_panel(event, payload, body_max_lines=35):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP状态文本")
    async def carrot_pvp_status_text(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        async for result in self._send_text(event, render_pvp_status(room), body_max_lines=35):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP速览")
    async def carrot_pvp_quick(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        uid = self._get_user_id(event)
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        player = room.get_player_state(uid)
        if not player:
            yield event.plain_result("你不在当前 PVP 房间中")
            return

        payload = build_pvp_my_state_payload(room, player, compact=True)
        if self.render_mode == "image":
            plain_text = self._payload_to_plain_text(payload)
            plain_text += "\n\n提示：完整地图请使用：/萝卜PVP我的状态文本"
            ok_img, result = await self._try_text_to_image(plain_text)
            if ok_img:
                yield event.image_result(result)
                return
            async for result in self._send_text(event, plain_text, body_max_lines=35):
                yield result
            return

        async for result in self._send_panel(event, payload, body_max_lines=35):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP我的状态")
    async def carrot_pvp_my_status(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        uid = self._get_user_id(event)
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        player = room.get_player_state(uid)
        if not player:
            yield event.plain_result("你不在当前 PVP 房间中")
            return

        payload = build_pvp_my_state_payload(room, player, compact=False)
        async for result in self._send_panel(event, payload, body_max_lines=MAX_STATUS_LINES):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP我的状态文本")
    async def carrot_pvp_my_status_text(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        uid = self._get_user_id(event)
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        player = room.get_player_state(uid)
        if not player:
            yield event.plain_result("你不在当前 PVP 房间中")
            return

        async for result in self._send_text(event, render_pvp_player_state(room, player), body_max_lines=MAX_STATUS_LINES):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP建造")
    async def carrot_pvp_build(self, event: AstrMessageEvent, tower_type=None, row=None, col=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)

        tower_type = self._normalize_tower_type(tower_type)
        row, col = self._parse_coord(row, col)
        if tower_type is None or row is None or col is None:
            yield event.plain_result(self._pvp_build_usage())
            return

        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
                return
            ok, msg = room.build_tower(uid, tower_type, row, col)
            self._touch_pvp_session(sid)
            self._save_sessions()
            if ok:
                player = room.get_player_state(uid)
                payload = build_pvp_my_state_payload(room, player, compact=True)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"
                if self.render_mode == "image":
                    text += "\n\n提示：完整地图请使用：/萝卜PVP我的状态文本"
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                async for result in self._send_text(event, text, body_max_lines=35):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP升级")
    async def carrot_pvp_upgrade(self, event: AstrMessageEvent, row=None, col=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        row, col = self._parse_coord(row, col)
        if row is None or col is None:
            yield event.plain_result("PVP 升级命令格式：/萝卜PVP升级 行 列\n示例：/萝卜PVP升级 2 3")
            return

        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
                return
            ok, msg = room.upgrade_tower(uid, row, col)
            self._touch_pvp_session(sid)
            self._save_sessions()
            if ok:
                player = room.get_player_state(uid)
                payload = build_pvp_my_state_payload(room, player, compact=True)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"
                if self.render_mode == "image":
                    text += "\n\n提示：完整地图请使用：/萝卜PVP我的状态文本"
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                async for result in self._send_text(event, text, body_max_lines=35):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP拆除")
    async def carrot_pvp_remove(self, event: AstrMessageEvent, row=None, col=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        row, col = self._parse_coord(row, col)
        if row is None or col is None:
            yield event.plain_result("PVP 拆除命令格式：/萝卜PVP拆除 行 列\n示例：/萝卜PVP拆除 2 3")
            return

        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
                return
            ok, msg = room.remove_tower(uid, row, col)
            self._touch_pvp_session(sid)
            self._save_sessions()
            if ok:
                player = room.get_player_state(uid)
                payload = build_pvp_my_state_payload(room, player, compact=True)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"
                if self.render_mode == "image":
                    text += "\n\n提示：完整地图请使用：/萝卜PVP我的状态文本"
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                async for result in self._send_text(event, text, body_max_lines=35):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP下一回合")
    async def carrot_pvp_next_turn(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
                return
            ok, msg = room.step_turn(uid)
            self._touch_pvp_session(sid)
            self._save_sessions()
            if ok:
                payload = build_pvp_status_payload(room)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"
                if self.render_mode == "image":
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                async for result in self._send_text(event, text, body_max_lines=MAX_STATUS_LINES):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP下一波")
    async def carrot_pvp_next_wave(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
                return
            ok, msg = room.next_wave(uid)
            self._touch_pvp_session(sid)
            self._save_sessions()
            if ok:
                payload = build_pvp_status_payload(room)
                text = f"\n{msg}\n\n{self._payload_to_plain_text(payload)}"
                if self.render_mode == "image":
                    ok_img, result = await self._try_text_to_image(text)
                    if ok_img:
                        yield event.image_result(result)
                        return
                async for result in self._send_text(event, text, body_max_lines=MAX_STATUS_LINES):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP排行")
    async def carrot_pvp_rank(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        payload = build_pvp_status_payload(room)
        async for result in self._send_panel(event, payload, body_max_lines=35):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP排行文本")
    async def carrot_pvp_rank_text(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        async for result in self._send_text(event, render_pvp_rankings(room), body_max_lines=35):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP结束")
    async def carrot_pvp_end(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)

        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间")
                return
            if uid != room.host_user_id:
                yield event.plain_result("只有房主可以结束 PVP 房间")
                return
            self.pvp_game_manager.remove_room(sid)
            self._save_sessions()
            yield event.plain_result("PVP 房间已结束并解散")
