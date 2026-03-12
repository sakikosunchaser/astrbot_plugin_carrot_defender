from __future__ import annotations

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict

from astrbot.api.star import Context, Star, register
from astrbot.api.event import filter, AstrMessageEvent

from .game import GameManager
from .render import (
    render_help,
    render_player_rankings,
    render_endless_rankings,
    render_room_rankings,
    render_player_stats,
    render_session_record,
    render_status,
    render_status_compact,
)
from .storage import JsonStorage
from .utils import smart_compose, MAX_LOG_LINES, MAX_RANK_LINES, MAX_STATUS_LINES


@register("carrot_defender", "sakikosunchaser", "QQ文字版保卫萝卜小游戏", "0.3.1")
class CarrotDefenderPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.game_manager = GameManager()
        self.session_locks: Dict[str, asyncio.Lock] = {}

        base_dir = Path(__file__).resolve().parent
        self.storage = JsonStorage(base_dir)

        raw_sessions = self.storage.load_sessions()
        self.game_manager.load_sessions(raw_sessions)

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

    def _get_lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self.session_locks:
            self.session_locks[session_id] = asyncio.Lock()
        return self.session_locks[session_id]

    def _save_sessions(self):
        self.storage.save_sessions(self.game_manager.dump_sessions())

    def _touch_session(self, session_id: str):
        session = self.game_manager.get_session(session_id)
        if session:
            session.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    def _parse_position(self, raw_position) -> int | None:
        try:
            return int(str(raw_position).strip())
        except Exception:
            return None

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
            "建造命令格式：/萝卜建造 塔类型 位置\n"
            "示例：/萝卜建造 弓箭 2\n"
            "可用塔类型：弓箭 / 炮塔 / 冰塔 / 治疗塔"
        )

    async def _send_image_text(self, event: AstrMessageEvent, text: str, body_max_lines: int | None = None):
        if body_max_lines is not None:
            text = self._chunks(text, body_max_lines=body_max_lines)
            text = "\n\n".join(text)
        url = await self.text_to_image(text)
        return event.image_result(url)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜帮助")
    async def carrot_help(self, event: AstrMessageEvent):
        for chunk in self._chunks(render_help(), body_max_lines=24):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜开始")
    async def carrot_start(self, event: AstrMessageEvent):
        session_id = self._get_session_id(event)
        user_id = self._get_user_id(event)
        lock = self._get_lock(session_id)
        async with lock:
            session = self.game_manager.create_or_reset_session(session_id, created_by=user_id, mode="normal")
            self._touch_session(session_id)
            self._save_sessions()
            for chunk in smart_compose(header="", body=render_status_compact(session), body_max_lines=20):
                yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜无尽")
    async def carrot_endless(self, event: AstrMessageEvent):
        session_id = self._get_session_id(event)
        user_id = self._get_user_id(event)
        lock = self._get_lock(session_id)
        async with lock:
            session = self.game_manager.create_or_reset_session(session_id, created_by=user_id, mode="endless")
            self._touch_session(session_id)
            self._save_sessions()
            for chunk in smart_compose(header="", body=render_status_compact(session), body_max_lines=20):
                yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜状态")
    async def carrot_status(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始 或 /萝卜无尽")
            return
        for chunk in self._chunks(render_status(session), body_max_lines=MAX_STATUS_LINES):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜状态图")
    async def carrot_status_image(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始 或 /萝卜无尽")
            return
        yield await self._send_image_text(event, render_status(session), body_max_lines=MAX_STATUS_LINES)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜状态简洁")
    async def carrot_status_compact_cmd(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始 或 /萝卜无尽")
            return
        for chunk in self._chunks(render_status_compact(session), body_max_lines=20):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜速览")
    async def carrot_status_quick(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始 或 /萝卜无尽")
            return
        for chunk in self._chunks(render_status_compact(session), body_max_lines=20):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜速览图")
    async def carrot_status_quick_image(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始 或 /萝卜无尽")
            return
        yield await self._send_image_text(event, render_status_compact(session), body_max_lines=20)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜建造")
    async def carrot_build(self, event: AstrMessageEvent, tower_type=None, position=None):
        session_id = self._get_session_id(event)
        lock = self._get_lock(session_id)

        tower_type = self._normalize_tower_type(tower_type)
        pos = self._parse_position(position)

        if tower_type is None or pos is None:
            yield event.plain_result(self._build_usage())
            return

        async with lock:
            session = self.game_manager.get_session(session_id)
            if not session:
                yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始 或 /萝卜无尽")
                return

            ok, msg = session.build_tower(tower_type, pos)
            self._touch_session(session_id)
            self._save_sessions()

            if ok:
                chunks = smart_compose(
                    header="",
                    body=msg,
                    footer="\n" + render_status_compact(session),
                    body_max_lines=10,
                )
            else:
                chunks = self._chunks(msg, body_max_lines=10)

            for chunk in chunks:
                yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜升级")
    async def carrot_upgrade(self, event: AstrMessageEvent, position=None):
        session_id = self._get_session_id(event)
        lock = self._get_lock(session_id)
        pos = self._parse_position(position)
        if pos is None:
            yield event.plain_result("升级命令格式：/萝卜升级 位置\n示例：/萝卜升级 2")
            return

        async with lock:
            session = self.game_manager.get_session(session_id)
            if not session:
                yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始 或 /萝卜无尽")
                return

            ok, msg = session.upgrade_tower(pos)
            self._touch_session(session_id)
            self._save_sessions()

            if ok:
                chunks = smart_compose(
                    header="",
                    body=msg,
                    footer="\n" + render_status_compact(session),
                    body_max_lines=10,
                )
            else:
                chunks = self._chunks(msg, body_max_lines=10)

            for chunk in chunks:
                yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜拆除")
    async def carrot_remove(self, event: AstrMessageEvent, position=None):
        session_id = self._get_session_id(event)
        lock = self._get_lock(session_id)
        pos = self._parse_position(position)
        if pos is None:
            yield event.plain_result("拆除命令格式：/萝卜拆除 位置\n示例：/萝卜拆除 2")
            return

        async with lock:
            session = self.game_manager.get_session(session_id)
            if not session:
                yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始 或 /萝卜无尽")
                return

            ok, msg = session.remove_tower(pos)
            self._touch_session(session_id)
            self._save_sessions()

            if ok:
                chunks = smart_compose(
                    header="",
                    body=msg,
                    footer="\n" + render_status_compact(session),
                    body_max_lines=10,
                )
            else:
                chunks = self._chunks(msg, body_max_lines=10)

            for chunk in chunks:
                yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜下一回合")
    async def carrot_next_turn(self, event: AstrMessageEvent):
        session_id = self._get_session_id(event)
        lock = self._get_lock(session_id)
        async with lock:
            session = self.game_manager.get_session(session_id)
            if not session:
                yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始 或 /萝卜无尽")
                return

            ok, msg = session.step_turn()
            self._touch_session(session_id)
            self._record_if_game_over(event, session_id)
            self._save_sessions()

            if ok:
                chunks = smart_compose(
                    header="",
                    body=msg,
                    footer="\n" + render_status_compact(session),
                    body_max_lines=MAX_LOG_LINES,
                )
            else:
                chunks = self._chunks(msg, body_max_lines=10)

            for chunk in chunks:
                yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜下一波")
    async def carrot_next_wave(self, event: AstrMessageEvent):
        session_id = self._get_session_id(event)
        lock = self._get_lock(session_id)
        async with lock:
            session = self.game_manager.get_session(session_id)
            if not session:
                yield event.plain_result("当前没有进行中的游戏，请先使用 /萝卜开始 或 /萝卜无尽")
                return

            ok, msg = session.next_wave()
            self._touch_session(session_id)
            self._record_if_game_over(event, session_id)
            self._save_sessions()

            if ok:
                chunks = smart_compose(
                    header="",
                    body=msg,
                    footer="\n" + render_status_compact(session),
                    body_max_lines=10,
                )
            else:
                chunks = self._chunks(msg, body_max_lines=10)

            for chunk in chunks:
                yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜记录")
    async def carrot_record(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前会话没有进行中的游戏记录")
            return
        for chunk in self._chunks(render_session_record(session), body_max_lines=20):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜���录图")
    async def carrot_record_image(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前会话没有进行中的游戏记录")
            return
        yield await self._send_image_text(event, render_session_record(session), body_max_lines=20)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜排行")
    async def carrot_rank(self, event: AstrMessageEvent):
        rankings = self.storage.get_player_rankings()
        for chunk in self._chunks(render_player_rankings(rankings), body_max_lines=MAX_RANK_LINES):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜排行图")
    async def carrot_rank_image(self, event: AstrMessageEvent):
        rankings = self.storage.get_player_rankings()
        yield await self._send_image_text(event, render_player_rankings(rankings), body_max_lines=MAX_RANK_LINES)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜无尽排行")
    async def carrot_endless_rank(self, event: AstrMessageEvent):
        rankings = self.storage.get_endless_rankings()
        for chunk in self._chunks(render_endless_rankings(rankings), body_max_lines=MAX_RANK_LINES):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜无尽排行图")
    async def carrot_endless_rank_image(self, event: AstrMessageEvent):
        rankings = self.storage.get_endless_rankings()
        yield await self._send_image_text(event, render_endless_rankings(rankings), body_max_lines=MAX_RANK_LINES)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜群排行")
    async def carrot_room_rank(self, event: AstrMessageEvent):
        rankings = self.storage.get_room_rankings()
        for chunk in self._chunks(render_room_rankings(rankings), body_max_lines=MAX_RANK_LINES):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜群排行图")
    async def carrot_room_rank_image(self, event: AstrMessageEvent):
        rankings = self.storage.get_room_rankings()
        yield await self._send_image_text(event, render_room_rankings(rankings), body_max_lines=MAX_RANK_LINES)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜我的战绩")
    async def carrot_my_stats(self, event: AstrMessageEvent):
        user_id = self._get_user_id(event)
        stats = self.storage.get_player_stats(user_id)
        for chunk in self._chunks(render_player_stats(user_id, stats), body_max_lines=20):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜我的战绩图")
    async def carrot_my_stats_image(self, event: AstrMessageEvent):
        user_id = self._get_user_id(event)
        stats = self.storage.get_player_stats(user_id)
        yield await self._send_image_text(event, render_player_stats(user_id, stats), body_max_lines=20)

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
