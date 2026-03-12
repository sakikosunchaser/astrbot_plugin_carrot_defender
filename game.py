from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
import random


MAP_LENGTH = 5
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


def spawn_enemies_for_wave(wave: int, endless: bool = False, prefix: str = "e") -> List["Enemy"]:
    enemies: List[Enemy] = []

    if not endless:
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
                        pos=0,
                    )
                )
                continue

            base = random.choice(ENEMY_ARCHETYPES)
            hp = base["hp"] + wave * 12
            reward = base["reward"] + wave * 3
            enemies.append(
                Enemy(
                    uid=f"{prefix}-{wave}-{i}",
                    name=base["name"],
                    hp=hp,
                    max_hp=hp,
                    speed=base["speed"],
                    reward=reward,
                    armor=base["armor"] + (1 if wave >= 3 else 0),
                    pos=0,
                )
            )
        return enemies

    enemy_count = min(12, 2 + wave // 2)
    for i in range(enemy_count):
        is_boss = (wave % 10 == 0 and i == enemy_count - 1)
        if is_boss:
            hp = 180 + wave * 35
            armor = 8 + wave // 8
            reward = 150 + wave * 6
            enemies.append(
                Enemy(
                    uid=f"{prefix}-endless-boss-{wave}-{i}",
                    name=f"无尽Boss-{wave}",
                    hp=hp,
                    max_hp=hp,
                    speed=1 if wave < 20 else 2,
                    reward=reward,
                    armor=armor,
                    pos=0,
                )
            )
            continue

        base = random.choice(ENEMY_ARCHETYPES)
        hp = base["hp"] + wave * 15
        armor = base["armor"] + wave // 4
        speed = base["speed"]
        if wave >= 15 and random.random() < 0.2:
            speed += 1
        reward = base["reward"] + wave * 4
        enemies.append(
            Enemy(
                uid=f"{prefix}-endless-{wave}-{i}",
                name=base["name"],
                hp=hp,
                max_hp=hp,
                speed=min(3, speed),
                reward=reward,
                armor=armor,
                pos=0,
            )
        )
    return enemies


@dataclass
class Enemy:
    uid: str
    name: str
    hp: int
    max_hp: int
    speed: int
    reward: int
    armor: int = 0
    pos: int = 0
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
    position: int
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

    def to_dict(self) -> dict:
        return {
            "tower_type": self.tower_type,
            "position": self.position,
            "level": self.level,
            "owner_user_id": self.owner_user_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Tower":
        return cls(**data)


@dataclass
class GameSession:
    session_id: str
    mode: str = "normal"
    wave: int = 0
    turn: int = 0
    gold: int = 200
    carrot_hp: int = 10
    max_carrot_hp: int = 10
    towers: Dict[int, Tower] = field(default_factory=dict)
    enemies: List[Enemy] = field(default_factory=list)
    status: str = "idle"
    created_by: str = ""
    updated_at: str = ""
    total_kills: int = 0
    total_gold_earned: int = 0
    total_heals: int = 0

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
        self.spawn_wave(self.wave)
        return f"游戏开始，模式：{self.mode}，第 1 波敌人已出现！"

    def spawn_wave(self, wave: int) -> None:
        self.enemies = spawn_enemies_for_wave(wave, endless=(self.mode == "endless"), prefix="single")

    def build_tower(self, tower_type: str, position: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "当前没有进行中的游戏，请先使用 /萝卜开始"

        if tower_type not in TOWER_TEMPLATES:
            return False, "未知塔类型，可用：弓箭 / 炮塔 / 冰塔 / 治疗塔"

        if position < 1 or position > MAP_LENGTH:
            return False, f"位置必须在 1 ~ {MAP_LENGTH} 之间"

        if position in self.towers:
            return False, "该位置已经有防御塔了"

        cost = TOWER_TEMPLATES[tower_type]["cost"]
        if self.gold < cost:
            return False, f"���币不足，需要 {cost}，当前仅有 {self.gold}"

        self.gold -= cost
        self.towers[position] = Tower(tower_type=tower_type, position=position, owner_user_id=self.created_by)
        return True, f"已在 {position} 号位建造 {TOWER_TEMPLATES[tower_type]['name']}，消耗 {cost} 金币"

    def upgrade_tower(self, position: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "当前没有进行中的游戏"

        tower = self.towers.get(position)
        if not tower:
            return False, "该位置没有防御塔"

        if tower.level >= 5:
            return False, "该防御塔已满级"

        cost = tower.upgrade_cost
        if self.gold < cost:
            return False, f"金币不足，升级需要 {cost}，当前仅有 {self.gold}"

        self.gold -= cost
        tower.level += 1
        return True, f"{position} 号位 {tower.name} 已升级到 Lv{tower.level}，消耗 {cost} 金币"

    def remove_tower(self, position: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "当前没有进行中的游戏"

        tower = self.towers.get(position)
        if not tower:
            return False, "该位置没有防御塔"

        refund = int((tower.cfg["cost"] + (tower.level - 1) * tower.cfg["upgrade_cost"]) * 0.5)
        self.gold += refund
        del self.towers[position]
        return True, f"已拆除 {position} 号位 {tower.name}，返还 {refund} 金币"

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
        logs: List[str] = [f"模式：{self.mode} | 第 {self.wave} 波 - 第 {self.turn} 回合"]

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

        for pos in sorted(self.towers.keys()):
            tower = self.towers[pos]

            if tower.kind == "heal":
                logs.append(f"{tower.name}({pos},Lv{tower.level}) 待机治疗")
                continue

            targets = [e for e in self.enemies if e.alive and abs(e.pos - tower.position) <= tower.range]
            targets.sort(key=lambda x: (-x.pos, x.hp))

            if not targets:
                logs.append(f"{tower.name}({pos}) 未找到目标")
                continue

            main_target = targets[0]
            dmg = max(1, tower.atk - main_target.armor)
            main_target.hp -= dmg
            main_target.last_hit_owner = tower.owner_user_id
            logs.append(f"{tower.name}({pos},Lv{tower.level}) 攻击 {main_target.name}，造成 {dmg} 伤害")

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
        for enemy in self.enemies:
            if not enemy.alive:
                continue

            old_pos = enemy.pos
            enemy.pos += enemy.get_actual_speed()

            if enemy.pos > MAP_LENGTH:
                enemy.alive = False
                self.carrot_hp -= 1
                logs.append(f"{enemy.name} 从位置 {old_pos} 冲到了萝卜！萝卜生命 -1")
            else:
                logs.append(f"{enemy.name} 从位置 {old_pos} 前进到位置 {enemy.pos}")
        return logs

    def _heal_phase(self) -> List[str]:
        logs: List[str] = []
        total_heal = 0
        for pos in sorted(self.towers.keys()):
            tower = self.towers[pos]
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
            "towers": {str(k): v.to_dict() for k, v in self.towers.items()},
            "enemies": [e.to_dict() for e in self.enemies],
            "status": self.status,
            "created_by": self.created_by,
            "updated_at": self.updated_at,
            "total_kills": self.total_kills,
            "total_gold_earned": self.total_gold_earned,
            "total_heals": self.total_heals,
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
        session.towers = {int(k): Tower.from_dict(v) for k, v in data.get("towers", {}).items()}
        session.enemies = [Enemy.from_dict(e) for e in data.get("enemies", [])]
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
    towers: Dict[int, Tower] = field(default_factory=dict)
    enemies: List[Enemy] = field(default_factory=list)
    players: Dict[str, CoopPlayer] = field(default_factory=dict)
    status: str = "waiting"
    host_user_id: str = ""
    updated_at: str = ""
    total_kills: int = 0
    total_gold_earned: int = 0
    total_heals: int = 0

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

        return True, f"合作模式已开始！当前人数：{len(self.players)}，第 1 波敌人已出现"

    def build_tower(self, user_id: str, tower_type: str, position: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "合作游戏尚未开始"
        player = self.players.get(user_id)
        if not player:
            return False, "你不在当前合作房间中"
        if tower_type not in TOWER_TEMPLATES:
            return False, "未知塔类型，可用：弓箭 / 炮塔 / 冰塔 / 治疗塔"
        if position < 1 or position > MAP_LENGTH:
            return False, f"位置必须在 1 ~ {MAP_LENGTH} 之间"
        if position in self.towers:
            return False, "该位置已经有防御塔了"

        cost = TOWER_TEMPLATES[tower_type]["cost"]
        if player.gold < cost:
            return False, f"你的金币不足，需要 {cost}，当前仅有 {player.gold}"

        player.gold -= cost
        player.build_count += 1
        player.gold_spent += cost
        self.towers[position] = Tower(tower_type=tower_type, position=position, level=1, owner_user_id=user_id)
        return True, f"你已在 {position} 号位建造 {TOWER_TEMPLATES[tower_type]['name']}，消耗 {cost} 金币"

    def upgrade_tower(self, user_id: str, position: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "合作游戏尚未开始"
        player = self.players.get(user_id)
        if not player:
            return False, "你不在当前合作房间中"

        tower = self.towers.get(position)
        if not tower:
            return False, "该位置没有防御塔"
        if tower.level >= 5:
            return False, "该防御塔已满级"

        cost = tower.upgrade_cost
        if player.gold < cost:
            return False, f"你的金币不足，升级需要 {cost}，当前仅有 {player.gold}"

        player.gold -= cost
        player.upgrade_count += 1
        player.gold_spent += cost
        tower.level += 1
        return True, f"你将 {position} 号位 {tower.name} 升级到 Lv{tower.level}，消耗 {cost} 金币"

    def remove_tower(self, user_id: str, position: int) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "合作游戏尚未开始"
        player = self.players.get(user_id)
        if not player:
            return False, "你不在当前合作房间中"

        tower = self.towers.get(position)
        if not tower:
            return False, "该位置没有防御塔"

        refund = int((tower.cfg["cost"] + (tower.level - 1) * tower.cfg["upgrade_cost"]) * 0.5)
        player.gold += refund
        player.remove_count += 1
        del self.towers[position]
        return True, f"你拆除了 {position} 号位 {tower.name}，返还 {refund} 金币"

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
        logs: List[str] = [f"【合作模式】第 {self.wave} 波 - 第 {self.turn} 回合"]
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

        for pos in sorted(self.towers.keys()):
            tower = self.towers[pos]
            if tower.kind == "heal":
                logs.append(f"{tower.name}({pos},Lv{tower.level}) 待机治疗")
                continue

            targets = [e for e in self.enemies if e.alive and abs(e.pos - tower.position) <= tower.range]
            targets.sort(key=lambda x: (-x.pos, x.hp))
            if not targets:
                logs.append(f"{tower.name}({pos}) 未找到目标")
                continue

            main_target = targets[0]
            dmg = max(1, tower.atk - main_target.armor)
            main_target.hp -= dmg
            main_target.last_hit_owner = tower.owner_user_id
            owner_name = self._player_name(tower.owner_user_id)
            logs.append(f"{tower.name}({pos},Lv{tower.level})[{owner_name}] 攻击 {main_target.name}，造成 {dmg} 伤害")

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
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            old_pos = enemy.pos
            enemy.pos += enemy.get_actual_speed()
            if enemy.pos > MAP_LENGTH:
                enemy.alive = False
                self.carrot_hp -= 1
                logs.append(f"{enemy.name} 从位置 {old_pos} 冲到了萝卜！萝卜生命 -1")
            else:
                logs.append(f"{enemy.name} 从位置 {old_pos} 前进到位置 {enemy.pos}")
        return logs

    def _heal_phase(self) -> List[str]:
        logs: List[str] = []
        total_heal = 0
        owner_heal: Dict[str, int] = {}
        for pos in sorted(self.towers.keys()):
            tower = self.towers[pos]
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
            "towers": {str(k): v.to_dict() for k, v in self.towers.items()},
            "enemies": [e.to_dict() for e in self.enemies],
            "players": {uid: p.to_dict() for uid, p in self.players.items()},
            "status": self.status,
            "host_user_id": self.host_user_id,
            "updated_at": self.updated_at,
            "total_kills": self.total_kills,
            "total_gold_earned": self.total_gold_earned,
            "total_heals": self.total_heals,
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
        session.towers = {int(k): Tower.from_dict(v) for k, v in data.get("towers", {}).items()}
        session.enemies = [Enemy.from_dict(e) for e in data.get("enemies", [])]
        session.players = {uid: CoopPlayer.from_dict(p) for uid, p in data.get("players", {}).items()}
        return session


@dataclass
class PvpPlayerState:
    user_id: str
    nickname: str = ""
    wave: int = 1
    turn: int = 0
    gold: int = 200
    carrot_hp: int = 10
    max_carrot_hp: int = 10
    towers: Dict[int, Tower] = field(default_factory=dict)
    enemies: List[Enemy] = field(default_factory=list)
    status: str = "alive"  # alive / lose / clear
    total_kills: int = 0
    total_gold_earned: int = 0
    total_heals: int = 0
    reached_wave: int = 1
    reached_turn: int = 0

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "wave": self.wave,
            "turn": self.turn,
            "gold": self.gold,
            "carrot_hp": self.carrot_hp,
            "max_carrot_hp": self.max_carrot_hp,
            "towers": {str(k): v.to_dict() for k, v in self.towers.items()},
            "enemies": [e.to_dict() for e in self.enemies],
            "status": self.status,
            "total_kills": self.total_kills,
            "total_gold_earned": self.total_gold_earned,
            "total_heals": self.total_heals,
            "reached_wave": self.reached_wave,
            "reached_turn": self.reached_turn,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PvpPlayerState":
        player = cls(
            user_id=data["user_id"],
            nickname=data.get("nickname", ""),
            wave=data.get("wave", 1),
            turn=data.get("turn", 0),
            gold=data.get("gold", 200),
            carrot_hp=data.get("carrot_hp", 10),
            max_carrot_hp=data.get("max_carrot_hp", 10),
            status=data.get("status", "alive"),
            total_kills=data.get("total_kills", 0),
            total_gold_earned=data.get("total_gold_earned", 0),
            total_heals=data.get("total_heals", 0),
            reached_wave=data.get("reached_wave", 1),
            reached_turn=data.get("reached_turn", 0),
        )
        player.towers = {int(k): Tower.from_dict(v) for k, v in data.get("towers", {}).items()}
        player.enemies = [Enemy.from_dict(e) for e in data.get("enemies", [])]
        return player


@dataclass
class PvpGameSession:
    session_id: str
    host_user_id: str = ""
    status: str = "waiting"  # waiting / running / finished
    wave: int = 0
    turn: int = 0
    players: Dict[str, PvpPlayerState] = field(default_factory=dict)
    updated_at: str = ""

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
        self.wave = 1
        self.turn = 0

        for pid, player in self.players.items():
            player.wave = 1
            player.turn = 0
            player.gold = 200
            player.carrot_hp = 10
            player.max_carrot_hp = 10
            player.towers = {}
            player.enemies = spawn_enemies_for_wave(1, prefix=f"pvp-{pid}")
            player.status = "alive"
            player.total_kills = 0
            player.total_gold_earned = 0
            player.total_heals = 0
            player.reached_wave = 1
            player.reached_turn = 0

        return True, f"PVP 已开始！当前人数：{len(self.players)}，所有玩家进入第 1 波"

    def build_tower(self, user_id: str, tower_type: str, position: int) -> Tuple[bool, str]:
        player = self.players.get(user_id)
        if self.status != "running":
            return False, "PVP 尚未开始"
        if not player:
            return False, "你不在当前 PVP 房间中"
        if player.status != "alive":
            return False, "你已出局，不能继续操作"
        if tower_type not in TOWER_TEMPLATES:
            return False, "未知塔类型，可用：弓箭 / 炮塔 / 冰塔 / 治疗塔"
        if position < 1 or position > MAP_LENGTH:
            return False, f"位置必须在 1 ~ {MAP_LENGTH} 之间"
        if position in player.towers:
            return False, "该位置已经有防御塔了"

        cost = TOWER_TEMPLATES[tower_type]["cost"]
        if player.gold < cost:
            return False, f"你的金币不足，需要 {cost}，当前仅有 {player.gold}"

        player.gold -= cost
        player.towers[position] = Tower(tower_type=tower_type, position=position, level=1, owner_user_id=user_id)
        return True, f"你已在 {position} 号位建造 {TOWER_TEMPLATES[tower_type]['name']}，消耗 {cost} 金币"

    def upgrade_tower(self, user_id: str, position: int) -> Tuple[bool, str]:
        player = self.players.get(user_id)
        if self.status != "running":
            return False, "PVP 尚未开始"
        if not player:
            return False, "你不在当前 PVP 房间中"
        if player.status != "alive":
            return False, "你已出局，不能继续操作"

        tower = player.towers.get(position)
        if not tower:
            return False, "该位置没有防御塔"
        if tower.level >= 5:
            return False, "该防御塔已满级"

        cost = tower.upgrade_cost
        if player.gold < cost:
            return False, f"你的金币不足，升级需要 {cost}，当前仅有 {player.gold}"

        player.gold -= cost
        tower.level += 1
        return True, f"你将 {position} 号位 {tower.name} 升级到 Lv{tower.level}，消耗 {cost} 金币"

    def remove_tower(self, user_id: str, position: int) -> Tuple[bool, str]:
        player = self.players.get(user_id)
        if self.status != "running":
            return False, "PVP 尚未开始"
        if not player:
            return False, "你不在当前 PVP 房间中"
        if player.status != "alive":
            return False, "你已出局，不能继续操作"

        tower = player.towers.get(position)
        if not tower:
            return False, "该位置没有防御塔"

        refund = int((tower.cfg["cost"] + (tower.level - 1) * tower.cfg["upgrade_cost"]) * 0.5)
        player.gold += refund
        del player.towers[position]
        return True, f"你拆除了 {position} 号位 {tower.name}，返还 {refund} 金币"

    def step_turn(self, user_id: str) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "PVP 尚未开始"
        if user_id != self.host_user_id:
            return False, "只有房主可以推进回合"

        alive_players = [p for p in self.players.values() if p.status == "alive"]
        if not alive_players:
            self.status = "finished"
            return True, "所有玩家都已出局，PVP 结束"

        self.turn += 1
        logs = [f"【PVP】第 {self.wave} 波 - 第 {self.turn} 回合"]

        for player in alive_players:
            player.turn += 1
            player.reached_wave = max(player.reached_wave, self.wave)
            player.reached_turn = max(player.reached_turn, player.turn)
            logs.append(f"—— {player.nickname or player.user_id} ——")
            logs.extend(self._step_one_player(player))

        self._update_pvp_result()
        return True, "\n".join(logs)

    def next_wave(self, user_id: str) -> Tuple[bool, str]:
        if self.status != "running":
            return False, "PVP 尚未开始"
        if user_id != self.host_user_id:
            return False, "只有房主可以推进到下一波"

        alive_players = [p for p in self.players.values() if p.status == "alive"]
        if not alive_players:
            self.status = "finished"
            return True, "所有玩家都已出局，PVP 结束"

        not_cleared = [p for p in alive_players if any(e.alive for e in p.enemies)]
        if not_cleared:
            names = "、".join((p.nickname or p.user_id) for p in not_cleared[:4])
            return False, f"还有玩家未清空当前波：{names}"

        if self.wave >= MAX_WAVE:
            self.status = "finished"
            for p in alive_players:
                p.status = "clear"
            return True, "所有玩家都完成了最终波，PVP 结束"

        self.wave += 1
        self.turn = 0

        for p in alive_players:
            p.wave = self.wave
            p.turn = 0
            p.enemies = spawn_enemies_for_wave(self.wave, prefix=f"pvp-{p.user_id}")
            p.reached_wave = max(p.reached_wave, self.wave)

        return True, f"PVP 进入第 {self.wave} 波"

    def _step_one_player(self, player: PvpPlayerState) -> List[str]:
        logs: List[str] = []

        if not any(e.alive for e in player.enemies):
            logs.append("当前没有敌人，可等待房主推进下一波")
            return logs

        logs.extend(self._tower_attack_phase_for_player(player))

        dead_rewards = 0
        dead_count = 0
        for enemy in player.enemies:
            if enemy.alive and enemy.hp <= 0:
                enemy.alive = False
                dead_rewards += enemy.reward
                dead_count += 1
                logs.append(f"{enemy.name} 被击败，获得 {enemy.reward} 金币")

        if dead_rewards > 0:
            player.gold += dead_rewards
            player.total_gold_earned += dead_rewards
            player.total_kills += dead_count

        if any(e.alive for e in player.enemies):
            logs.extend(self._enemy_move_phase_for_player(player))

        logs.extend(self._heal_phase_for_player(player))

        for enemy in player.enemies:
            if enemy.alive and enemy.slow_turns > 0:
                enemy.slow_turns -= 1

        if player.carrot_hp <= 0:
            player.status = "lose"
            logs.append("你的萝卜生命归零，你已出局！")
        elif not any(e.alive for e in player.enemies):
            logs.append("你已清空当前波，等待房主推进下一波")

        return logs

    def _tower_attack_phase_for_player(self, player: PvpPlayerState) -> List[str]:
        logs: List[str] = []
        if not player.towers:
            return ["本回合没有防御塔出手"]

        for pos in sorted(player.towers.keys()):
            tower = player.towers[pos]

            if tower.kind == "heal":
                logs.append(f"{tower.name}({pos},Lv{tower.level}) 待机治疗")
                continue

            targets = [e for e in player.enemies if e.alive and abs(e.pos - tower.position) <= tower.range]
            targets.sort(key=lambda x: (-x.pos, x.hp))
            if not targets:
                logs.append(f"{tower.name}({pos}) 未找到目标")
                continue

            main_target = targets[0]
            dmg = max(1, tower.atk - main_target.armor)
            main_target.hp -= dmg
            logs.append(f"{tower.name}({pos},Lv{tower.level}) 攻击 {main_target.name}，造成 {dmg} 伤害")

            if tower.kind == "splash":
                for extra in targets[1:3]:
                    splash = max(1, tower.atk // 2 - extra.armor)
                    extra.hp -= splash
                    logs.append(f"  ↳ 溅射到 {extra.name}，造成 {splash} 伤害")
            elif tower.kind == "slow":
                main_target.slow_turns = max(main_target.slow_turns, 2)
                logs.append(f"  ↳ {main_target.name} 被减速 2 回合")
        return logs

    def _enemy_move_phase_for_player(self, player: PvpPlayerState) -> List[str]:
        logs: List[str] = []
        for enemy in player.enemies:
            if not enemy.alive:
                continue
            old_pos = enemy.pos
            enemy.pos += enemy.get_actual_speed()
            if enemy.pos > MAP_LENGTH:
                enemy.alive = False
                player.carrot_hp -= 1
                logs.append(f"{enemy.name} 从位置 {old_pos} 冲到了你的萝卜！生命 -1")
            else:
                logs.append(f"{enemy.name} 从位置 {old_pos} 前进到位置 {enemy.pos}")
        return logs

    def _heal_phase_for_player(self, player: PvpPlayerState) -> List[str]:
        logs: List[str] = []
        total_heal = 0
        for pos in sorted(player.towers.keys()):
            tower = player.towers[pos]
            if tower.kind == "heal":
                total_heal += tower.heal_amount

        if total_heal <= 0:
            return logs
        if player.carrot_hp >= player.max_carrot_hp:
            logs.append("治疗塔尝试治疗，但你的萝卜生命已满")
            return logs

        before = player.carrot_hp
        player.carrot_hp = min(player.max_carrot_hp, player.carrot_hp + total_heal)
        actual = player.carrot_hp - before
        if actual > 0:
            player.total_heals += actual
            logs.append(f"治疗塔共为你的萝卜恢复了 {actual} 点生命")
        return logs

    def _update_pvp_result(self):
        alive_players = [p for p in self.players.values() if p.status == "alive"]
        if len(alive_players) <= 1:
            self.status = "finished"

    def get_rankings(self) -> List[dict]:
        rows = []
        for player in self.players.values():
            rows.append(
                {
                    "user_id": player.user_id,
                    "nickname": player.nickname,
                    "status": player.status,
                    "reached_wave": player.reached_wave,
                    "reached_turn": player.reached_turn,
                    "total_kills": player.total_kills,
                    "carrot_hp": player.carrot_hp,
                    "gold": player.gold,
                    "total_gold_earned": player.total_gold_earned,
                    "total_heals": player.total_heals,
                }
            )

        def status_score(s: str) -> int:
            if s == "alive":
                return 3
            if s == "clear":
                return 2
            return 1

        rows.sort(
            key=lambda x: (
                -status_score(x["status"]),
                -x["reached_wave"],
                -x["reached_turn"],
                -x["total_kills"],
                -x["carrot_hp"],
            )
        )
        return rows

    def get_player(self, user_id: str) -> Optional[PvpPlayerState]:
        return self.players.get(user_id)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "host_user_id": self.host_user_id,
            "status": self.status,
            "wave": self.wave,
            "turn": self.turn,
            "players": {uid: p.to_dict() for uid, p in self.players.items()},
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PvpGameSession":
        session = cls(
            session_id=data["session_id"],
            host_user_id=data.get("host_user_id", ""),
            status=data.get("status", "waiting"),
            wave=data.get("wave", 0),
            turn=data.get("turn", 0),
            updated_at=data.get("updated_at", ""),
        )
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
        return True, "合作房间已创建，你已成为房主", room

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
