from __future__ import annotations

from .game import GameSession, CoopGameSession, PvpGameSession, PvpPlayerState


def _mode_text(mode: str) -> str:
    return "普通模式" if mode == "normal" else "无尽模式"


def _tower_short_name(tower_type: str) -> str:
    return {
        "弓箭": "A",
        "炮塔": "C",
        "冰塔": "I",
        "治疗塔": "H",
    }.get(tower_type, "T")


def build_path_summary_from_state(map_state, max_nodes: int = 10) -> str:
    if not map_state or not map_state.path:
        return "无"

    path = map_state.path
    shown = path[:max_nodes]
    text = " -> ".join(f"({r},{c})" for r, c in shown)
    if len(path) > max_nodes:
        text += f" -> ... 共 {len(path)} 个���点"
    return text


def build_path_summary(game: GameSession, max_nodes: int = 10) -> str:
    return build_path_summary_from_state(game.map_state, max_nodes=max_nodes)


def build_enemy_items(game: GameSession) -> list[dict]:
    alive = [e for e in game.enemies if e.alive]
    alive.sort(key=lambda x: (-x.path_index, x.hp))
    items = []
    for enemy in alive:
        r, c = game.enemy_coord(enemy)
        sub = f"路径点 {enemy.path_index} ｜ 坐标 ({r},{c}) ｜ 护甲 {enemy.armor} ｜ 速度 {enemy.speed}"
        if enemy.slow_turns > 0:
            sub += f" ｜ 减速 {enemy.slow_turns} 回合"
        items.append({
            "main": f"{enemy.name} · HP {max(0, enemy.hp)}/{enemy.max_hp}",
            "sub": sub,
        })
    return items


def build_tower_items(game: GameSession) -> list[dict]:
    items = []
    for key in sorted(game.towers.keys()):
        tower = game.towers[key]
        if tower.kind == "heal":
            main = f"({tower.row},{tower.col}) {tower.name} Lv{tower.level}"
            sub = f"标记 {_tower_short_name(tower.tower_type)} ｜ 治疗 {tower.heal_amount} ｜ 升级费用 {tower.upgrade_cost}"
        else:
            main = f"({tower.row},{tower.col}) {tower.name} Lv{tower.level}"
            sub = f"标记 {_tower_short_name(tower.tower_type)} ｜ ATK {tower.atk} ｜ 射程 {tower.range} ｜ 升级费用 {tower.upgrade_cost}"
        items.append({"main": main, "sub": sub})
    return items


def build_status_payload(game: GameSession, compact: bool = False) -> dict:
    alive_count = sum(1 for e in game.enemies if e.alive)
    front_enemy = None
    alive = [e for e in game.enemies if e.alive]
    if alive:
        alive.sort(key=lambda x: (-x.path_index, x.hp))
        front_enemy = alive[0]

    map_name = game.map_state.name if game.map_state else "未知"
    start = str(game.map_state.start()) if game.map_state else "-"
    end = str(game.map_state.end()) if game.map_state else "-"
    path_length = len(game.map_state.path) if game.map_state else 0
    path_summary = build_path_summary(game, max_nodes=10)
    buildable_summary = game.get_buildable_cells_text(limit=12)

    stats = [
        {"label": "模式", "value": _mode_text(game.mode)},
        {"label": "地图", "value": map_name},
        {"label": "波次 / 回合", "value": f"{game.wave} / {game.turn}"},
        {"label": "金币", "value": str(game.gold)},
        {"label": "生命", "value": f"{game.carrot_hp}/{game.max_carrot_hp}"},
    ]

    if compact:
        return {
            "title": "保卫萝卜 · 随机路径速览",
            "subtitle": f"状态：{game.status}",
            "badge": _mode_text(game.mode),
            "stats": stats,
            "sections": [
                {
                    "title": "地图摘要",
                    "kv": [
                        {"label": "地图名", "value": map_name},
                        {"label": "起点", "value": start},
                        {"label": "终点", "value": end},
                        {"label": "路径长度", "value": path_length},
                        {"label": "路径摘要", "value": path_summary},
                        {"label": "可建造格", "value": buildable_summary},
                    ],
                },
                {
                    "title": "战况速览",
                    "kv": [
                        {"label": "敌人剩余", "value": str(alive_count)},
                        {
                            "label": "最前敌人",
                            "value": (
                                f"{front_enemy.name} @ {game.enemy_coord(front_enemy)}"
                                if front_enemy else "当前无敌人"
                            ),
                        },
                        {"label": "累计击杀", "value": str(game.total_kills)},
                        {"label": "累计治疗", "value": str(game.total_heals)},
                    ],
                },
                {
                    "title": "塔概况",
                    "items": build_tower_items(game),
                    "empty_text": "当前没有防御塔",
                },
            ],
        }

    return {
        "title": "保卫萝卜 · 随机路径状态面板",
        "subtitle": f"状态：{game.status} ｜ 地图：{map_name} ｜ 累计击杀 {game.total_kills}",
        "badge": _mode_text(game.mode),
        "stats": stats + [
            {"label": "总赏金", "value": str(game.total_gold_earned)},
            {"label": "存活敌人", "value": str(alive_count)},
            {"label": "创建者", "value": str(game.created_by or '未知')},
            {"label": "更新时间", "value": str(game.updated_at or "-")},
        ],
        "sections": [
            {
                "title": "地图摘要",
                "kv": [
                    {"label": "地图名", "value": map_name},
                    {"label": "起点", "value": start},
                    {"label": "终点", "value": end},
                    {"label": "路径长度", "value": path_length},
                    {"label": "路径摘要", "value": path_summary},
                    {"label": "可建造格", "value": buildable_summary},
                ],
            },
            {
                "title": "敌人列表",
                "items": build_enemy_items(game),
                "empty_text": "当前没有敌人",
            },
            {
                "title": "防御塔",
                "items": build_tower_items(game),
                "empty_text": "当前没有防御塔",
            },
        ],
    }


def build_rank_payload(title: str, rankings: list[dict], kind: str = "player") -> dict:
    items = []

    if kind == "player":
        for idx, item in enumerate(rankings[:10], start=1):
            items.append({
                "no": idx,
                "main": f"{item['user_id']}",
                "sub": (
                    f"胜场 {item['wins']} ｜ 局数 {item['games']} ｜ 普通最高 {item['best_normal_wave']} ｜ "
                    f"无尽最高 {item['best_endless_wave']} ｜ 胜率 {item['win_rate']}% ｜ 击杀 {item['total_kills']}"
                ),
            })
    elif kind == "endless":
        for idx, item in enumerate(rankings[:10], start=1):
            items.append({
                "no": idx,
                "main": f"{item['user_id']}",
                "sub": (
                    f"无尽最高 {item['best_endless_wave']} 波 ｜ 最高生存回合 {item['best_turn_survived']} ｜ "
                    f"击杀 {item['total_kills']} ｜ 赏金 {item['total_gold_earned']}"
                ),
            })
    elif kind == "room":
        for idx, item in enumerate(rankings[:10], start=1):
            items.append({
                "no": idx,
                "main": f"{item['room_id']}",
                "sub": (
                    f"胜场 {item['wins']} ｜ 局数 {item['games']} ｜ 普通最高 {item['best_normal_wave']} ｜ "
                    f"无尽最高 {item['best_endless_wave']}"
                ),
            })

    return {
        "title": title,
        "subtitle": "排行榜前 10",
        "badge": "Ranking",
        "sections": [
            {
                "title": "榜单",
                "items": items,
                "empty_text": "暂无记录",
            }
        ],
    }


def build_player_stats_payload(user_id: str, stats: dict) -> dict:
    if not stats:
        return {
            "title": "我的战绩",
            "subtitle": f"玩家：{user_id}",
            "badge": "Stats",
            "sections": [
                {
                    "title": "个人记录",
                    "items": [],
                    "empty_text": "暂无记录",
                }
            ],
        }

    return {
        "title": "我的战绩",
        "subtitle": f"玩家：{user_id}",
        "badge": "Stats",
        "sections": [
            {
                "title": "基础数据",
                "kv": [
                    {"label": "总局数", "value": stats.get("games", 0)},
                    {"label": "胜场", "value": stats.get("wins", 0)},
                    {"label": "败场", "value": stats.get("losses", 0)},
                    {"label": "最高生存回合", "value": stats.get("best_turn_survived", 0)},
                    {"label": "普通最高波数", "value": stats.get("best_normal_wave", 0)},
                    {"label": "无尽最高波数", "value": stats.get("best_endless_wave", 0)},
                    {"label": "总击杀", "value": stats.get("total_kills", 0)},
                    {"label": "总赏金", "value": stats.get("total_gold_earned", 0)},
                    {"label": "总治疗量", "value": stats.get("total_heals", 0)},
                    {"label": "最近结果", "value": stats.get("last_result", "") or "-"},
                    {"label": "最后游玩", "value": stats.get("last_play_at", "") or "-"},
                    {"label": "胜率", "value": f"{stats.get('win_rate', 0)}%"},
                ],
            }
        ],
    }


def build_session_record_payload(game: GameSession) -> dict:
    map_name = game.map_state.name if game.map_state else "未知"
    start = str(game.map_state.start()) if game.map_state else "-"
    end = str(game.map_state.end()) if game.map_state else "-"
    path_length = len(game.map_state.path) if game.map_state else 0

    return {
        "title": "当前会话记录",
        "subtitle": f"创建者：{game.created_by or '未知'}",
        "badge": _mode_text(game.mode),
        "sections": [
            {
                "title": "记录",
                "kv": [
                    {"label": "状态", "value": game.status},
                    {"label": "地图", "value": map_name},
                    {"label": "起点", "value": start},
                    {"label": "终点", "value": end},
                    {"label": "路径长度", "value": path_length},
                    {"label": "波次", "value": game.wave},
                    {"label": "回合", "value": game.turn},
                    {"label": "萝卜生命", "value": f"{game.carrot_hp}/{game.max_carrot_hp}"},
                    {"label": "累计击杀", "value": game.total_kills},
                    {"label": "累计赏金", "value": game.total_gold_earned},
                    {"label": "累计治疗", "value": game.total_heals},
                    {"label": "更新时间", "value": game.updated_at or "-"},
                ],
            }
        ],
    }


def build_coop_room_payload(room: CoopGameSession) -> dict:
    items = []
    for uid, player in room.players.items():
        host_mark = "（房主）" if uid == room.host_user_id else ""
        items.append({
            "main": f"{player.nickname or uid}{host_mark}",
            "sub": f"金币 {player.gold} ｜ 建造 {player.build_count} ｜ 升级 {player.upgrade_count}",
        })

    map_name = room.map_state.name if room.map_state else "待开局"
    return {
        "title": "合作房间",
        "subtitle": f"状态：{room.status}",
        "badge": "Co-op",
        "sections": [
            {
                "title": "房间信息",
                "kv": [
                    {"label": "房主", "value": room.host_user_id or "未知"},
                    {"label": "人数", "value": f"{len(room.players)}/8"},
                    {"label": "状态", "value": room.status},
                    {"label": "地图", "value": map_name},
                ],
            },
            {"title": "成员列表", "items": items, "empty_text": "暂无成员"},
        ],
    }


def build_coop_enemy_items(room: CoopGameSession) -> list[dict]:
    alive = [e for e in room.enemies if e.alive]
    alive.sort(key=lambda x: (-x.path_index, x.hp))
    items = []
    for enemy in alive:
        r, c = room.enemy_coord(enemy)
        sub = f"路径点 {enemy.path_index} ｜ 坐标 ({r},{c}) ｜ 护甲 {enemy.armor} ｜ 速度 {enemy.speed}"
        if enemy.slow_turns > 0:
            sub += f" ｜ 减速 {enemy.slow_turns} 回合"
        items.append({"main": f"{enemy.name} · HP {max(0, enemy.hp)}/{enemy.max_hp}", "sub": sub})
    return items


def build_coop_tower_items(room: CoopGameSession) -> list[dict]:
    items = []
    for key in sorted(room.towers.keys()):
        tower = room.towers[key]
        owner = room.players.get(tower.owner_user_id)
        owner_name = owner.nickname or owner.user_id if owner else tower.owner_user_id
        if tower.kind == "heal":
            main = f"({tower.row},{tower.col}) {tower.name} Lv{tower.level}"
            sub = f"所属 {owner_name} ｜ 标记 {_tower_short_name(tower.tower_type)} ｜ 治疗 {tower.heal_amount} ｜ 升级费用 {tower.upgrade_cost}"
        else:
            main = f"({tower.row},{tower.col}) {tower.name} Lv{tower.level}"
            sub = f"所属 {owner_name} ｜ 标记 {_tower_short_name(tower.tower_type)} ｜ ATK {tower.atk} ｜ 射程 {tower.range} ｜ 升级费用 {tower.upgrade_cost}"
        items.append({"main": main, "sub": sub})
    return items


def build_coop_status_payload(room: CoopGameSession, compact: bool = False) -> dict:
    alive_count = sum(1 for e in room.enemies if e.alive)
    front_enemy = None
    alive = [e for e in room.enemies if e.alive]
    if alive:
        alive.sort(key=lambda x: (-x.path_index, x.hp))
        front_enemy = alive[0]

    player_items = []
    for uid, player in room.players.items():
        player_items.append({
            "main": f"{player.nickname or uid}",
            "sub": f"金币 {player.gold} ｜ 击杀 {player.kills_contributed} ｜ 治疗 {player.heal_contributed}",
        })

    map_name = room.map_state.name if room.map_state else "未知"
    start = str(room.map_state.start()) if room.map_state else "-"
    end = str(room.map_state.end()) if room.map_state else "-"
    path_length = len(room.map_state.path) if room.map_state else 0
    path_summary = build_path_summary_from_state(room.map_state, max_nodes=10)
    buildable_summary = room.get_buildable_cells_text(limit=12)

    stats = [
        {"label": "模式", "value": "合作模式"},
        {"label": "地图", "value": map_name},
        {"label": "波次 / 回合", "value": f"{room.wave} / {room.turn}"},
        {"label": "生命", "value": f"{room.carrot_hp}/{room.max_carrot_hp}"},
        {"label": "人数", "value": f"{len(room.players)}/8"},
    ]

    if compact:
        return {
            "title": "合作保卫萝卜 · 随机路径速览",
            "subtitle": f"状态：{room.status}",
            "badge": "Co-op",
            "stats": stats,
            "sections": [
                {
                    "title": "地图摘要",
                    "kv": [
                        {"label": "地图名", "value": map_name},
                        {"label": "起点", "value": start},
                        {"label": "终点", "value": end},
                        {"label": "路径长度", "value": path_length},
                        {"label": "路径摘要", "value": path_summary},
                        {"label": "可建造格", "value": buildable_summary},
                    ],
                },
                {
                    "title": "战况速览",
                    "kv": [
                        {"label": "敌人剩余", "value": str(alive_count)},
                        {
                            "label": "最前敌人",
                            "value": f"{front_enemy.name} @ {room.enemy_coord(front_enemy)}" if front_enemy else "当前无敌人",
                        },
                        {"label": "累计击杀", "value": str(room.total_kills)},
                        {"label": "累计治疗", "value": str(room.total_heals)},
                    ],
                },
                {"title": "玩家金币", "items": player_items, "empty_text": "暂无玩家"},
            ],
        }

    return {
        "title": "合作保卫萝卜 · 随机路径状态面板",
        "subtitle": f"状态：{room.status} ｜ 地图：{map_name} ｜ 累计击杀 {room.total_kills}",
        "badge": "Co-op",
        "stats": stats + [
            {"label": "总赏金", "value": str(room.total_gold_earned)},
            {"label": "存活敌人", "value": str(alive_count)},
            {"label": "房主", "value": room.host_user_id or "未知"},
            {"label": "更新时间", "value": room.updated_at or "-"},
        ],
        "sections": [
            {
                "title": "地图摘要",
                "kv": [
                    {"label": "地图名", "value": map_name},
                    {"label": "起点", "value": start},
                    {"label": "终点", "value": end},
                    {"label": "路径长度", "value": path_length},
                    {"label": "路径摘要", "value": path_summary},
                    {"label": "可建造格", "value": buildable_summary},
                ],
            },
            {"title": "玩家金币", "items": player_items, "empty_text": "暂无玩家"},
            {"title": "敌人列表", "items": build_coop_enemy_items(room), "empty_text": "当前没有敌人"},
            {"title": "防御塔", "items": build_coop_tower_items(room), "empty_text": "当前没有防御塔"},
        ],
    }


def build_coop_contribution_payload(room: CoopGameSession) -> dict:
    rows = room.get_contribution_rankings()
    items = []
    for idx, row in enumerate(rows, start=1):
        name = row["nickname"] or row["user_id"]
        items.append({
            "no": idx,
            "main": name,
            "sub": f"击杀 {row['kills_contributed']} ｜ 治疗 {row['heal_contributed']} ｜ 建造 {row['build_count']} ｜ 升级 {row['upgrade_count']} ｜ 花费 {row['gold_spent']} ｜ 赏金 {row['gold_earned']} ｜ 当前金币 {row['gold']}",
        })
    return {
        "title": "合作贡献榜",
        "subtitle": f"当前人数：{len(room.players)}",
        "badge": "Co-op",
        "sections": [{"title": "贡献排行", "items": items, "empty_text": "暂无贡献数据"}],
    }


def build_pvp_room_payload(room: PvpGameSession) -> dict:
    items = []
    for uid, player in room.players.items():
        host_mark = "（房主）" if uid == room.host_user_id else ""
        items.append({
            "main": f"{player.nickname or uid}{host_mark}",
            "sub": f"状态 {player.status} ｜ 波次 {player.wave} ｜ 金币 {player.gold}",
        })

    map_name = room.map_state.name if room.map_state else "待开局"
    return {
        "title": "PVP 房间",
        "subtitle": f"状态：{room.status}",
        "badge": "PVP",
        "sections": [
            {
                "title": "房间信息",
                "kv": [
                    {"label": "房主", "value": room.host_user_id or "未知"},
                    {"label": "人数", "value": f"{len(room.players)}/8"},
                    {"label": "状态", "value": room.status},
                    {"label": "共享地图", "value": map_name},
                ],
            },
            {"title": "成员列表", "items": items, "empty_text": "暂无成员"},
        ],
    }


def build_pvp_player_enemy_items(room: PvpGameSession, player: PvpPlayerState) -> list[dict]:
    alive = [e for e in player.enemies if e.alive]
    alive.sort(key=lambda x: (-x.path_index, x.hp))
    items = []
    for enemy in alive:
        r, c = room.enemy_coord(enemy)
        sub = f"路径点 {enemy.path_index} ｜ 坐标 ({r},{c}) ｜ 护甲 {enemy.armor} ｜ 速度 {enemy.speed}"
        if enemy.slow_turns > 0:
            sub += f" ｜ 减速 {enemy.slow_turns} 回合"
        items.append({"main": f"{enemy.name} · HP {max(0, enemy.hp)}/{enemy.max_hp}", "sub": sub})
    return items


def build_pvp_player_tower_items(player: PvpPlayerState) -> list[dict]:
    items = []
    for key in sorted(player.towers.keys()):
        tower = player.towers[key]
        if tower.kind == "heal":
            main = f"({tower.row},{tower.col}) {tower.name} Lv{tower.level}"
            sub = f"标记 {_tower_short_name(tower.tower_type)} ｜ 治疗 {tower.heal_amount} ｜ 升级费用 {tower.upgrade_cost}"
        else:
            main = f"({tower.row},{tower.col}) {tower.name} Lv{tower.level}"
            sub = f"标记 {_tower_short_name(tower.tower_type)} ｜ ATK {tower.atk} ｜ 射程 {tower.range} ｜ 升级费用 {tower.upgrade_cost}"
        items.append({"main": main, "sub": sub})
    return items


def build_pvp_my_state_payload(room: PvpGameSession, player: PvpPlayerState, compact: bool = False) -> dict:
    alive_count = sum(1 for e in player.enemies if e.alive)
    front_enemy = None
    alive = [e for e in player.enemies if e.alive]
    if alive:
        alive.sort(key=lambda x: (-x.path_index, x.hp))
        front_enemy = alive[0]

    map_name = room.map_state.name if room.map_state else "未知"
    start = str(room.map_state.start()) if room.map_state else "-"
    end = str(room.map_state.end()) if room.map_state else "-"
    path_length = len(room.map_state.path) if room.map_state else 0
    path_summary = build_path_summary_from_state(room.map_state, max_nodes=10)
    buildable_summary = room.get_buildable_cells_text(limit=12)

    stats = [
        {"label": "模式", "value": "PVP"},
        {"label": "共享地图", "value": map_name},
        {"label": "波次 / 回合", "value": f"{player.wave} / {player.turn}"},
        {"label": "金币", "value": str(player.gold)},
        {"label": "生命", "value": f"{player.carrot_hp}/{player.max_carrot_hp}"},
    ]

    if compact:
        return {
            "title": "PVP · 我的速览",
            "subtitle": f"玩家：{player.nickname or player.user_id} ｜ 状态：{player.status}",
            "badge": "PVP",
            "stats": stats,
            "sections": [
                {
                    "title": "地图摘要",
                    "kv": [
                        {"label": "地图名", "value": map_name},
                        {"label": "起点", "value": start},
                        {"label": "终点", "value": end},
                        {"label": "路径长度", "value": path_length},
                        {"label": "路径摘要", "value": path_summary},
                        {"label": "可建造格", "value": buildable_summary},
                    ],
                },
                {
                    "title": "战况速览",
                    "kv": [
                        {"label": "敌人剩余", "value": str(alive_count)},
                        {
                            "label": "最前敌人",
                            "value": f"{front_enemy.name} @ {room.enemy_coord(front_enemy)}" if front_enemy else "当前无敌人",
                        },
                        {"label": "累计击杀", "value": str(player.total_kills)},
                        {"label": "累计治疗", "value": str(player.total_heals)},
                    ],
                },
                {"title": "塔概况", "items": build_pvp_player_tower_items(player), "empty_text": "当前没有防御塔"},
            ],
        }

    return {
        "title": "PVP · 我的状态面板",
        "subtitle": f"玩家：{player.nickname or player.user_id} ｜ 状态：{player.status}",
        "badge": "PVP",
        "stats": stats + [
            {"label": "总赏金", "value": str(player.total_gold_earned)},
            {"label": "存活敌人", "value": str(alive_count)},
            {"label": "共享房主", "value": room.host_user_id or "未知"},
            {"label": "更新时间", "value": room.updated_at or "-"},
        ],
        "sections": [
            {
                "title": "地图摘要",
                "kv": [
                    {"label": "地图名", "value": map_name},
                    {"label": "起点", "value": start},
                    {"label": "终点", "value": end},
                    {"label": "路径长度", "value": path_length},
                    {"label": "路径摘要", "value": path_summary},
                    {"label": "可建造格", "value": buildable_summary},
                ],
            },
            {
                "title": "敌人列表",
                "items": build_pvp_player_enemy_items(room, player),
                "empty_text": "当前没有敌人",
            },
            {
                "title": "防御塔",
                "items": build_pvp_player_tower_items(player),
                "empty_text": "当前没有防御塔",
            },
        ],
    }


def build_pvp_status_payload(room: PvpGameSession) -> dict:
    items = []
    for idx, row in enumerate(room.get_rankings(), start=1):
        items.append({
            "no": idx,
            "main": f"{row['nickname'] or row['user_id']}",
            "sub": f"状态 {row['status']} ｜ 波次 {row['wave']} ｜ 回合 {row['turn']} ｜ 生命 {row['carrot_hp']} ｜ 击杀 {row['kills']} ｜ 金币 {row['gold']}",
        })

    map_name = room.map_state.name if room.map_state else "未知"
    start = str(room.map_state.start()) if room.map_state else "-"
    end = str(room.map_state.end()) if room.map_state else "-"
    path_length = len(room.map_state.path) if room.map_state else 0
    path_summary = build_path_summary_from_state(room.map_state, max_nodes=10)
    buildable_summary = room.get_buildable_cells_text(limit=12)

    return {
        "title": "PVP 总览",
        "subtitle": f"状态：{room.status}",
        "badge": "PVP",
        "sections": [
            {
                "title": "地图摘要",
                "kv": [
                    {"label": "地图名", "value": map_name},
                    {"label": "起点", "value": start},
                    {"label": "终点", "value": end},
                    {"label": "路径长度", "value": path_length},
                    {"label": "路径摘要", "value": path_summary},
                    {"label": "可建造格", "value": buildable_summary},
                ],
            },
            {
                "title": "玩家排行",
                "items": items,
                "empty_text": "暂无玩家",
            },
        ],
    }
