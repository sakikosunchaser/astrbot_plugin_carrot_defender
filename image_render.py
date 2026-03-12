from __future__ import annotations

from .game import GameSession, MAP_LENGTH


CARD_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>{{ title }}</title>
  <style>
    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      padding: 24px;
      width: 920px;
      background: linear-gradient(180deg, #f8fbff 0%, #eef5ff 100%);
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
      color: #1f2937;
    }

    .panel {
      background: #ffffff;
      border-radius: 24px;
      padding: 24px;
      box-shadow: 0 12px 40px rgba(58, 93, 170, 0.12);
      border: 1px solid rgba(125, 160, 255, 0.16);
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 18px;
    }

    .title-wrap h1 {
      margin: 0;
      font-size: 30px;
      color: #1d4ed8;
      line-height: 1.2;
    }

    .subtitle {
      margin-top: 8px;
      font-size: 15px;
      color: #6b7280;
    }

    .badge {
      display: inline-block;
      padding: 8px 14px;
      border-radius: 999px;
      background: #dbeafe;
      color: #1d4ed8;
      font-size: 14px;
      font-weight: 700;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin-top: 14px;
      margin-bottom: 20px;
    }

    .stat-card {
      background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
      border: 1px solid #dbeafe;
      border-radius: 18px;
      padding: 16px;
    }

    .stat-label {
      font-size: 13px;
      color: #6b7280;
      margin-bottom: 8px;
    }

    .stat-value {
      font-size: 28px;
      font-weight: 800;
      color: #111827;
      line-height: 1.2;
    }

    .section {
      margin-top: 18px;
    }

    .section-title {
      font-size: 18px;
      font-weight: 800;
      color: #1e40af;
      margin-bottom: 12px;
    }

    .map-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    .map-node {
      min-width: 82px;
      padding: 12px 10px;
      text-align: center;
      border-radius: 14px;
      background: #f3f6ff;
      border: 1px solid #dbeafe;
      font-size: 14px;
      font-weight: 700;
      color: #334155;
    }

    .map-node.special {
      background: #eff6ff;
      color: #1d4ed8;
    }

    .map-arrow {
      display: flex;
      align-items: center;
      color: #94a3b8;
      font-weight: 700;
      padding: 0 2px;
    }

    .list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .list-item {
      padding: 14px 16px;
      border-radius: 16px;
      background: #f8fbff;
      border: 1px solid #dbeafe;
    }

    .item-main {
      font-size: 15px;
      font-weight: 700;
      color: #111827;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .item-sub {
      margin-top: 6px;
      font-size: 13px;
      color: #6b7280;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .muted-box {
      padding: 16px;
      border-radius: 16px;
      background: #f9fafb;
      border: 1px dashed #cbd5e1;
      color: #6b7280;
      font-size: 14px;
    }

    .footer {
      margin-top: 22px;
      text-align: right;
      font-size: 12px;
      color: #94a3b8;
    }

    .rank-no {
      display: inline-block;
      min-width: 34px;
      text-align: center;
      padding: 6px 10px;
      border-radius: 999px;
      background: #dbeafe;
      color: #1d4ed8;
      font-weight: 800;
      margin-right: 10px;
    }

    .two-col {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 18px;
    }

    .kv-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }

    .kv {
      padding: 14px 16px;
      border-radius: 14px;
      background: #f8fbff;
      border: 1px solid #dbeafe;
    }

    .kv .k {
      font-size: 13px;
      color: #6b7280;
      margin-bottom: 6px;
    }

    .kv .v {
      font-size: 20px;
      color: #111827;
      font-weight: 800;
    }
  </style>
</head>
<body>
  <div class="panel">
    <div class="header">
      <div class="title-wrap">
        <h1>{{ title }}</h1>
        {% if subtitle %}
        <div class="subtitle">{{ subtitle }}</div>
        {% endif %}
      </div>
      {% if badge %}
      <div class="badge">{{ badge }}</div>
      {% endif %}
    </div>

    {% if stats %}
    <div class="stats-grid">
      {% for s in stats %}
      <div class="stat-card">
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-value">{{ s.value }}</div>
      </div>
      {% endfor %}
    </div>
    {% endif %}

    {% if map_nodes %}
    <div class="section">
      <div class="section-title">地图</div>
      <div class="map-row">
        {% for node in map_nodes %}
          <div class="map-node {% if node.special %}special{% endif %}">{{ node.text }}</div>
          {% if not loop.last %}
            <div class="map-arrow">→</div>
          {% endif %}
        {% endfor %}
      </div>
    </div>
    {% endif %}

    {% if two_col %}
    <div class="section">
      <div class="two-col">
        {% for col in two_col %}
        <div>
          <div class="section-title">{{ col.title }}</div>
          {% if col.items %}
          <div class="list">
            {% for item in col.items %}
            <div class="list-item">
              <div class="item-main">{{ item.main }}</div>
              {% if item.sub %}
              <div class="item-sub">{{ item.sub }}</div>
              {% endif %}
            </div>
            {% endfor %}
          </div>
          {% else %}
          <div class="muted-box">{{ col.empty_text or '暂无内容' }}</div>
          {% endif %}
        </div>
        {% endfor %}
      </div>
    </div>
    {% endif %}

    {% if sections %}
      {% for sec in sections %}
      <div class="section">
        <div class="section-title">{{ sec.title }}</div>
        {% if sec.kv %}
        <div class="kv-grid">
          {% for row in sec.kv %}
          <div class="kv">
            <div class="k">{{ row.label }}</div>
            <div class="v">{{ row.value }}</div>
          </div>
          {% endfor %}
        </div>
        {% elif sec.items %}
        <div class="list">
          {% for item in sec.items %}
          <div class="list-item">
            <div class="item-main">
              {% if item.no %}<span class="rank-no">{{ item.no }}</span>{% endif %}{{ item.main }}
            </div>
            {% if item.sub %}
            <div class="item-sub">{{ item.sub }}</div>
            {% endif %}
          </div>
          {% endfor %}
        </div>
        {% else %}
        <div class="muted-box">{{ sec.empty_text or '暂无内容' }}</div>
        {% endif %}
      </div>
      {% endfor %}
    {% endif %}

    <div class="footer">Generated by carrot_defender · HTML Render</div>
  </div>
</body>
</html>
"""


def _mode_text(mode: str) -> str:
    return "普通模式" if mode == "normal" else "无尽模式"


def _tower_short_name(tower_type: str) -> str:
    return {
        "弓箭": "弓",
        "炮塔": "炮",
        "冰塔": "冰",
        "治疗塔": "奶",
    }.get(tower_type, "塔")


def build_map_nodes(game: GameSession) -> list[dict]:
    nodes = [{"text": "起点", "special": True}]
    for pos in range(1, MAP_LENGTH + 1):
        tower = game.towers.get(pos)
        if tower:
            nodes.append({
                "text": f"{pos}号\n{_tower_short_name(tower.tower_type)}Lv{tower.level}",
                "special": False,
            })
        else:
            nodes.append({
                "text": f"{pos}号\n空位",
                "special": False,
            })
    nodes.append({"text": "🥕萝卜", "special": True})
    return nodes


def build_enemy_items(game: GameSession) -> list[dict]:
    alive = [e for e in game.enemies if e.alive]
    alive.sort(key=lambda x: (-x.pos, x.hp))
    items = []
    for enemy in alive:
        sub = f"位置 {enemy.pos} ｜ 护甲 {enemy.armor} ｜ 速度 {enemy.speed}"
        if enemy.slow_turns > 0:
            sub += f" ｜ 减速 {enemy.slow_turns} 回合"
        items.append({
            "main": f"{enemy.name} · HP {max(0, enemy.hp)}/{enemy.max_hp}",
            "sub": sub,
        })
    return items


def build_tower_items(game: GameSession) -> list[dict]:
    items = []
    for pos in sorted(game.towers.keys()):
        tower = game.towers[pos]
        if tower.kind == "heal":
            main = f"{pos}号位 {tower.name} Lv{tower.level}"
            sub = f"治疗 {tower.heal_amount} ｜ 升级费用 {tower.upgrade_cost}"
        else:
            main = f"{pos}号位 {tower.name} Lv{tower.level}"
            sub = f"ATK {tower.atk} ｜ 射程 {tower.range} ｜ 升级费用 {tower.upgrade_cost}"
        items.append({"main": main, "sub": sub})
    return items


def build_status_payload(game: GameSession, compact: bool = False) -> dict:
    alive_count = sum(1 for e in game.enemies if e.alive)
    front_enemy = None
    alive = [e for e in game.enemies if e.alive]
    if alive:
        alive.sort(key=lambda x: (-x.pos, x.hp))
        front_enemy = alive[0]

    stats = [
        {"label": "模式", "value": _mode_text(game.mode)},
        {"label": "波次 / 回合", "value": f"{game.wave} / {game.turn}"},
        {"label": "金币", "value": str(game.gold)},
        {"label": "生命", "value": f"{game.carrot_hp}/{game.max_carrot_hp}"},
    ]

    if compact:
        sections = [
            {
                "title": "战况速览",
                "kv": [
                    {"label": "敌人剩余", "value": str(alive_count)},
                    {
                        "label": "最前敌人",
                        "value": (
                            f"{front_enemy.name} @ {front_enemy.pos}"
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
        ]
        return {
            "title": "保卫萝卜 · 速览面板",
            "subtitle": f"状态：{game.status}",
            "badge": _mode_text(game.mode),
            "stats": stats,
            "map_nodes": build_map_nodes(game),
            "sections": sections,
        }

    return {
        "title": "保卫萝卜 · 状态面板",
        "subtitle": f"状态：{game.status} ｜ 累计击杀 {game.total_kills} ｜ 累计治疗 {game.total_heals}",
        "badge": _mode_text(game.mode),
        "stats": stats + [
            {"label": "总赏金", "value": str(game.total_gold_earned)},
            {"label": "存活敌人", "value": str(alive_count)},
            {"label": "创建者", "value": str(game.created_by or '未知')},
            {"label": "更新时间", "value": str(game.updated_at or '-')},
        ],
        "map_nodes": build_map_nodes(game),
        "two_col": [
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
    return {
        "title": "当前会话记录",
        "subtitle": f"创建者：{game.created_by or '未知'}",
        "badge": _mode_text(game.mode),
        "sections": [
            {
                "title": "记录",
                "kv": [
                    {"label": "状态", "value": game.status},
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
