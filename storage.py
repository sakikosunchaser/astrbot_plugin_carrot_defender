from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class JsonStorage:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.sessions_file = self.base_dir / "sessions.json"
        self.coop_sessions_file = self.base_dir / "coop_sessions.json"
        self.pvp_sessions_file = self.base_dir / "pvp_sessions.json"
        self.player_stats_file = self.base_dir / "player_stats.json"
        self.room_stats_file = self.base_dir / "room_stats.json"

    def _read_json(self, path: Path, default):
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _write_json(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # -------- 单人会话 --------

    def load_sessions(self) -> dict:
        return self._read_json(self.sessions_file, {})

    def save_sessions(self, data: dict) -> None:
        self._write_json(self.sessions_file, data)

    # -------- 合作会话 --------

    def load_coop_sessions(self) -> dict:
        return self._read_json(self.coop_sessions_file, {})

    def save_coop_sessions(self, data: dict) -> None:
        self._write_json(self.coop_sessions_file, data)

    # -------- PVP 会话 --------

    def load_pvp_sessions(self) -> dict:
        return self._read_json(self.pvp_sessions_file, {})

    def save_pvp_sessions(self, data: dict) -> None:
        self._write_json(self.pvp_sessions_file, data)

    # -------- 战绩 --------

    def _load_player_stats(self) -> Dict[str, dict]:
        return self._read_json(self.player_stats_file, {})

    def _save_player_stats(self, data: Dict[str, dict]) -> None:
        self._write_json(self.player_stats_file, data)

    def _load_room_stats(self) -> Dict[str, dict]:
        return self._read_json(self.room_stats_file, {})

    def _save_room_stats(self, data: Dict[str, dict]) -> None:
        self._write_json(self.room_stats_file, data)

    def record_result(
        self,
        user_id: str,
        room_id: str,
        result: str,
        mode: str,
        wave: int,
        turns: int,
        kills: int,
        gold_earned: int,
        heals: int,
    ) -> None:
        player_stats = self._load_player_stats()
        room_stats = self._load_room_stats()

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user_id not in player_stats:
            player_stats[user_id] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "best_normal_wave": 0,
                "best_endless_wave": 0,
                "best_turn_survived": 0,
                "total_kills": 0,
                "total_gold_earned": 0,
                "total_heals": 0,
                "last_result": "",
                "last_play_at": "",
            }

        if room_id not in room_stats:
            room_stats[room_id] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "best_normal_wave": 0,
                "best_endless_wave": 0,
                "last_play_at": "",
            }

        p = player_stats[user_id]
        r = room_stats[room_id]

        p["games"] += 1
        r["games"] += 1

        if result == "win":
            p["wins"] += 1
            r["wins"] += 1
        else:
            p["losses"] += 1
            r["losses"] += 1

        if mode == "normal":
            p["best_normal_wave"] = max(int(p.get("best_normal_wave", 0)), int(wave))
            r["best_normal_wave"] = max(int(r.get("best_normal_wave", 0)), int(wave))
        elif mode == "endless":
            p["best_endless_wave"] = max(int(p.get("best_endless_wave", 0)), int(wave))
            r["best_endless_wave"] = max(int(r.get("best_endless_wave", 0)), int(wave))

        p["best_turn_survived"] = max(int(p.get("best_turn_survived", 0)), int(turns))
        p["total_kills"] = int(p.get("total_kills", 0)) + int(kills)
        p["total_gold_earned"] = int(p.get("total_gold_earned", 0)) + int(gold_earned)
        p["total_heals"] = int(p.get("total_heals", 0)) + int(heals)
        p["last_result"] = str(result)
        p["last_play_at"] = now_str

        r["last_play_at"] = now_str

        self._save_player_stats(player_stats)
        self._save_room_stats(room_stats)

    def get_player_stats(self, user_id: str) -> dict:
        player_stats = self._load_player_stats()
        return dict(player_stats.get(user_id, {}))

    def get_player_rankings(self) -> list[dict]:
        player_stats = self._load_player_stats()
        rows = []

        for user_id, stats in player_stats.items():
            games = int(stats.get("games", 0))
            wins = int(stats.get("wins", 0))
            win_rate = round((wins / games * 100), 2) if games > 0 else 0.0

            rows.append(
                {
                    "user_id": user_id,
                    "games": games,
                    "wins": wins,
                    "losses": int(stats.get("losses", 0)),
                    "best_normal_wave": int(stats.get("best_normal_wave", 0)),
                    "best_endless_wave": int(stats.get("best_endless_wave", 0)),
                    "best_turn_survived": int(stats.get("best_turn_survived", 0)),
                    "total_kills": int(stats.get("total_kills", 0)),
                    "total_gold_earned": int(stats.get("total_gold_earned", 0)),
                    "total_heals": int(stats.get("total_heals", 0)),
                    "win_rate": win_rate,
                    "last_result": stats.get("last_result", ""),
                    "last_play_at": stats.get("last_play_at", ""),
                }
            )

        rows.sort(
            key=lambda x: (
                -x["wins"],
                -x["win_rate"],
                -x["best_normal_wave"],
                -x["best_endless_wave"],
                -x["total_kills"],
            )
        )
        return rows

    def get_endless_rankings(self) -> list[dict]:
        player_stats = self._load_player_stats()
        rows = []

        for user_id, stats in player_stats.items():
            rows.append(
                {
                    "user_id": user_id,
                    "games": int(stats.get("games", 0)),
                    "wins": int(stats.get("wins", 0)),
                    "losses": int(stats.get("losses", 0)),
                    "best_normal_wave": int(stats.get("best_normal_wave", 0)),
                    "best_endless_wave": int(stats.get("best_endless_wave", 0)),
                    "best_turn_survived": int(stats.get("best_turn_survived", 0)),
                    "total_kills": int(stats.get("total_kills", 0)),
                    "total_gold_earned": int(stats.get("total_gold_earned", 0)),
                    "total_heals": int(stats.get("total_heals", 0)),
                    "last_result": stats.get("last_result", ""),
                    "last_play_at": stats.get("last_play_at", ""),
                }
            )

        rows.sort(
            key=lambda x: (
                -x["best_endless_wave"],
                -x["best_turn_survived"],
                -x["total_kills"],
                -x["total_gold_earned"],
            )
        )
        return rows

    def get_room_rankings(self) -> list[dict]:
        room_stats = self._load_room_stats()
        rows = []

        for room_id, stats in room_stats.items():
            rows.append(
                {
                    "room_id": room_id,
                    "games": int(stats.get("games", 0)),
                    "wins": int(stats.get("wins", 0)),
                    "losses": int(stats.get("losses", 0)),
                    "best_normal_wave": int(stats.get("best_normal_wave", 0)),
                    "best_endless_wave": int(stats.get("best_endless_wave", 0)),
                    "last_play_at": stats.get("last_play_at", ""),
                }
            )

        rows.sort(
            key=lambda x: (
                -x["wins"],
                -x["games"],
                -x["best_normal_wave"],
                -x["best_endless_wave"],
            )
        )
        return rows
