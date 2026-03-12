from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
import random


GRID_ROWS = 5
GRID_COLS = 5
MAX_WAVE = 5
COOP_MIN_PLAYERS = 2
COOP_MAX_PLAYERS = 8
PVP_MIN_PLAYERS = 2
PVP_MAX_PLAYERS = 8

TOWER_TEMPLATES = {
    "弓箭": {
        "name": "弓箭塔",
        "cost": 50,
        "base_atk": 18,
        "range": 2,
        "upgrade_cost": 35,
        "kind": "single",
    },
    "炮塔": {
        "name": "炮塔",
        "cost": 80,
        "base_atk": 28,
        "range": 2,
        "upgrade_cost": 50,
        "kind": "splash",
    },
    "冰塔": {
        "name": "冰塔",
        "cost": 70,
        "base_atk": 10,
        "range": 2,
        "upgrade_cost": 45,
        "kind": "slow",
    },
    "治疗塔": {
        "name": "治疗塔",
        "cost": 90,
        "base_atk": 0,
        "range": 0,
        "upgrade_cost": 55,
        "kind": "heal",
    },
}

ENEMY_ARCHETYPES = [
    {"name": "小史莱姆", "hp": 40, "speed": 1, "reward": 18, "armor": 0},
    {"name": "小狗", "hp": 55, "speed": 1, "reward": 22, "armor": 2},
    {"name": "飞贼", "hp": 35, "speed": 2, "reward": 25, "armor": 0},
    {"name": "铁甲怪", "hp": 85, "speed": 1, "reward": 35, "armor": 5},
]

MAP_TEMPLATES: List[dict] = [
    {
        "name": "直角长廊",
        "path": [(0, 0), (1, 0), (1, 1), (1, 2), (2, 2), (3, 2), (3, 3), (3, 4), (4, 4)],
    },
    {
        "name": "Z字折线",
        "path": [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2), (2, 1), (2, 0), (3, 0), (4, 0), (4, 1), (4, 2), (4, 3), (4, 4)],
    },
    {
        "name": "蛇形小道",
        "path": [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (0, 3), (0, 4), (1, 4), (2, 4), (3, 4), (4, 4)],
    },
    {
        "name": "中路回折",
        "path": [(0, 0), (1, 0), (1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (3, 2), (3, 1), (4, 1), (4, 2), (4, 3), (4, 4)],
    },
    {
        "name": "上路突进",
        "path": [(0, 0), (0, 1), (0, 2), (1, 2), (2, 2), (2, 3), (2, 4), (3, 4), (4, 4)],
    },
    {
        "name": "双弯回廊",
        "path": [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (3, 2), (4, 2), (4, 3), (4, 4)],
    },
]


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def in_bounds(row: int, col: int) -> bool:
    return 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS


@dataclass
class Enemy:
    uid: str
    name: str
    hp: int
    max_hp: int
    speed: int
    reward: int
    armor: int = 0
    path_index: int = 0
    slow_turns: int = 0
    alive: bool = True
    last_hit_owner: str = ""

    def get_actual_speed(self) -> int:
        if self.slow_turns > 0:
            return max(1, self.speed - 1)
        return self.speed

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Enemy":
        return cls(**data)


@dataclass
class Tower:
    tower_type: str
    row: int
    col: int
    level: int = 1
    owner_user_id: str = ""

    @property
    def cfg(self) -> dict:
        return TOWER_TEMPLATES[self.tower_type]

    @property
    def atk(self) -> int:
        return self.cfg["base_atk"] + (self.level - 1) * 10

    @property
    def range(self) -> int:
        return self.cfg["range"]

    @property
    def name(self) -> str:
        return self.cfg["name"]

    @property
    def upgrade_cost(self) -> int:
        return self.cfg["upgrade_cost"] + (self.level - 1) * 20

    @property
    def kind(self) -> str:
        return self.cfg["kind"]

    @property
    def heal_amount(self) -> int:
        if self.kind != "heal":
            return 0
        return 1 + (self.level - 1) // 2

    def position_key(self) -> str:
        return f"{self.row},{self.col}"

    def to_dict(self) -> dict:
        return {
            "tower_type": self.tower_type,
            "row": self.row,
            "col": self.col,
            "level": self.level,
            "owner_user_id": self.owner_user_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Tower":
        return cls(**data)


@dataclass
class MapState:
    name: str
    path: List[Tuple[int, int]]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": [[r, c] for r, c in self.path],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MapState":
        return cls(
            name=data["name"],
            path=[(int(p[0]), int(p[1])) for p in data["path"]],
        )

    def is_path_cell(self, row: int, col: int) -> bool:
        return (row, col) in self.path

    def is_buildable(self, row: int, col: int) -> bool:
        if not in_bounds(row, col):
            return False
        return (row, col) not in self.path

    def start(self) -> Tuple[int, int]:
        return self.path[0]

    def end(self) -> Tuple[int, int]:
        return self.path[-1]


def random_map_state() -> MapState:
    tpl = random.choice(MAP_TEMPLATES)
    return MapState(name=tpl["name"], path=list(tpl["path"]))


def spawn_enemies_for_wave(wave: int, prefix: str = "e") -> List[Enemy]:
    enemies: List[Enemy] = []
    enemy_count = 2 + wave

    for i in range(enemy_count):
        if wave == MAX_WAVE and i == enemy_count - 1:
            hp = 140 + wave * 25
            enemies.append(
                Enemy(
                    uid=f"{prefix}-boss-{wave}-{i}",
                    name="Boss兔将军",
                    hp=hp,
                    max_hp=hp,
                    speed=1,
                    reward=120,
                    armor=8,
                    path_index=0,
                )
            )
            continue

        base = random.choice(ENEMY_ARCHETYPES)
        hp = base["hp"] + wave * 12
        reward = base["reward"] + wave * 3
        armor = base["armor"] + (1 if wave >= 3 else 0)

        enemies.append(
            Enemy(
                uid=f"{prefix}-{wave}-{i}",
                name=base["name"],
                hp=hp,
                max_hp=hp,
                speed=base["speed"],
                reward=reward,
                armor=armor,
                path_index=0,
            )
        )
    return enemies


@dataclass
class GameSession:
    session_id: str
    mode: str = "normal"
    wave: int = 0
    turn: int = 0
    gold: int = 200
    carrot_hp: int = 10
    max_carrot_hp: int = 10
    towers: Dict[str, Tower] = field(default_factory=dict)
    enemies: List[Enemy] = field(default_factory=list)
    status: str = "idle"
    created_by: str = ""
    updated_at: str = ""
    total_kills: int = 0
    total_gold_earned: int = 0
    total_heals: int = 0
    map_state: Optional[MapState] = None

    def is_over(self) -> bool:
        return self.status in ("win", "lose")

    def start(self, created_by: str = "", mode: str = "normal") -> str:
        self.mode = mode
        self.wave = 1
        self.turn = 0
        self.gold = 200
        self.carrot_hp = 10
        self.max_carrot_hp = 10
        self.towers = {}
        self.enemies = []
        self.status = "running"
        self.created_by = created_by
        self.total_kills = 0
        self.total_gold_earned = 0
        self.total_heals = 0
        self.map_state = random_map_state()
        self.spawn_wave(self.wave)
        return (
            f"游戏开始，模式：{self.mode}，地图：{self.map_state.name}，第 1 波敌人已出现！\n"
            f"可建造格：{self.get_buildable_cells_text(limit=12)}"
        )

    def spawn_wave(self, wave: int) -> None:
        self.enemies = spawn_enemies_for_wave(wave, prefix="solo")

    def enemy_coord(self, enemy: Enemy) -> Tuple[int, int]:
        if not self.map_state:
            return (0, 0)
        idx = max(0, min(enemy.path_index, len(self.map_state.path) - 1))
        return self.map_state.path[idx]

    def get_buildable_cells(self) -> List[Tuple[int, int]]:
        if not self.map_state:
            return []
        cells: List[Tuple[int, int]] = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if self.map_state.is_buildable(row, col):
                    cells.append((row, col))
        return cells

    def get_buildable_cells_text(self, limit: int | None = None) -> str:
        cells = self.get_buildable_cells()
        if not cells:
            return "无"
        parts = [f"({r},{c})" for r, c in cells]
        if limit is not None and len(parts) > limit:
            shown = "、".join(parts[:limit])
            return f"{shown} …… 共 {len(parts)} 个"
        return "、".join(parts)

    def _build_invalid_position_message(self, row: int, col: int) -> str:
        if not in_bounds(row, col):
            return f"坐标 ({row},{col}) 超出地图范围。\n有效范围：行 0~{GRID_ROWS - 1}，列 0~{GRID_COLS - 1}。"
        if not self.map_state:
            return "地图未初始化。"
        if (row, col) == self.map_state.start():
            return f"坐标 ({row},{col}) 是起点，不能建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"
        if (row, col) == self.map_state.end():
            return f"坐标 ({row},{col}) 是萝卜终点，不能建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"
        if self.map_state.is_path_cell(row, col):
            return f"坐标 ({row},{col}) 是敌人路径格，不能建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"
        return f"坐标 ({row},{col}) 不可建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"

    def build_tower(self, tower_type: str, row: int, col: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "当前没有进行中的游戏，请先使用 /萝卜开始"
        if tower_type not in TOWER_TEMPLATES:
            return False, "未知塔类型，可用：弓箭 / 炮塔 / 冰塔 / 治疗塔"
        if not in_bounds(row, col):
            return False, self._build_invalid_position_message(row, col)
        if not self.map_state:
            return False, "地图未初始化"
        if not self.map_state.is_buildable(row, col):
            return False, self._build_invalid_position_message(row, col)

        key = f"{row},{col}"
        if key in self.towers:
            tower = self.towers[key]
            return False, f"坐标 ({row},{col}) 已有防御塔：{tower.name} Lv{tower.level}。\n如需处理，可使用：/萝卜升级 {row} {col} 或 /萝卜拆除 {row} {col}"

        cost = TOWER_TEMPLATES[tower_type]["cost"]
        if self.gold < cost:
            return False, f"金币不足，需要 {cost}，当前仅有 {self.gold}"

        self.gold -= cost
        self.towers[key] = Tower(tower_type=tower_type, row=row, col=col, owner_user_id=self.created_by)
        return True, f"已在 ({row},{col}) 建造 {TOWER_TEMPLATES[tower_type]['name']}，消耗 {cost} 金币"

    def upgrade_tower(self, row: int, col: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "当前没有进行中的游戏"
        if not in_bounds(row, col):
            return False, f"坐标 ({row},{col}) 超出地图范围，不能升级。"
        key = f"{row},{col}"
        tower = self.towers.get(key)
        if not tower:
            return False, f"坐标 ({row},{col}) 没有防御塔，无法升级。\n可建造格：{self.get_buildable_cells_text(limit=12)}"
        if tower.level >= 5:
            return False, "该防御塔已满级"

        cost = tower.upgrade_cost
        if self.gold < cost:
            return False, f"金币不足，升级需要 {cost}，当前仅有 {self.gold}"

        self.gold -= cost
        tower.level += 1
        return True, f"({row},{col}) 的 {tower.name} 已升级到 Lv{tower.level}，消耗 {cost} 金币"

    def remove_tower(self, row: int, col: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "当前没有进行中的游戏"
        if not in_bounds(row, col):
            return False, f"坐标 ({row},{col}) 超出地图范围，不能拆除。"

        key = f"{row},{col}"
        tower = self.towers.get(key)
        if not tower:
            return False, f"坐标 ({row},{col}) 没有防御塔，无法拆除。"

        refund = int((tower.cfg["cost"] + (tower.level - 1) * tower.cfg["upgrade_cost"]) * 0.5)
        self.gold += refund
        del self.towers[key]
        return True, f"已拆除 ({row},{col}) 的 {tower.name}，返还 {refund} 金币"

    def next_wave(self) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "当前没有进行中的游戏"
        if any(e.alive for e in self.enemies):
            return False, "当前还有敌人存活，不能直接进入下一波"

        if self.mode == "normal" and self.wave >= MAX_WAVE:
            self.status = "win"
            return True, "所有波次已完成，恭喜你成功保卫了萝卜！"

        self.wave += 1
        self.turn = 0
        self.spawn_wave(self.wave)
        return True, f"第 {self.wave} 波开始！敌人来袭！"

    def step_turn(self) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "当前没有进行中的游戏"
        if not any(e.alive for e in self.enemies):
            if self.mode == "normal" and self.wave >= MAX_WAVE:
                self.status = "win"
                return True, "所有波次都已清空，恭喜通关！"
            return False, "当前没有敌人，请使用 /萝卜下一波"

        self.turn += 1
        logs: List[str] = [f"模式：{self.mode} | 地图：{self.map_state.name if self.map_state else '未知'} | 第 {self.wave} 波 - 第 {self.turn} 回合"]

        logs.extend(self._tower_attack_phase())

        dead_rewards = 0
        dead_count = 0
        for enemy in self.enemies:
            if enemy.alive and enemy.hp <= 0:
                enemy.alive = False
                dead_rewards += enemy.reward
                dead_count += 1
                logs.append(f"{enemy.name} 被击败，获得 {enemy.reward} 金币")

        if dead_rewards > 0:
            self.gold += dead_rewards
            self.total_gold_earned += dead_rewards
            self.total_kills += dead_count

        if any(e.alive for e in self.enemies):
            logs.extend(self._enemy_move_phase())

        logs.extend(self._heal_phase())

        for enemy in self.enemies:
            if enemy.alive and enemy.slow_turns > 0:
                enemy.slow_turns -= 1

        if self.carrot_hp <= 0:
            self.status = "lose"
            logs.append("萝卜生命归零，游戏失败！")
        elif not any(e.alive for e in self.enemies):
            if self.mode == "normal" and self.wave >= MAX_WAVE:
                self.status = "win"
                logs.append("所有波次已清空，恭喜通关！")
            else:
                logs.append(f"第 {self.wave} 波已清空，可使用 /萝卜下一波")

        return True, "\n".join(logs)

    def _tower_attack_phase(self) -> List[str]:
        logs: List[str] = []
        if not self.towers:
            return ["本回合没有防御塔出手"]

        for key in sorted(self.towers.keys()):
            tower = self.towers[key]

            if tower.kind == "heal":
                logs.append(f"{tower.name}({tower.row},{tower.col},Lv{tower.level}) 待机治疗")
                continue

            targets = []
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                er, ec = self.enemy_coord(enemy)
                if manhattan((tower.row, tower.col), (er, ec)) <= tower.range:
                    targets.append(enemy)

            targets.sort(key=lambda e: (-e.path_index, e.hp))
            if not targets:
                logs.append(f"{tower.name}({tower.row},{tower.col}) 未找到目标")
                continue

            main_target = targets[0]
            dmg = max(1, tower.atk - main_target.armor)
            main_target.hp -= dmg
            main_target.last_hit_owner = tower.owner_user_id
            logs.append(f"{tower.name}({tower.row},{tower.col},Lv{tower.level}) 攻击 {main_target.name}，造成 {dmg} 伤害")

            if tower.kind == "splash":
                for extra in targets[1:3]:
                    splash = max(1, tower.atk // 2 - extra.armor)
                    extra.hp -= splash
                    extra.last_hit_owner = tower.owner_user_id
                    logs.append(f"  ↳ 溅射到 {extra.name}，造成 {splash} 伤害")
            elif tower.kind == "slow":
                main_target.slow_turns = max(main_target.slow_turns, 2)
                logs.append(f"  ↳ {main_target.name} 被减速 2 回合")

        return logs

    def _enemy_move_phase(self) -> List[str]:
        logs: List[str] = []
        if not self.map_state:
            return logs

        last_index = len(self.map_state.path) - 1
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            old_index = enemy.path_index
            enemy.path_index += enemy.get_actual_speed()
            if enemy.path_index >= last_index:
                enemy.alive = False
                self.carrot_hp -= 1
                logs.append(f"{enemy.name} 冲到了萝卜！萝卜生命 -1")
            else:
                old_pos = self.map_state.path[old_index]
                new_pos = self.map_state.path[enemy.path_index]
                logs.append(f"{enemy.name} 从 {old_pos} 前进到 {new_pos}")
        return logs

    def _heal_phase(self) -> List[str]:
        logs: List[str] = []
        total_heal = 0
        for tower in self.towers.values():
            if tower.kind == "heal":
                total_heal += tower.heal_amount

        if total_heal <= 0:
            return logs
        if self.carrot_hp >= self.max_carrot_hp:
            logs.append("治疗塔尝试治疗，但萝卜生命已满")
            return logs

        before = self.carrot_hp
        self.carrot_hp = min(self.max_carrot_hp, self.carrot_hp + total_heal)
        actual = self.carrot_hp - before
        if actual > 0:
            self.total_heals += actual
            logs.append(f"治疗塔共为萝卜恢复了 {actual} 点生命")
        return logs

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "wave": self.wave,
            "turn": self.turn,
            "gold": self.gold,
            "carrot_hp": self.carrot_hp,
            "max_carrot_hp": self.max_carrot_hp,
            "towers": {k: v.to_dict() for k, v in self.towers.items()},
            "enemies": [e.to_dict() for e in self.enemies],
            "status": self.status,
            "created_by": self.created_by,
            "updated_at": self.updated_at,
            "total_kills": self.total_kills,
            "total_gold_earned": self.total_gold_earned,
            "total_heals": self.total_heals,
            "map_state": self.map_state.to_dict() if self.map_state else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameSession":
        session = cls(
            session_id=data["session_id"],
            mode=data.get("mode", "normal"),
            wave=data.get("wave", 0),
            turn=data.get("turn", 0),
            gold=data.get("gold", 200),
            carrot_hp=data.get("carrot_hp", 10),
            max_carrot_hp=data.get("max_carrot_hp", 10),
            status=data.get("status", "idle"),
            created_by=data.get("created_by", ""),
            updated_at=data.get("updated_at", ""),
            total_kills=data.get("total_kills", 0),
            total_gold_earned=data.get("total_gold_earned", 0),
            total_heals=data.get("total_heals", 0),
        )
        session.towers = {k: Tower.from_dict(v) for k, v in data.get("towers", {}).items()}
        session.enemies = [Enemy.from_dict(e) for e in data.get("enemies", [])]
        raw_map = data.get("map_state")
        session.map_state = MapState.from_dict(raw_map) if raw_map else None
        return session


@dataclass
class CoopPlayer:
    user_id: str
    nickname: str = ""
    gold: int = 200
    build_count: int = 0
    upgrade_count: int = 0
    remove_count: int = 0
    gold_spent: int = 0
    gold_earned: int = 0
    heal_contributed: int = 0
    kills_contributed: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CoopPlayer":
        return cls(**data)


@dataclass
class CoopGameSession:
    session_id: str
    wave: int = 0
    turn: int = 0
    carrot_hp: int = 10
    max_carrot_hp: int = 10
    towers: Dict[str, Tower] = field(default_factory=dict)
    enemies: List[Enemy] = field(default_factory=list)
    players: Dict[str, CoopPlayer] = field(default_factory=dict)
    status: str = "waiting"
    host_user_id: str = ""
    updated_at: str = ""
    total_kills: int = 0
    total_gold_earned: int = 0
    total_heals: int = 0
    map_state: Optional[MapState] = None

    def enemy_coord(self, enemy: Enemy) -> Tuple[int, int]:
        if not self.map_state:
            return (0, 0)
        idx = max(0, min(enemy.path_index, len(self.map_state.path) - 1))
        return self.map_state.path[idx]

    def get_buildable_cells(self) -> List[Tuple[int, int]]:
        if not self.map_state:
            return []
        cells: List[Tuple[int, int]] = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if self.map_state.is_buildable(row, col):
                    cells.append((row, col))
        return cells

    def get_buildable_cells_text(self, limit: int | None = None) -> str:
        cells = self.get_buildable_cells()
        if not cells:
            return "无"
        parts = [f"({r},{c})" for r, c in cells]
        if limit is not None and len(parts) > limit:
            shown = "、".join(parts[:limit])
            return f"{shown} …… 共 {len(parts)} 个"
        return "、".join(parts)

    def _build_invalid_position_message(self, row: int, col: int) -> str:
        if not in_bounds(row, col):
            return f"坐标 ({row},{col}) 超出地图范围。\n有效范围：行 0~{GRID_ROWS - 1}，列 0~{GRID_COLS - 1}。"
        if not self.map_state:
            return "地图未初始化。"
        if (row, col) == self.map_state.start():
            return f"坐标 ({row},{col}) 是起点，不能建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"
        if (row, col) == self.map_state.end():
            return f"坐标 ({row},{col}) 是萝卜终点，不能建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"
        if self.map_state.is_path_cell(row, col):
            return f"坐标 ({row},{col}) 是敌人路径格，不能建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"
        return f"坐标 ({row},{col}) 不可建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"

    def add_player(self, user_id: str, nickname: str = "") -> Tuple[bool, str]:
        if self.status != "waiting":
            return False, "游戏已开始，不能再加入"
        if user_id in self.players:
            return False, "你已经在合作房间中了"
        if len(self.players) >= COOP_MAX_PLAYERS:
            return False, f"合作房间人数已满，最多 {COOP_MAX_PLAYERS} 人"
        self.players[user_id] = CoopPlayer(user_id=user_id, nickname=nickname, gold=200)
        return True, f"加入成功，当前人数：{len(self.players)}/{COOP_MAX_PLAYERS}"

    def remove_player(self, user_id: str) -> Tuple[bool, str]:
        if user_id not in self.players:
            return False, "你不在合作房间中"
        if self.status == "running":
            return False, "游戏进行中暂不支持退出房间"
        del self.players[user_id]
        if self.host_user_id == user_id:
            self.host_user_id = next(iter(self.players.keys()), "")
        return True, "已退出合作房间"

    def start(self, user_id: str) -> Tuple[bool, str]:
        if user_id != self.host_user_id:
            return False, "只有房主可以开始合作游戏"
        if self.status != "waiting":
            return False, "当前房间不处于等待状态"
        if len(self.players) < COOP_MIN_PLAYERS:
            return False, f"合作模式至少需要 {COOP_MIN_PLAYERS} 人"

        self.wave = 1
        self.turn = 0
        self.carrot_hp = 10
        self.max_carrot_hp = 10
        self.towers = {}
        self.enemies = []
        self.map_state = random_map_state()
        self.enemies = spawn_enemies_for_wave(1, prefix="coop")
        self.status = "running"
        self.total_kills = 0
        self.total_gold_earned = 0
        self.total_heals = 0

        for player in self.players.values():
            player.gold = 200
            player.build_count = 0
            player.upgrade_count = 0
            player.remove_count = 0
            player.gold_spent = 0
            player.gold_earned = 0
            player.heal_contributed = 0
            player.kills_contributed = 0

        return True, f"合作模式已开始！地图：{self.map_state.name}，当前人数：{len(self.players)}，第 1 波敌人已出现\n可建造格：{self.get_buildable_cells_text(limit=12)}"

    def build_tower(self, user_id: str, tower_type: str, row: int, col: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "合作游戏尚未开始"
        player = self.players.get(user_id)
        if not player:
            return False, "你不在当前合作房间中"
        if tower_type not in TOWER_TEMPLATES:
            return False, "未知塔类型，可用：弓箭 / 炮塔 / 冰塔 / 治疗塔"
        if not in_bounds(row, col):
            return False, self._build_invalid_position_message(row, col)
        if not self.map_state:
            return False, "地图未初始化"
        if not self.map_state.is_buildable(row, col):
            return False, self._build_invalid_position_message(row, col)

        key = f"{row},{col}"
        if key in self.towers:
            tower = self.towers[key]
            return False, f"坐标 ({row},{col}) 已有防御塔：{tower.name} Lv{tower.level}。\n可使用：/萝卜合作升级 {row} {col} 或 /萝卜合作拆除 {row} {col}"

        cost = TOWER_TEMPLATES[tower_type]["cost"]
        if player.gold < cost:
            return False, f"你的金币不足，需要 {cost}，当前仅有 {player.gold}"

        player.gold -= cost
        player.build_count += 1
        player.gold_spent += cost
        self.towers[key] = Tower(tower_type=tower_type, row=row, col=col, level=1, owner_user_id=user_id)
        return True, f"你已在 ({row},{col}) 建造 {TOWER_TEMPLATES[tower_type]['name']}，消耗 {cost} 金币"

    def upgrade_tower(self, user_id: str, row: int, col: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "合作游戏尚未开始"
        player = self.players.get(user_id)
        if not player:
            return False, "你不在当前合作房间中"
        if not in_bounds(row, col):
            return False, f"坐标 ({row},{col}) 超出地图范围，不能升级。"

        key = f"{row},{col}"
        tower = self.towers.get(key)
        if not tower:
            return False, f"坐标 ({row},{col}) 没有防御塔，无法升级。"
        if tower.level >= 5:
            return False, "该防御塔已满级"

        cost = tower.upgrade_cost
        if player.gold < cost:
            return False, f"你的金币不足，升级需要 {cost}，当前仅有 {player.gold}"

        player.gold -= cost
        player.upgrade_count += 1
        player.gold_spent += cost
        tower.level += 1
        return True, f"你将 ({row},{col}) 的 {tower.name} 升级到 Lv{tower.level}，消耗 {cost} 金币"

    def remove_tower(self, user_id: str, row: int, col: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "合作游戏尚未开始"
        player = self.players.get(user_id)
        if not player:
            return False, "你不在当前合作房间中"
        if not in_bounds(row, col):
            return False, f"坐标 ({row},{col}) 超出地图范围，不能拆除。"

        key = f"{row},{col}"
        tower = self.towers.get(key)
        if not tower:
            return False, f"坐标 ({row},{col}) 没有防御塔，无法拆除。"

        refund = int((tower.cfg["cost"] + (tower.level - 1) * tower.cfg["upgrade_cost"]) * 0.5)
        player.gold += refund
        player.remove_count += 1
        del self.towers[key]
        return True, f"你拆除了 ({row},{col}) 的 {tower.name}，返还 {refund} 金币"

    def next_wave(self, user_id: str) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "合作游戏尚未开始"
        if user_id != self.host_user_id:
            return False, "只有房主可以推进到下一波"
        if any(e.alive for e in self.enemies):
            return False, "当前还有敌人存活，不能直接进入下一波"

        if self.wave >= MAX_WAVE:
            self.status = "win"
            return True, "所有波次已完成，恭喜你们成功保卫了萝卜！"

        self.wave += 1
        self.turn = 0
        self.enemies = spawn_enemies_for_wave(self.wave, prefix="coop")
        return True, f"第 {self.wave} 波开始！敌人来袭！"

    def step_turn(self, user_id: str) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "合作游戏尚未开始"
        if user_id != self.host_user_id:
            return False, "只有房主可以推进回合"
        if not any(e.alive for e in self.enemies):
            if self.wave >= MAX_WAVE:
                self.status = "win"
                return True, "所有波次都已清空，恭喜通关！"
            return False, "当前没有敌人，请使用 /萝卜合作下一波"

        self.turn += 1
        logs: List[str] = [f"【合作模式】地图：{self.map_state.name if self.map_state else '未知'} | 第 {self.wave} 波 - 第 {self.turn} 回合"]
        logs.extend(self._tower_attack_phase())

        reward_pool = 0
        dead_count = 0
        for enemy in self.enemies:
            if enemy.alive and enemy.hp <= 0:
                enemy.alive = False
                reward_pool += enemy.reward
                dead_count += 1
                owner = enemy.last_hit_owner
                if owner and owner in self.players:
                    self.players[owner].kills_contributed += 1
                logs.append(f"{enemy.name} 被击败，掉落 {enemy.reward} 金币")

        if reward_pool > 0 and self.players:
            per_player = reward_pool // len(self.players)
            extra = reward_pool % len(self.players)
            player_ids = sorted(self.players.keys())
            for idx, pid in enumerate(player_ids):
                gain = per_player + (1 if idx < extra else 0)
                self.players[pid].gold += gain
                self.players[pid].gold_earned += gain
            self.total_gold_earned += reward_pool
            self.total_kills += dead_count
            logs.append(f"本回合共掉落 {reward_pool} 金币，已按人数平分")

        if any(e.alive for e in self.enemies):
            logs.extend(self._enemy_move_phase())

        logs.extend(self._heal_phase())

        for enemy in self.enemies:
            if enemy.alive and enemy.slow_turns > 0:
                enemy.slow_turns -= 1

        if self.carrot_hp <= 0:
            self.status = "lose"
            logs.append("萝卜生命归零，合作游戏失败！")
        elif not any(e.alive for e in self.enemies):
            if self.wave >= MAX_WAVE:
                self.status = "win"
                logs.append("所有波次已清空，恭喜通关！")
            else:
                logs.append(f"第 {self.wave} 波已清空，可使用 /萝卜合作下一波")

        return True, "\n".join(logs)

    def _tower_attack_phase(self) -> List[str]:
        logs: List[str] = []
        if not self.towers:
            return ["本回合没有防御塔出手"]

        for key in sorted(self.towers.keys()):
            tower = self.towers[key]
            if tower.kind == "heal":
                logs.append(f"{tower.name}({tower.row},{tower.col},Lv{tower.level}) 待机治疗")
                continue

            targets = []
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                er, ec = self.enemy_coord(enemy)
                if manhattan((tower.row, tower.col), (er, ec)) <= tower.range:
                    targets.append(enemy)

            targets.sort(key=lambda e: (-e.path_index, e.hp))
            if not targets:
                logs.append(f"{tower.name}({tower.row},{tower.col}) 未找到目标")
                continue

            main_target = targets[0]
            dmg = max(1, tower.atk - main_target.armor)
            main_target.hp -= dmg
            main_target.last_hit_owner = tower.owner_user_id
            owner_name = self._player_name(tower.owner_user_id)
            logs.append(f"{tower.name}({tower.row},{tower.col},Lv{tower.level})[{owner_name}] 攻击 {main_target.name}，造成 {dmg} 伤害")

            if tower.kind == "splash":
                for extra in targets[1:3]:
                    splash = max(1, tower.atk // 2 - extra.armor)
                    extra.hp -= splash
                    extra.last_hit_owner = tower.owner_user_id
                    logs.append(f"  ↳ 溅射到 {extra.name}，造成 {splash} 伤害")
            elif tower.kind == "slow":
                main_target.slow_turns = max(main_target.slow_turns, 2)
                logs.append(f"  ↳ {main_target.name} 被减速 2 回合")
        return logs

    def _enemy_move_phase(self) -> List[str]:
        logs: List[str] = []
        if not self.map_state:
            return logs

        last_index = len(self.map_state.path) - 1
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            old_index = enemy.path_index
            enemy.path_index += enemy.get_actual_speed()
            if enemy.path_index >= last_index:
                enemy.alive = False
                self.carrot_hp -= 1
                logs.append(f"{enemy.name} 冲到了萝卜！萝卜生命 -1")
            else:
                old_pos = self.map_state.path[old_index]
                new_pos = self.map_state.path[enemy.path_index]
                logs.append(f"{enemy.name} 从 {old_pos} 前进到 {new_pos}")
        return logs

    def _heal_phase(self) -> List[str]:
        logs: List[str] = []
        total_heal = 0
        owner_heal: Dict[str, int] = {}
        for tower in self.towers.values():
            if tower.kind != "heal":
                continue
            amount = tower.heal_amount
            total_heal += amount
            owner_heal[tower.owner_user_id] = owner_heal.get(tower.owner_user_id, 0) + amount

        if total_heal <= 0:
            return logs
        if self.carrot_hp >= self.max_carrot_hp:
            logs.append("治疗塔尝试治疗，但萝卜生命已满")
            return logs

        before = self.carrot_hp
        self.carrot_hp = min(self.max_carrot_hp, self.carrot_hp + total_heal)
        actual = self.carrot_hp - before
        if actual <= 0:
            return logs

        self.total_heals += actual
        total_owner_heal = sum(owner_heal.values())
        if total_owner_heal > 0:
            assigned = 0
            owner_ids = sorted(owner_heal.keys())
            for idx, oid in enumerate(owner_ids):
                raw = owner_heal[oid]
                share = actual * raw // total_owner_heal
                if idx == len(owner_ids) - 1:
                    share = actual - assigned
                assigned += share
                if oid in self.players:
                    self.players[oid].heal_contributed += share

        logs.append(f"治疗塔共为萝卜恢复了 {actual} 点生命")
        return logs

    def _player_name(self, user_id: str) -> str:
        player = self.players.get(user_id)
        if not player:
            return user_id
        return player.nickname or player.user_id

    def get_contribution_rankings(self) -> List[dict]:
        rows = []
        for player in self.players.values():
            rows.append(
                {
                    "user_id": player.user_id,
                    "nickname": player.nickname,
                    "gold": player.gold,
                    "build_count": player.build_count,
                    "upgrade_count": player.upgrade_count,
                    "remove_count": player.remove_count,
                    "gold_spent": player.gold_spent,
                    "gold_earned": player.gold_earned,
                    "heal_contributed": player.heal_contributed,
                    "kills_contributed": player.kills_contributed,
                }
            )
        rows.sort(key=lambda x: (-x["kills_contributed"], -x["heal_contributed"], -x["build_count"], -x["upgrade_count"], -x["gold_spent"]))
        return rows

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "wave": self.wave,
            "turn": self.turn,
            "carrot_hp": self.carrot_hp,
            "max_carrot_hp": self.max_carrot_hp,
            "towers": {k: v.to_dict() for k, v in self.towers.items()},
            "enemies": [e.to_dict() for e in self.enemies],
            "players": {uid: p.to_dict() for uid, p in self.players.items()},
            "status": self.status,
            "host_user_id": self.host_user_id,
            "updated_at": self.updated_at,
            "total_kills": self.total_kills,
            "total_gold_earned": self.total_gold_earned,
            "total_heals": self.total_heals,
            "map_state": self.map_state.to_dict() if self.map_state else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CoopGameSession":
        session = cls(
            session_id=data["session_id"],
            wave=data.get("wave", 0),
            turn=data.get("turn", 0),
            carrot_hp=data.get("carrot_hp", 10),
            max_carrot_hp=data.get("max_carrot_hp", 10),
            status=data.get("status", "waiting"),
            host_user_id=data.get("host_user_id", ""),
            updated_at=data.get("updated_at", ""),
            total_kills=data.get("total_kills", 0),
            total_gold_earned=data.get("total_gold_earned", 0),
            total_heals=data.get("total_heals", 0),
        )
        session.towers = {k: Tower.from_dict(v) for k, v in data.get("towers", {}).items()}
        session.enemies = [Enemy.from_dict(e) for e in data.get("enemies", [])]
        session.players = {uid: CoopPlayer.from_dict(p) for uid, p in data.get("players", {}).items()}
        raw_map = data.get("map_state")
        session.map_state = MapState.from_dict(raw_map) if raw_map else None
        return session


@dataclass
class PvpPlayerState:
    user_id: str
    nickname: str = ""
    gold: int = 200
    carrot_hp: int = 10
    max_carrot_hp: int = 10
    wave: int = 1
    turn: int = 0
    towers: Dict[str, Tower] = field(default_factory=dict)
    enemies: List[Enemy] = field(default_factory=list)
    status: str = "running"  # running / win / lose
    total_kills: int = 0
    total_gold_earned: int = 0
    total_heals: int = 0
    build_count: int = 0
    upgrade_count: int = 0
    remove_count: int = 0
    gold_spent: int = 0

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "gold": self.gold,
            "carrot_hp": self.carrot_hp,
            "max_carrot_hp": self.max_carrot_hp,
            "wave": self.wave,
            "turn": self.turn,
            "towers": {k: v.to_dict() for k, v in self.towers.items()},
            "enemies": [e.to_dict() for e in self.enemies],
            "status": self.status,
            "total_kills": self.total_kills,
            "total_gold_earned": self.total_gold_earned,
            "total_heals": self.total_heals,
            "build_count": self.build_count,
            "upgrade_count": self.upgrade_count,
            "remove_count": self.remove_count,
            "gold_spent": self.gold_spent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PvpPlayerState":
        state = cls(
            user_id=data["user_id"],
            nickname=data.get("nickname", ""),
            gold=data.get("gold", 200),
            carrot_hp=data.get("carrot_hp", 10),
            max_carrot_hp=data.get("max_carrot_hp", 10),
            wave=data.get("wave", 1),
            turn=data.get("turn", 0),
            status=data.get("status", "running"),
            total_kills=data.get("total_kills", 0),
            total_gold_earned=data.get("total_gold_earned", 0),
            total_heals=data.get("total_heals", 0),
            build_count=data.get("build_count", 0),
            upgrade_count=data.get("upgrade_count", 0),
            remove_count=data.get("remove_count", 0),
            gold_spent=data.get("gold_spent", 0),
        )
        state.towers = {k: Tower.from_dict(v) for k, v in data.get("towers", {}).items()}
        state.enemies = [Enemy.from_dict(e) for e in data.get("enemies", [])]
        return state


@dataclass
class PvpGameSession:
    session_id: str
    status: str = "waiting"
    host_user_id: str = ""
    updated_at: str = ""
    map_state: Optional[MapState] = None
    players: Dict[str, PvpPlayerState] = field(default_factory=dict)

    def add_player(self, user_id: str, nickname: str = "") -> Tuple[bool, str]:
        if self.status != "waiting":
            return False, "PVP 已开始，不能再加入"
        if user_id in self.players:
            return False, "你已经在 PVP 房间中了"
        if len(self.players) >= PVP_MAX_PLAYERS:
            return False, f"PVP 房间人数已满，最多 {PVP_MAX_PLAYERS} 人"
        self.players[user_id] = PvpPlayerState(user_id=user_id, nickname=nickname)
        return True, f"加入成功，当前人数：{len(self.players)}/{PVP_MAX_PLAYERS}"

    def remove_player(self, user_id: str) -> Tuple[bool, str]:
        if user_id not in self.players:
            return False, "你不在 PVP 房间中"
        if self.status == "running":
            return False, "PVP 进行中暂不支持退出房间"
        del self.players[user_id]
        if self.host_user_id == user_id:
            self.host_user_id = next(iter(self.players.keys()), "")
        return True, "已退出 PVP 房间"

    def start(self, user_id: str) -> Tuple[bool, str]:
        if user_id != self.host_user_id:
            return False, "只有房主可以开始 PVP"
        if self.status != "waiting":
            return False, "当前房间不处于等待状态"
        if len(self.players) < PVP_MIN_PLAYERS:
            return False, f"PVP 至少需要 {PVP_MIN_PLAYERS} 人"

        self.status = "running"
        self.map_state = random_map_state()

        for uid, player in self.players.items():
            player.gold = 200
            player.carrot_hp = 10
            player.max_carrot_hp = 10
            player.wave = 1
            player.turn = 0
            player.towers = {}
            player.enemies = spawn_enemies_for_wave(1, prefix=f"pvp-{uid}")
            player.status = "running"
            player.total_kills = 0
            player.total_gold_earned = 0
            player.total_heals = 0
            player.build_count = 0
            player.upgrade_count = 0
            player.remove_count = 0
            player.gold_spent = 0

        return True, f"PVP 已开始！共享地图：{self.map_state.name}，当前人数：{len(self.players)}"

    def enemy_coord(self, enemy: Enemy) -> Tuple[int, int]:
        if not self.map_state:
            return (0, 0)
        idx = max(0, min(enemy.path_index, len(self.map_state.path) - 1))
        return self.map_state.path[idx]

    def get_buildable_cells(self) -> List[Tuple[int, int]]:
        if not self.map_state:
            return []
        cells: List[Tuple[int, int]] = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if self.map_state.is_buildable(row, col):
                    cells.append((row, col))
        return cells

    def get_buildable_cells_text(self, limit: int | None = None) -> str:
        cells = self.get_buildable_cells()
        if not cells:
            return "无"
        parts = [f"({r},{c})" for r, c in cells]
        if limit is not None and len(parts) > limit:
            shown = "、".join(parts[:limit])
            return f"{shown} …… 共 {len(parts)} 个"
        return "、".join(parts)

    def _invalid_pos_msg(self, row: int, col: int) -> str:
        if not in_bounds(row, col):
            return f"坐标 ({row},{col}) 超出地图范围。\n有效范围：行 0~{GRID_ROWS - 1}，列 0~{GRID_COLS - 1}。"
        if not self.map_state:
            return "地图未初始化。"
        if (row, col) == self.map_state.start():
            return f"坐标 ({row},{col}) 是起点，不能建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"
        if (row, col) == self.map_state.end():
            return f"坐标 ({row},{col}) 是萝卜终点，不能建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"
        if self.map_state.is_path_cell(row, col):
            return f"坐标 ({row},{col}) 是敌人路径格，不能建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"
        return f"坐标 ({row},{col}) 不可建造。\n可建造格：{self.get_buildable_cells_text(limit=12)}"

    def build_tower(self, user_id: str, tower_type: str, row: int, col: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "PVP 尚未开始"
        player = self.players.get(user_id)
        if not player:
            return False, "你不在当前 PVP 房间中"
        if player.status != "running":
            return False, "你当前已出局，不能继续操作"
        if tower_type not in TOWER_TEMPLATES:
            return False, "未知塔类型，可用：弓箭 / 炮塔 / 冰塔 / 治疗塔"
        if not in_bounds(row, col):
            return False, self._invalid_pos_msg(row, col)
        if not self.map_state:
            return False, "地图未初始化"
        if not self.map_state.is_buildable(row, col):
            return False, self._invalid_pos_msg(row, col)

        key = f"{row},{col}"
        if key in player.towers:
            tower = player.towers[key]
            return False, f"你在 ({row},{col}) 已有防御塔：{tower.name} Lv{tower.level}"

        cost = TOWER_TEMPLATES[tower_type]["cost"]
        if player.gold < cost:
            return False, f"你的金币不足，需要 {cost}，当前仅有 {player.gold}"

        player.gold -= cost
        player.build_count += 1
        player.gold_spent += cost
        player.towers[key] = Tower(tower_type=tower_type, row=row, col=col, level=1, owner_user_id=user_id)
        return True, f"你已在 ({row},{col}) 建造 {TOWER_TEMPLATES[tower_type]['name']}，消耗 {cost} 金币"

    def upgrade_tower(self, user_id: str, row: int, col: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "PVP 尚未开始"
        player = self.players.get(user_id)
        if not player:
            return False, "你不在当前 PVP 房间中"
        if player.status != "running":
            return False, "你当前已出局，不能继续操作"
        if not in_bounds(row, col):
            return False, f"坐标 ({row},{col}) 超出地图范围，不能升级。"

        key = f"{row},{col}"
        tower = player.towers.get(key)
        if not tower:
            return False, f"你在 ({row},{col}) 没有防御塔，无法升级。"
        if tower.level >= 5:
            return False, "该防御塔已满级"

        cost = tower.upgrade_cost
        if player.gold < cost:
            return False, f"你的金币不足，升级需要 {cost}，当前仅有 {player.gold}"

        player.gold -= cost
        player.upgrade_count += 1
        player.gold_spent += cost
        tower.level += 1
        return True, f"你将 ({row},{col}) 的 {tower.name} 升级到 Lv{tower.level}，消耗 {cost} 金币"

    def remove_tower(self, user_id: str, row: int, col: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "PVP 尚未开始"
        player = self.players.get(user_id)
        if not player:
            return False, "你不在当前 PVP 房间中"
        if player.status != "running":
            return False, "你当前已出局，不能继续操作"
        if not in_bounds(row, col):
            return False, f"坐标 ({row},{col}) 超出地图范围，不能拆除。"

        key = f"{row},{col}"
        tower = player.towers.get(key)
        if not tower:
            return False, f"你在 ({row},{col}) 没有防御塔，无法拆除。"

        refund = int((tower.cfg["cost"] + (tower.level - 1) * tower.cfg["upgrade_cost"]) * 0.5)
        player.gold += refund
        player.remove_count += 1
        del player.towers[key]
        return True, f"你拆除了 ({row},{col}) 的 {tower.name}，返还 {refund} 金币"

    def step_turn(self, user_id: str) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "PVP 尚未开始"
        if user_id != self.host_user_id:
            return False, "只有房主可以推进 PVP 回合"

        logs: List[str] = [f"【PVP 模式】共享地图：{self.map_state.name if self.map_state else '未知'}"]
        active_count = 0

        for uid in sorted(self.players.keys()):
            player = self.players[uid]
            if player.status != "running":
                continue
            active_count += 1
            logs.append(self._step_player_turn(player))

        if active_count == 0:
            return False, "所有玩家都已结束当前战局"

        return True, "\n\n".join(logs)

    def _step_player_turn(self, player: PvpPlayerState) -> str:
        if not any(e.alive for e in player.enemies):
            if player.wave >= MAX_WAVE:
                player.status = "win"
                return f"[{player.nickname or player.user_id}] 已完成全部波次，获得胜利！"
            return f"[{player.nickname or player.user_id}] 当前没有敌人，请等待房主推进下一波"

        player.turn += 1
        logs: List[str] = [f"[{player.nickname or player.user_id}] 第 {player.wave} 波 - 第 {player.turn} 回合"]

        # attack
        if not player.towers:
            logs.append("本回合没有防御塔出手")
        else:
            for key in sorted(player.towers.keys()):
                tower = player.towers[key]
                if tower.kind == "heal":
                    logs.append(f"{tower.name}({tower.row},{tower.col},Lv{tower.level}) 待机治疗")
                    continue

                targets = []
                for enemy in player.enemies:
                    if not enemy.alive:
                        continue
                    er, ec = self.enemy_coord(enemy)
                    if manhattan((tower.row, tower.col), (er, ec)) <= tower.range:
                        targets.append(enemy)

                targets.sort(key=lambda e: (-e.path_index, e.hp))
                if not targets:
                    logs.append(f"{tower.name}({tower.row},{tower.col}) 未找到目标")
                    continue

                main_target = targets[0]
                dmg = max(1, tower.atk - main_target.armor)
                main_target.hp -= dmg
                main_target.last_hit_owner = player.user_id
                logs.append(f"{tower.name}({tower.row},{tower.col},Lv{tower.level}) 攻击 {main_target.name}，造成 {dmg} 伤害")

                if tower.kind == "splash":
                    for extra in targets[1:3]:
                        splash = max(1, tower.atk // 2 - extra.armor)
                        extra.hp -= splash
                        extra.last_hit_owner = player.user_id
                        logs.append(f"  ↳ 溅射到 {extra.name}，造成 {splash} 伤害")
                elif tower.kind == "slow":
                    main_target.slow_turns = max(main_target.slow_turns, 2)
                    logs.append(f"  ↳ {main_target.name} 被减速 2 回合")

        reward = 0
        dead_count = 0
        for enemy in player.enemies:
            if enemy.alive and enemy.hp <= 0:
                enemy.alive = False
                reward += enemy.reward
                dead_count += 1
                logs.append(f"{enemy.name} 被击败，获得 {enemy.reward} 金币")

        if reward > 0:
            player.gold += reward
            player.total_gold_earned += reward
            player.total_kills += dead_count

        if any(e.alive for e in player.enemies):
            last_index = len(self.map_state.path) - 1 if self.map_state else 0
            for enemy in player.enemies:
                if not enemy.alive:
                    continue
                old_index = enemy.path_index
                enemy.path_index += enemy.get_actual_speed()
                if enemy.path_index >= last_index:
                    enemy.alive = False
                    player.carrot_hp -= 1
                    logs.append(f"{enemy.name} 冲到了萝卜！萝卜生命 -1")
                else:
                    old_pos = self.map_state.path[old_index]
                    new_pos = self.map_state.path[enemy.path_index]
                    logs.append(f"{enemy.name} 从 {old_pos} 前进到 {new_pos}")

        total_heal = 0
        for tower in player.towers.values():
            if tower.kind == "heal":
                total_heal += tower.heal_amount
        if total_heal > 0:
            if player.carrot_hp >= player.max_carrot_hp:
                logs.append("治疗塔尝试治疗，但萝卜生命已满")
            else:
                before = player.carrot_hp
                player.carrot_hp = min(player.max_carrot_hp, player.carrot_hp + total_heal)
                actual = player.carrot_hp - before
                if actual > 0:
                    player.total_heals += actual
                    logs.append(f"治疗塔共恢复了 {actual} 点生命")

        for enemy in player.enemies:
            if enemy.alive and enemy.slow_turns > 0:
                enemy.slow_turns -= 1

        if player.carrot_hp <= 0:
            player.status = "lose"
            logs.append("萝卜生命归零，你已出局！")
        elif not any(e.alive for e in player.enemies):
            if player.wave >= MAX_WAVE:
                player.status = "win"
                logs.append("所有波次已清空，你获得胜利！")
            else:
                logs.append(f"第 {player.wave} 波已清空，等待房主推进下一波")

        return "\n".join(logs)

    def next_wave(self, user_id: str) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "PVP 尚未开始"
        if user_id != self.host_user_id:
            return False, "只有房主可以推进 PVP 下一波"

        active = [p for p in self.players.values() if p.status == "running"]
        if not active:
            return False, "当前没有仍在对局中的玩家"

        for p in active:
            if any(e.alive for e in p.enemies):
                return False, "仍有玩家未清空当前波敌人，不能进入下一波"

        logs = []
        for p in active:
            if p.wave >= MAX_WAVE:
                p.status = "win"
                logs.append(f"[{p.nickname or p.user_id}] 已完成全部波次，获得胜利！")
                continue
            p.wave += 1
            p.turn = 0
            p.enemies = spawn_enemies_for_wave(p.wave, prefix=f"pvp-{p.user_id}")
            logs.append(f"[{p.nickname or p.user_id}] 第 {p.wave} 波开始！")

        return True, "\n".join(logs)

    def get_player_state(self, user_id: str) -> Optional[PvpPlayerState]:
        return self.players.get(user_id)

    def get_rankings(self) -> List[dict]:
        rows = []
        for p in self.players.values():
            rows.append({
                "user_id": p.user_id,
                "nickname": p.nickname,
                "status": p.status,
                "wave": p.wave,
                "turn": p.turn,
                "gold": p.gold,
                "carrot_hp": p.carrot_hp,
                "kills": p.total_kills,
                "gold_earned": p.total_gold_earned,
                "heals": p.total_heals,
            })
        rows.sort(key=lambda x: (0 if x["status"] == "win" else 1 if x["status"] == "running" else 2, -x["wave"], -x["turn"], -x["kills"], -x["carrot_hp"]))
        return rows

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "host_user_id": self.host_user_id,
            "updated_at": self.updated_at,
            "map_state": self.map_state.to_dict() if self.map_state else None,
            "players": {uid: p.to_dict() for uid, p in self.players.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PvpGameSession":
        session = cls(
            session_id=data["session_id"],
            status=data.get("status", "waiting"),
            host_user_id=data.get("host_user_id", ""),
            updated_at=data.get("updated_at", ""),
        )
        raw_map = data.get("map_state")
        session.map_state = MapState.from_dict(raw_map) if raw_map else None
        session.players = {uid: PvpPlayerState.from_dict(p) for uid, p in data.get("players", {}).items()}
        return session


class GameManager:
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}

    def get_session(self, session_id: str) -> Optional[GameSession]:
        return self.sessions.get(session_id)

    def create_or_reset_session(self, session_id: str, created_by: str = "", mode: str = "normal") -> GameSession:
        session = GameSession(session_id=session_id)
        self.sessions[session_id] = session
        session.start(created_by=created_by, mode=mode)
        return session

    def end_session(self, session_id: str) -> Optional[GameSession]:
        return self.sessions.pop(session_id, None)

    def load_sessions(self, raw: dict) -> None:
        self.sessions = {}
        for sid, session_data in raw.items():
            self.sessions[sid] = GameSession.from_dict(session_data)

    def dump_sessions(self) -> dict:
        return {sid: session.to_dict() for sid, session in self.sessions.items()}


class CoopGameManager:
    def __init__(self):
        self.sessions: Dict[str, CoopGameSession] = {}

    def get_session(self, session_id: str) -> Optional[CoopGameSession]:
        return self.sessions.get(session_id)

    def create_room(self, session_id: str, host_user_id: str, nickname: str = "") -> Tuple[bool, str, Optional[CoopGameSession]]:
        if session_id in self.sessions:
            return False, "当前会话已经存在合作房间", None
        room = CoopGameSession(session_id=session_id, host_user_id=host_user_id, status="waiting")
        room.players[host_user_id] = CoopPlayer(user_id=host_user_id, nickname=nickname, gold=200)
        self.sessions[session_id] = room
        return True, "合作房���已创建，你已成为房主", room

    def remove_room(self, session_id: str) -> Optional[CoopGameSession]:
        return self.sessions.pop(session_id, None)

    def load_sessions(self, raw: dict) -> None:
        self.sessions = {}
        for sid, session_data in raw.items():
            self.sessions[sid] = CoopGameSession.from_dict(session_data)

    def dump_sessions(self) -> dict:
        return {sid: session.to_dict() for sid, session in self.sessions.items()}


class PvpGameManager:
    def __init__(self):
        self.sessions: Dict[str, PvpGameSession] = {}

    def get_session(self, session_id: str) -> Optional[PvpGameSession]:
        return self.sessions.get(session_id)

    def create_room(self, session_id: str, host_user_id: str, nickname: str = "") -> Tuple[bool, str, Optional[PvpGameSession]]:
        if session_id in self.sessions:
            return False, "当前会话已经存在 PVP 房间", None
        room = PvpGameSession(session_id=session_id, host_user_id=host_user_id, status="waiting")
        room.players[host_user_id] = PvpPlayerState(user_id=host_user_id, nickname=nickname)
        self.sessions[session_id] = room
        return True, "PVP 房间已创建，你已成为房主", room

    def remove_room(self, session_id: str) -> Optional[PvpGameSession]:
        return self.sessions.pop(session_id, None)

    def load_sessions(self, raw: dict) -> None:
        self.sessions = {}
        for sid, session_data in raw.items():
            self.sessions[sid] = PvpGameSession.from_dict(session_data)

    def dump_sessions(self) -> dict:
        return {sid: session.to_dict() for sid, session in self.sessions.items()}
