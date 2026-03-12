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
    render_pvp_player_status,
    render_pvp_player_status_compact,
    render_pvp_rankings,
    render_pvp_overview,
)
from .storage import JsonStorage
from .utils import smart_compose, MAX_LOG_LINES, MAX_RANK_LINES, MAX_STATUS_LINES
from .image_render import (
    build_status_payload,
    build_rank_payload,
    build_player_stats_payload,
    build_session_record_payload,
    build_coop_room_payload,
    build_coop_status_payload,
    build_coop_contribution_payload,
    build_pvp_room_payload,
    build_pvp_player_payload,
    build_pvp_rank_payload,
    build_pvp_overview_payload,
)


@register("carrot_defender", "sakikosunchaser", "QQ文字版保卫萝卜小游戏", "0.5.0")
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

    def _coop_build_usage(self) -> str:
        return (
            "合作建造命令格式：/萝卜合作建造 塔类型 位置\n"
            "示例：/萝卜合作建造 弓箭 2\n"
            "可用塔类型：弓箭 / 炮塔 / 冰塔 / 治疗塔"
        )

    def _pvp_build_usage(self) -> str:
        return (
            "PVP 建造命令格式：/萝卜PVP建造 塔类型 位置\n"
            "示例：/萝卜PVP建造 弓箭 2\n"
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
            lines.append("【概览】")
            for item in stats:
                lines.append(f"{item.get('label', '')}：{item.get('value', '')}")

        map_nodes = payload.get("map_nodes", [])
        if map_nodes:
            lines.append("")
            lines.append("【地图】")
            lines.append(" -> ".join(str(x.get("text", "")) for x in map_nodes))

        sections = payload.get("sections", [])
        for sec in sections:
            lines.append("")
            lines.append(f"【{sec.get('title', '')}】")
            kv = sec.get("kv", [])
            if kv:
                for row in kv:
                    lines.append(f"{row.get('label', '')}：{row.get('value', '')}")
                continue
            items = sec.get("items", [])
            if items:
                for item in items:
                    prefix = f"{item.get('no')}. " if item.get("no") else "- "
                    lines.append(prefix + str(item.get("main", "")))
                    sub = str(item.get("sub", ""))
                    if sub:
                        lines.append(f"  {sub}")
            else:
                lines.append(sec.get("empty_text", "暂无内容"))

        return "\n".join(lines).strip()

    async def _render_panel_image(self, payload: dict) -> tuple[str, str]:
        plain_text = self._payload_to_plain_text(payload)
        try:
            url = await self.text_to_image(plain_text)
            return "image", url
        except Exception:
            return "text", plain_text

    async def _send_panel(self, event: AstrMessageEvent, payload: dict, body_max_lines: int | None = None):
        result_type, result_value = await self._render_panel_image(payload)
        if result_type == "image":
            yield event.image_result(result_value)
        else:
            for chunk in self._chunks(result_value, body_max_lines=body_max_lines):
                yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜帮助")
    async def carrot_help(self, event: AstrMessageEvent):
        for chunk in self._chunks(render_help(), body_max_lines=60):
            yield event.plain_result(chunk)

    # -------- 单人（保留图片优先） --------

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜开始")
    async def carrot_start(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        async with lock:
            session = self.game_manager.create_or_reset_session(sid, created_by=uid, mode="normal")
            self._touch_single_session(sid)
            self._save_sessions()
            payload = build_status_payload(session, compact=True)
            async for result in self._send_panel(event, payload, body_max_lines=20):
                yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜无尽")
    async def carrot_endless(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        async with lock:
            session = self.game_manager.create_or_reset_session(sid, created_by=uid, mode="endless")
            self._touch_single_session(sid)
            self._save_sessions()
            payload = build_status_payload(session, compact=True)
            async for result in self._send_panel(event, payload, body_max_lines=20):
                yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜状态")
    async def carrot_status(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的单人游戏，请先使用 /萝卜开始")
            return
        payload = build_status_payload(session, compact=False)
        async for result in self._send_panel(event, payload, body_max_lines=MAX_STATUS_LINES):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜速览")
    async def carrot_quick(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的单人游戏，请先使用 /萝卜开始")
            return
        payload = build_status_payload(session, compact=True)
        async for result in self._send_panel(event, payload, body_max_lines=20):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜状态文本")
    async def carrot_status_text(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前没有进行中的单人游戏，请先使用 /萝卜开始")
            return
        for chunk in self._chunks(render_status(session), body_max_lines=MAX_STATUS_LINES):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜建造")
    async def carrot_build(self, event: AstrMessageEvent, tower_type=None, position=None):
        sid = self._get_session_id(event)
        lock = self._get_lock(sid)
        tower_type = self._normalize_tower_type(tower_type)
        pos = self._parse_position(position)
        if tower_type is None or pos is None:
            yield event.plain_result(self._build_usage())
            return

        async with lock:
            session = self.game_manager.get_session(sid)
            if not session:
                yield event.plain_result("当前没有进行中的单人游戏，请先使用 /萝卜开始")
                return
            ok, msg = session.build_tower(tower_type, pos)
            self._touch_single_session(sid)
            self._save_sessions()
            if ok:
                payload = build_status_payload(session, compact=True)
                async for result in self._send_panel(event, payload, body_max_lines=20):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜升级")
    async def carrot_upgrade(self, event: AstrMessageEvent, position=None):
        sid = self._get_session_id(event)
        lock = self._get_lock(sid)
        pos = self._parse_position(position)
        if pos is None:
            yield event.plain_result("升级命令格式：/萝卜升级 位置\n示例：/萝卜升级 2")
            return
        async with lock:
            session = self.game_manager.get_session(sid)
            if not session:
                yield event.plain_result("当前没有进行中的单人游戏，请先使用 /萝卜开始")
                return
            ok, msg = session.upgrade_tower(pos)
            self._touch_single_session(sid)
            self._save_sessions()
            if ok:
                payload = build_status_payload(session, compact=True)
                async for result in self._send_panel(event, payload, body_max_lines=20):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜拆除")
    async def carrot_remove(self, event: AstrMessageEvent, position=None):
        sid = self._get_session_id(event)
        lock = self._get_lock(sid)
        pos = self._parse_position(position)
        if pos is None:
            yield event.plain_result("拆除命令格式：/萝卜拆除 位置\n示例：/萝卜拆除 2")
            return
        async with lock:
            session = self.game_manager.get_session(sid)
            if not session:
                yield event.plain_result("当前没有进行中的单人游戏，请先使用 /萝卜开始")
                return
            ok, msg = session.remove_tower(pos)
            self._touch_single_session(sid)
            self._save_sessions()
            if ok:
                payload = build_status_payload(session, compact=True)
                async for result in self._send_panel(event, payload, body_max_lines=20):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜下一回合")
    async def carrot_next_turn(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        lock = self._get_lock(sid)
        async with lock:
            session = self.game_manager.get_session(sid)
            if not session:
                yield event.plain_result("当前没有进行中的单人游戏，请先使用 /萝卜开始")
                return
            ok, msg = session.step_turn()
            self._touch_single_session(sid)
            self._record_if_game_over(event, sid)
            self._save_sessions()
            if ok:
                payload = build_status_payload(session, compact=False)
                async for result in self._send_panel(event, payload, body_max_lines=MAX_STATUS_LINES):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜下一波")
    async def carrot_next_wave(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        lock = self._get_lock(sid)
        async with lock:
            session = self.game_manager.get_session(sid)
            if not session:
                yield event.plain_result("当前没有进行中的单人游戏，请先使用 /萝卜开始")
                return
            ok, msg = session.next_wave()
            self._touch_single_session(sid)
            self._record_if_game_over(event, sid)
            self._save_sessions()
            if ok:
                payload = build_status_payload(session, compact=False)
                async for result in self._send_panel(event, payload, body_max_lines=MAX_STATUS_LINES):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜记录")
    async def carrot_record(self, event: AstrMessageEvent):
        session = self.game_manager.get_session(self._get_session_id(event))
        if not session:
            yield event.plain_result("当前会话没有进行中的单人游戏记录")
            return
        payload = build_session_record_payload(session)
        async for result in self._send_panel(event, payload, body_max_lines=20):
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
        uid = self._get_user_id(event)
        stats = self.storage.get_player_stats(uid)
        stats = dict(stats) if stats else {}
        if stats:
            games = int(stats.get("games", 0))
            wins = int(stats.get("wins", 0))
            stats["win_rate"] = round((wins / games * 100), 2) if games > 0 else 0.0
        payload = build_player_stats_payload(uid, stats)
        async for result in self._send_panel(event, payload, body_max_lines=20):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜结束")
    async def carrot_end(self, event: AstrMessageEvent):
        sid = self._get_session_id(event)
        lock = self._get_lock(sid)
        async with lock:
            session = self.game_manager.get_session(sid)
            if not session:
                yield event.plain_result("当前没有进行中的单人游戏")
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
            self.game_manager.end_session(sid)
            self._save_sessions()
            yield event.plain_result("当前单人游戏已结束，并已记录本局战绩")

    # -------- 合作（保留） --------

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
            async for result in self._send_panel(event, payload, body_max_lines=20):
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
                async for result in self._send_panel(event, payload, body_max_lines=20):
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
                async for result in self._send_panel(event, payload, body_max_lines=20):
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
        async for result in self._send_panel(event, payload, body_max_lines=20):
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
                async for result in self._send_panel(event, payload, body_max_lines=25):
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
        async for result in self._send_panel(event, payload, body_max_lines=25):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作建造")
    async def carrot_coop_build(self, event: AstrMessageEvent, tower_type=None, position=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        tower_type = self._normalize_tower_type(tower_type)
        pos = self._parse_position(position)
        if tower_type is None or pos is None:
            yield event.plain_result(self._coop_build_usage())
            return
        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
                return
            ok, msg = room.build_tower(uid, tower_type, pos)
            self._touch_coop_session(sid)
            self._save_sessions()
            if ok:
                payload = build_coop_status_payload(room, compact=True)
                async for result in self._send_panel(event, payload, body_max_lines=25):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作升级")
    async def carrot_coop_upgrade(self, event: AstrMessageEvent, position=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        pos = self._parse_position(position)
        if pos is None:
            yield event.plain_result("合作升级命令格式：/萝卜合作升级 位置\n示例：/萝卜合作升级 2")
            return
        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
                return
            ok, msg = room.upgrade_tower(uid, pos)
            self._touch_coop_session(sid)
            self._save_sessions()
            if ok:
                payload = build_coop_status_payload(room, compact=True)
                async for result in self._send_panel(event, payload, body_max_lines=25):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜合作拆除")
    async def carrot_coop_remove(self, event: AstrMessageEvent, position=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        pos = self._parse_position(position)
        if pos is None:
            yield event.plain_result("合作拆除命令格式：/萝卜合作拆除 位置\n示例：/萝卜合作拆除 2")
            return
        async with lock:
            room = self.coop_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有合作房间，请先使用 /萝卜合作创建")
                return
            ok, msg = room.remove_tower(uid, pos)
            self._touch_coop_session(sid)
            self._save_sessions()
            if ok:
                payload = build_coop_status_payload(room, compact=True)
                async for result in self._send_panel(event, payload, body_max_lines=25):
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
                async for result in self._send_panel(event, payload, body_max_lines=MAX_STATUS_LINES):
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
                async for result in self._send_panel(event, payload, body_max_lines=25):
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
        async for result in self._send_panel(event, payload, body_max_lines=25):
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

    # -------- PVP 新增 --------

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
            async for result in self._send_panel(event, payload, body_max_lines=20):
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
                async for result in self._send_panel(event, payload, body_max_lines=20):
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
                async for result in self._send_panel(event, payload, body_max_lines=20):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP房间")
    async def carrot_pvp_room(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        payload = build_pvp_room_payload(room)
        async for result in self._send_panel(event, payload, body_max_lines=20):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP房间文本")
    async def carrot_pvp_room_text(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        for chunk in self._chunks(render_pvp_room(room), body_max_lines=20):
            yield event.plain_result(chunk)

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
                payload = build_pvp_overview_payload(room)
                async for result in self._send_panel(event, payload, body_max_lines=25):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP我的状态")
    async def carrot_pvp_my_status(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        player = room.get_player(self._get_user_id(event))
        if not player:
            yield event.plain_result("你不在当前 PVP 房间中")
            return
        payload = build_pvp_player_payload(player, compact=False)
        async for result in self._send_panel(event, payload, body_max_lines=MAX_STATUS_LINES):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP速览")
    async def carrot_pvp_quick(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        payload = build_pvp_overview_payload(room)
        async for result in self._send_panel(event, payload, body_max_lines=25):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP状态")
    async def carrot_pvp_status(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        payload = build_pvp_rank_payload(room)
        async for result in self._send_panel(event, payload, body_max_lines=25):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP排行")
    async def carrot_pvp_rank(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        payload = build_pvp_rank_payload(room)
        async for result in self._send_panel(event, payload, body_max_lines=25):
            yield result

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP我的状态文本")
    async def carrot_pvp_my_status_text(self, event: AstrMessageEvent):
        room = self.pvp_game_manager.get_session(self._get_session_id(event))
        if not room:
            yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
            return
        player = room.get_player(self._get_user_id(event))
        if not player:
            yield event.plain_result("你不在当前 PVP 房间中")
            return
        for chunk in self._chunks(render_pvp_player_status(player), body_max_lines=MAX_STATUS_LINES):
            yield event.plain_result(chunk)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP建造")
    async def carrot_pvp_build(self, event: AstrMessageEvent, tower_type=None, position=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        tower_type = self._normalize_tower_type(tower_type)
        pos = self._parse_position(position)
        if tower_type is None or pos is None:
            yield event.plain_result(self._pvp_build_usage())
            return
        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
                return
            ok, msg = room.build_tower(uid, tower_type, pos)
            self._touch_pvp_session(sid)
            self._save_sessions()
            if ok:
                player = room.get_player(uid)
                if not player:
                    yield event.plain_result("未找到你的 PVP 状态")
                    return
                payload = build_pvp_player_payload(player, compact=True)
                async for result in self._send_panel(event, payload, body_max_lines=20):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP升级")
    async def carrot_pvp_upgrade(self, event: AstrMessageEvent, position=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        pos = self._parse_position(position)
        if pos is None:
            yield event.plain_result("PVP 升级命令格式：/萝卜PVP升级 位置\n示例：/萝卜PVP升级 2")
            return
        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
                return
            ok, msg = room.upgrade_tower(uid, pos)
            self._touch_pvp_session(sid)
            self._save_sessions()
            if ok:
                player = room.get_player(uid)
                if not player:
                    yield event.plain_result("未找到你的 PVP 状态")
                    return
                payload = build_pvp_player_payload(player, compact=True)
                async for result in self._send_panel(event, payload, body_max_lines=20):
                    yield result
            else:
                yield event.plain_result(msg)

    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    @filter.command("萝卜PVP拆除")
    async def carrot_pvp_remove(self, event: AstrMessageEvent, position=None):
        sid = self._get_session_id(event)
        uid = self._get_user_id(event)
        lock = self._get_lock(sid)
        pos = self._parse_position(position)
        if pos is None:
            yield event.plain_result("PVP 拆除命令格式：/萝卜PVP拆除 位置\n示例：/萝卜PVP拆除 2")
            return
        async with lock:
            room = self.pvp_game_manager.get_session(sid)
            if not room:
                yield event.plain_result("当前没有 PVP 房间，请先使用 /萝卜PVP创建")
                return
            ok, msg = room.remove_tower(uid, pos)
            self._touch_pvp_session(sid)
            self._save_sessions()
            if ok:
                player = room.get_player(uid)
                if not player:
                    yield event.plain_result("未找到你的 PVP 状态")
                    return
                payload = build_pvp_player_payload(player, compact=True)
                async for result in self._send_panel(event, payload, body_max_lines=20):
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
                payload = build_pvp_overview_payload(room)
                async for result in self._send_panel(event, payload, body_max_lines=25):
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
                payload = build_pvp_overview_payload(room)
                async for result in self._send_panel(event, payload, body_max_lines=25):
                    yield result
            else:
                yield event.plain_result(msg)

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
