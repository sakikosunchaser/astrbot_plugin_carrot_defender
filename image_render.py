from __future__ import annotations

from .game import GameSession


def _mode_text(mode: str) -> str:
    return "普通模式" if mode == "normal" else "无尽模式"


def _tower_short_name(tower_type: str) -> str:
    return {
        "弓箭": "A",
        "炮塔": "C",
        "冰塔": "I",
        "治疗塔": "H",
    }.get(tower_type, "T")


def build_path_summary(game: GameSession, max_nodes: int = 10) -> str:
    if not game.map_state or not game.map_state.path:
        return "无"

    path = game.map_state.path
    shown = path[:max_nodes]
    text = " -> ".join(f"({r},{c})" for r, c in shown)
    if len(path) > max_nodes:
        text += f" -> ... 共 {len(path)} 个节点"
    return text


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
