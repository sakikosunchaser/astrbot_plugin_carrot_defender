from __future__ import annotations

from game import GameSession, MAP_LENGTH, TOWER_TEMPLATES


def render_map(game: GameSession) -> str:
    parts = ["[起点]"]
    for pos in range(1, MAP_LENGTH + 1):
        tower = game.towers.get(pos)
        if tower:
            short_name = {
                "弓箭": "弓",
                "炮塔": "炮",
                "冰塔": "冰",
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
        lines.append(
            f"- {pos}号位 {tower.name} Lv{tower.level} | ATK {tower.atk} | 射程 {tower.range} | 升级费用 {tower.upgrade_cost}"
        )
    return "\n".join(lines)


def render_shop() -> str:
    lines = []
    for key, cfg in TOWER_TEMPLATES.items():
        lines.append(
            f"- {key}（{cfg['name']}）| 价格 {cfg['cost']} | 攻击 {cfg['base_atk']} | 射程 {cfg['range']}"
        )
    return "\n".join(lines)


def render_status(game: GameSession) -> str:
    return (
        f"【保卫萝卜文字版】\n"
        f"状态：{game.status}\n"
        f"波次：第 {game.wave} 波\n"
        f"回合：第 {game.turn} 回合\n"
        f"金币：{game.gold}\n"
        f"萝卜生命：{game.carrot_hp}/{game.max_carrot_hp}\n"
        f"累计击杀：{game.total_kills}\n"
        f"累计赏金：{game.total_gold_earned}\n\n"
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
        }.get(tower.tower_type, "塔")
        pieces.append(f"{pos}{short_name}Lv{tower.level}")

    return f"共 {tower_count} 座，平均等级 {avg_level} | " + "、".join(pieces)


def render_status_compact(game: GameSession) -> str:
    alive_count = _count_alive_enemies(game)
    front_enemy = _render_compact_enemy_summary(game)
    tower_summary = _render_compact_tower_summary(game)

    return (
        f"【保卫萝卜速览】\n"
        f"状态：{game.status}\n"
        f"第 {game.wave} 波 · 第 {game.turn} 回合\n"
        f"金币：{game.gold}\n"
        f"生命：{game.carrot_hp}/{game.max_carrot_hp}\n"
        f"击杀：{game.total_kills}\n"
        f"赏金：{game.total_gold_earned}\n\n"
        f"地图：\n{render_map(game)}\n\n"
        f"敌人剩余：{alive_count}\n"
        f"最前敌人：{front_enemy}\n\n"
        f"塔概况：\n{tower_summary}"
    )


def render_help() -> str:
    return (
        "【保卫萝卜文字版 指令帮助】\n"
        "/萝卜开始 - 开始新游戏\n"
        "/萝卜状态 - 查看当前完整状态\n"
        "/萝卜状态简洁 - 查看简洁状态\n"
        "/萝卜速览 - 查看简洁状态\n"
        "/萝卜建造 弓箭 2 - 在 2 号位建造弓箭塔\n"
        "/萝卜建造 炮塔 3 - 在 3 号位建造炮塔\n"
        "/萝卜建造 冰塔 4 - 在 4 号位建造冰塔\n"
        "/萝卜升级 2 - 升级 2 号位塔\n"
        "/萝卜拆除 2 - 拆除 2 号位塔\n"
        "/萝卜下一回合 - 推进一回合\n"
        "/萝卜下一波 - 进入下一波\n"
        "/萝卜排行 - 查看玩家排行榜\n"
        "/萝卜群排行 - 查看群战绩排行\n"
        "/萝卜记录 - 查看当前会话记录\n"
        "/萝卜结束 - 结束当前游戏\n"
        "/萝卜帮助 - 查看帮助"
    )


def render_player_rankings(rankings: list[dict], top_n: int = 10) -> str:
    if not rankings:
        return "暂无玩家战绩记录"

    lines = ["【玩家排行榜】"]
    for idx, item in enumerate(rankings[:top_n], start=1):
        lines.append(
            f"{idx}. {item['user_id']} | 胜场 {item['wins']} | 局数 {item['games']} | "
            f"最高波次 {item['best_wave']} | 胜率 {item['win_rate']}% | 击杀 {item['total_kills']}"
        )
    return "\n".join(lines)


def render_room_rankings(rankings: list[dict], top_n: int = 10) -> str:
    if not rankings:
        return "暂无群战绩记录"

    lines = ["【群排行榜】"]
    for idx, item in enumerate(rankings[:top_n], start=1):
        lines.append(
            f"{idx}. {item['room_id']} | 胜场 {item['wins']} | 局数 {item['games']} | 最高波次 {item['best_wave']}"
        )
    return "\n".join(lines)


def render_session_record(game: GameSession) -> str:
    return (
        "【当前会话记录】\n"
        f"创建者：{game.created_by or '未知'}\n"
        f"状态：{game.status}\n"
        f"当前波次：{game.wave}\n"
        f"当前回合：{game.turn}\n"
        f"累计击杀：{game.total_kills}\n"
        f"累计赏金：{game.total_gold_earned}\n"
        f"萝卜生命：{game.carrot_hp}/{game.max_carrot_hp}"
    )
