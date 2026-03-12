from __future__ import annotations

from .game import GameSession, CoopGameSession, MAP_LENGTH, TOWER_TEMPLATES


def render_map(game: GameSession) -> str:
    parts = ["[起点]"]
    for pos in range(1, MAP_LENGTH + 1):
        tower = game.towers.get(pos)
        if tower:
            short_name = {
                "弓箭": "弓",
                "炮塔": "炮",
                "冰塔": "冰",
                "治疗塔": "奶",
            }.get(tower.tower_type, "塔")
            parts.append(f"[{pos}{short_name}Lv{tower.level}]")
        else:
            parts.append(f"[{pos}空]")
    parts.append("[🥕]")
    return " -> ".join(parts)


def render_enemies(game: GameSession) -> str:
    alive = [e for e in game.enemies if e.alive]
    if not alive:
        return "无"

    lines = []
    for enemy in sorted(alive, key=lambda x: (-x.pos, x.hp)):
        slow_text = f"，减速{enemy.slow_turns}回合" if enemy.slow_turns > 0 else ""
        lines.append(
            f"- {enemy.name} | HP {max(0, enemy.hp)}/{enemy.max_hp} | 位置 {enemy.pos} | 护甲 {enemy.armor}{slow_text}"
        )
    return "\n".join(lines)


def render_towers(game: GameSession) -> str:
    if not game.towers:
        return "无"

    lines = []
    for pos in sorted(game.towers.keys()):
        tower = game.towers[pos]
        if tower.kind == "heal":
            lines.append(
                f"- {pos}号位 {tower.name} Lv{tower.level} | 治疗 {tower.heal_amount} | 升级费用 {tower.upgrade_cost}"
            )
        else:
            lines.append(
                f"- {pos}号位 {tower.name} Lv{tower.level} | ATK {tower.atk} | 射程 {tower.range} | 升级费用 {tower.upgrade_cost}"
            )
    return "\n".join(lines)


def render_shop() -> str:
    lines = []
    for key, cfg in TOWER_TEMPLATES.items():
        if cfg["kind"] == "heal":
            lines.append(f"- {key}（{cfg['name']}）| 价格 {cfg['cost']} | 治疗塔")
        else:
            lines.append(
                f"- {key}（{cfg['name']}）| 价格 {cfg['cost']} | 攻击 {cfg['base_atk']} | 射程 {cfg['range']}"
            )
    return "\n".join(lines)


def render_status(game: GameSession) -> str:
    mode_text = "普通模式" if game.mode == "normal" else "无尽模式"
    return (
        f"【保卫萝卜】\n"
        f"模式：{mode_text}\n"
        f"状态：{game.status}\n"
        f"波次：第 {game.wave} 波\n"
        f"回合：第 {game.turn} 回合\n"
        f"金币：{game.gold}\n"
        f"萝卜生命：{game.carrot_hp}/{game.max_carrot_hp}\n"
        f"累计击杀：{game.total_kills}\n"
        f"累计赏金：{game.total_gold_earned}\n"
        f"累计治疗：{game.total_heals}\n\n"
        f"地图：\n{render_map(game)}\n\n"
        f"敌人：\n{render_enemies(game)}\n\n"
        f"防御塔：\n{render_towers(game)}\n\n"
        f"商店：\n{render_shop()}"
    )


def _get_front_enemy(game: GameSession):
    alive = [e for e in game.enemies if e.alive]
    if not alive:
        return None
    alive.sort(key=lambda x: (-x.pos, x.hp))
    return alive[0]


def _count_alive_enemies(game: GameSession) -> int:
    return sum(1 for e in game.enemies if e.alive)


def _render_compact_enemy_summary(game: GameSession) -> str:
    enemy = _get_front_enemy(game)
    if not enemy:
        return "当前无敌人"

    slow_text = f"，减速{enemy.slow_turns}回合" if enemy.slow_turns > 0 else ""
    return (
        f"{enemy.name} | HP {max(0, enemy.hp)}/{enemy.max_hp} | "
        f"位置 {enemy.pos} | 护甲 {enemy.armor}{slow_text}"
    )


def _render_compact_tower_summary(game: GameSession) -> str:
    if not game.towers:
        return "无防御塔"

    tower_count = len(game.towers)
    total_level = sum(t.level for t in game.towers.values())
    avg_level = round(total_level / tower_count, 1)

    pieces = []
    for pos in sorted(game.towers.keys()):
        tower = game.towers[pos]
        short_name = {
            "弓箭": "弓",
            "炮塔": "炮",
            "冰塔": "冰",
            "治疗塔": "奶",
        }.get(tower.tower_type, "塔")
        pieces.append(f"{pos}{short_name}Lv{tower.level}")

    return f"共 {tower_count} 座，平均等级 {avg_level} | " + "、".join(pieces)


def render_status_compact(game: GameSession) -> str:
    alive_count = _count_alive_enemies(game)
    front_enemy = _render_compact_enemy_summary(game)
    tower_summary = _render_compact_tower_summary(game)
    mode_text = "普通" if game.mode == "normal" else "无尽"

    return (
        f"【保卫萝卜速览】\n"
        f"模式：{mode_text}\n"
        f"状态：{game.status}\n"
        f"第 {game.wave} 波 · 第 {game.turn} 回合\n"
        f"金币：{game.gold}\n"
        f"生命：{game.carrot_hp}/{game.max_carrot_hp}\n"
        f"击杀：{game.total_kills}\n"
        f"治疗：{game.total_heals}\n\n"
        f"地图：\n{render_map(game)}\n\n"
        f"敌人剩余：{alive_count}\n"
        f"最前敌人：{front_enemy}\n\n"
        f"塔概况：\n{tower_summary}"
    )


def render_help() -> str:
    return (
        "【保卫萝卜文字版 指令帮助】\n"
        "—— 单人模式 ——\n"
        "/萝卜开始 - 开始普通模式\n"
        "/萝卜无尽 - 开始无尽模式\n"
        "/萝卜状态\n"
        "/萝卜速览\n"
        "/萝卜建造 弓箭 2\n"
        "/萝卜升级 2\n"
        "/萝卜拆除 2\n"
        "/萝卜下一回合\n"
        "/萝卜下一波\n"
        "/萝卜记录\n"
        "/萝卜排行\n"
        "/萝卜无尽排行\n"
        "/萝卜群排行\n"
        "/萝卜我的战绩\n"
        "/萝卜结束\n\n"
        "—— 合作模式 ——\n"
        "/萝卜合作创建\n"
        "/萝卜合作加入\n"
        "/萝卜合作退出\n"
        "/萝卜合作房间\n"
        "/萝卜合作开始\n"
        "/萝卜合作结束\n"
        "/萝卜合作状态\n"
        "/萝卜合作速览\n"
        "/萝卜合作建造 弓箭 2\n"
        "/萝卜合作升级 2\n"
        "/萝卜合作拆除 2\n"
        "/萝卜合作下一回合\n"
        "/萝卜合作下一波\n"
        "/萝卜合作贡献\n\n"
        "/萝卜帮助"
    )


def render_player_rankings(rankings: list[dict], top_n: int = 10) -> str:
    if not rankings:
        return "暂无玩家战绩记录"

    lines = ["【玩家排行榜】"]
    for idx, item in enumerate(rankings[:top_n], start=1):
        lines.append(
            f"{idx}. {item['user_id']} | 胜场 {item['wins']} | 局数 {item['games']} | "
            f"普通最高 {item['best_normal_wave']} | 无尽最高 {item['best_endless_wave']} | "
            f"胜率 {item['win_rate']}% | 击杀 {item['total_kills']}"
        )
    return "\n".join(lines)


def render_endless_rankings(rankings: list[dict], top_n: int = 10) -> str:
    if not rankings:
        return "暂无无尽模式战绩记录"

    lines = ["【无尽排行榜】"]
    for idx, item in enumerate(rankings[:top_n], start=1):
        lines.append(
            f"{idx}. {item['user_id']} | 无尽最高 {item['best_endless_wave']} 波 | "
            f"最高生存回合 {item['best_turn_survived']} | 击杀 {item['total_kills']}"
        )
    return "\n".join(lines)


def render_room_rankings(rankings: list[dict], top_n: int = 10) -> str:
    if not rankings:
        return "暂无群战绩记录"

    lines = ["【群排行榜】"]
    for idx, item in enumerate(rankings[:top_n], start=1):
        lines.append(
            f"{idx}. {item['room_id']} | 胜场 {item['wins']} | 局数 {item['games']} | "
            f"普通最高 {item['best_normal_wave']} | 无尽最高 {item['best_endless_wave']}"
        )
    return "\n".join(lines)


def render_session_record(game: GameSession) -> str:
    mode_text = "普通模式" if game.mode == "normal" else "无尽模式"
    return (
        "【当前会话记录】\n"
        f"创建者：{game.created_by or '未知'}\n"
        f"模式：{mode_text}\n"
        f"状态：{game.status}\n"
        f"当前波次：{game.wave}\n"
        f"当前回合：{game.turn}\n"
        f"累计击杀：{game.total_kills}\n"
        f"累计赏金：{game.total_gold_earned}\n"
        f"累计治疗：{game.total_heals}\n"
        f"萝卜生命：{game.carrot_hp}/{game.max_carrot_hp}"
    )


def render_player_stats(user_id: str, stats: dict) -> str:
    if not stats:
        return f"【我的战绩】\n玩家：{user_id}\n暂无记录"

    return (
        "【我的战绩】\n"
        f"玩家：{user_id}\n"
        f"总局数：{stats.get('games', 0)}\n"
        f"胜场：{stats.get('wins', 0)}\n"
        f"败场：{stats.get('losses', 0)}\n"
        f"普通模式最高波数：{stats.get('best_normal_wave', 0)}\n"
        f"无尽模式最高波数：{stats.get('best_endless_wave', 0)}\n"
        f"最高生存回合：{stats.get('best_turn_survived', 0)}\n"
        f"总击杀：{stats.get('total_kills', 0)}\n"
        f"总赏金：{stats.get('total_gold_earned', 0)}\n"
        f"总治疗量：{stats.get('total_heals', 0)}\n"
        f"最近结果：{stats.get('last_result', '')}\n"
        f"最后游玩：{stats.get('last_play_at', '')}"
    )


def render_coop_room(room: CoopGameSession) -> str:
    lines = [
        "【合作房间】",
        f"状态：{room.status}",
        f"房主：{room.host_user_id or '未知'}",
        f"人数：{len(room.players)}/8",
        "成员：",
    ]
    for player in room.players.values():
        name = player.nickname or player.user_id
        host_mark = "（房主）" if player.user_id == room.host_user_id else ""
        lines.append(f"- {name} {host_mark}".rstrip())
    return "\n".join(lines)


def render_coop_map(room: CoopGameSession) -> str:
    parts = ["[起点]"]
    for pos in range(1, MAP_LENGTH + 1):
        tower = room.towers.get(pos)
        if tower:
            short_name = {
                "弓箭": "弓",
                "炮塔": "炮",
                "冰塔": "冰",
                "治疗塔": "奶",
            }.get(tower.tower_type, "塔")
            owner_short = tower.owner_user_id[-4:] if tower.owner_user_id else "未知"
            parts.append(f"[{pos}{short_name}Lv{tower.level}/{owner_short}]")
        else:
            parts.append(f"[{pos}空]")
    parts.append("[🥕]")
    return " -> ".join(parts)


def render_coop_enemies(room: CoopGameSession) -> str:
    alive = [e for e in room.enemies if e.alive]
    if not alive:
        return "无"

    lines = []
    for enemy in sorted(alive, key=lambda x: (-x.pos, x.hp)):
        slow_text = f"，减速{enemy.slow_turns}回合" if enemy.slow_turns > 0 else ""
        lines.append(
            f"- {enemy.name} | HP {max(0, enemy.hp)}/{enemy.max_hp} | 位置 {enemy.pos} | 护甲 {enemy.armor}{slow_text}"
        )
    return "\n".join(lines)


def render_coop_players(room: CoopGameSession) -> str:
    lines = []
    for player in room.players.values():
        name = player.nickname or player.user_id
        lines.append(f"- {name} | 金币 {player.gold}")
    return "\n".join(lines) if lines else "无"


def render_coop_towers(room: CoopGameSession) -> str:
    if not room.towers:
        return "无"

    lines = []
    for pos in sorted(room.towers.keys()):
        tower = room.towers[pos]
        owner = room.players.get(tower.owner_user_id)
        owner_name = owner.nickname if owner and owner.nickname else tower.owner_user_id
        if tower.kind == "heal":
            lines.append(
                f"- {pos}号位 {tower.name} Lv{tower.level} | 治疗 {tower.heal_amount} | 所有者 {owner_name}"
            )
        else:
            lines.append(
                f"- {pos}号位 {tower.name} Lv{tower.level} | ATK {tower.atk} | 射程 {tower.range} | 所有者 {owner_name}"
            )
    return "\n".join(lines)


def render_coop_status(room: CoopGameSession) -> str:
    return (
        "【合作保卫萝卜】\n"
        f"状态：{room.status}\n"
        f"波次：第 {room.wave} 波\n"
        f"回合：第 {room.turn} 回合\n"
        f"萝卜生命：{room.carrot_hp}/{room.max_carrot_hp}\n"
        f"累计击杀：{room.total_kills}\n"
        f"累计赏金：{room.total_gold_earned}\n"
        f"累计治疗：{room.total_heals}\n\n"
        f"玩家金币：\n{render_coop_players(room)}\n\n"
        f"地图：\n{render_coop_map(room)}\n\n"
        f"敌人：\n{render_coop_enemies(room)}\n\n"
        f"防御塔：\n{render_coop_towers(room)}"
    )


def render_coop_status_compact(room: CoopGameSession) -> str:
    alive = [e for e in room.enemies if e.alive]
    front_enemy = "当前无敌人"
    if alive:
        alive.sort(key=lambda x: (-x.pos, x.hp))
        front = alive[0]
        front_enemy = f"{front.name} | HP {max(0, front.hp)}/{front.max_hp} | 位置 {front.pos}"

    lines = [
        "【合作速览】",
        f"状态：{room.status}",
        f"第 {room.wave} 波 · 第 {room.turn} 回合",
        f"生命：{room.carrot_hp}/{room.max_carrot_hp}",
        f"击杀：{room.total_kills}",
        f"治疗：{room.total_heals}",
        "",
        f"人数：{len(room.players)}/8",
        f"地图：\n{render_coop_map(room)}",
        "",
        f"敌人剩余：{sum(1 for e in room.enemies if e.alive)}",
        f"最前敌人：{front_enemy}",
        "",
        "玩家金币：",
        render_coop_players(room),
    ]
    return "\n".join(lines)


def render_coop_contributions(room: CoopGameSession) -> str:
    rows = room.get_contribution_rankings()
    if not rows:
        return "【合作贡献榜】\n暂无数据"

    lines = ["【合作贡献榜】"]
    for idx, row in enumerate(rows, start=1):
        name = row["nickname"] or row["user_id"]
        lines.append(
            f"{idx}. {name} | 击杀 {row['kills_contributed']} | 治疗 {row['heal_contributed']} | "
            f"建造 {row['build_count']} | 升级 {row['upgrade_count']} | "
            f"花费 {row['gold_spent']} | 赏金 {row['gold_earned']} | 当前金币 {row['gold']}"
        )
    return "\n".join(lines)
