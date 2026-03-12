from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any, List


class JsonStorage:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "data"
        self.sessions_file = self.data_dir / "sessions.json"
        self.coop_sessions_file = self.data_dir / "coop_sessions.json"
        self.pvp_sessions_file = self.data_dir / "pvp_sessions.json"
        self.leaderboard_file = self.data_dir / "leaderboard.json"
        self._ensure_files()

    def _ensure_files(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)

        for path in [self.sessions_file, self.coop_sessions_file, self.pvp_sessions_file]:
            if not path.exists():
                path.write_text("{}", encoding="utf-8")

        if not self.leaderboard_file.exists():
            self.leaderboard_file.write_text(
                json.dumps({"players": {}, "rooms": {}}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _read_json(self, path: Path, default: Any):
        try:
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                return default
            return json.loads(text)
        except Exception:
            return default

    def _write_json(self, path: Path, data: Any):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_sessions(self) -> dict:
        return self._read_json(self.sessions_file, {})

    def save_sessions(self, sessions: dict):
        self._write_json(self.sessions_file, sessions)

    def load_coop_sessions(self) -> dict:
        return self._read_json(self.coop_sessions_file, {})

    def save_coop_sessions(self, sessions: dict):
        self._write_json(self.coop_sessions_file, sessions)

    def load_pvp_sessions(self) -> dict:
        return self._read_json(self.pvp_sessions_file, {})

    def save_pvp_sessions(self, sessions: dict):
        self._write_json(self.pvp_sessions_file, sessions)

    def load_leaderboard(self) -> dict:
        board = self._read_json(self.leaderboard_file, {"players": {}, "rooms": {}})
        if "players" not in board or not isinstance(board["players"], dict):
            board["players"] = {}
        if "rooms" not in board or not isinstance(board["rooms"], dict):
            board["rooms"] = {}
        return board

    def save_leaderboard(self, leaderboard: dict):
        if "players" not in leaderboard or not isinstance(leaderboard["players"], dict):
            leaderboard["players"] = {}
        if "rooms" not in leaderboard or not isinstance(leaderboard["rooms"], dict):
            leaderboard["rooms"] = {}
        self._write_json(self.leaderboard_file, leaderboard)

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
    ):
        board = self.load_leaderboard()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        user_id = str(user_id or "unknown")
        room_id = str(room_id or "unknown")
        result = result if result in ("win", "lose") else "lose"
        mode = mode if mode in ("normal", "endless") else "normal"

        if user_id not in board["players"]:
            board["players"][user_id] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "best_wave": 0,
                "best_normal_wave": 0,
                "best_endless_wave": 0,
                "best_turn_survived": 0,
                "total_kills": 0,
                "total_gold_earned": 0,
                "total_heals": 0,
                "last_result": "",
                "last_play_at": "",
            }

        player = board["players"][user_id]
        player["games"] += 1
        if result == "win":
            player["wins"] += 1
        else:
            player["losses"] += 1

        player["best_wave"] = max(player.get("best_wave", 0), wave)
        if mode == "normal":
            player["best_normal_wave"] = max(player.get("best_normal_wave", 0), wave)
        else:
            player["best_endless_wave"] = max(player.get("best_endless_wave", 0), wave)

        player["best_turn_survived"] = max(player.get("best_turn_survived", 0), turns)
        player["total_kills"] += kills
        player["total_gold_earned"] += gold_earned
        player["total_heals"] += heals
        player["last_result"] = result
        player["last_play_at"] = now

        if room_id not in board["rooms"]:
            board["rooms"][room_id] = {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "best_wave": 0,
                "best_normal_wave": 0,
                "best_endless_wave": 0,
                "best_turn_survived": 0,
                "total_kills": 0,
                "total_gold_earned": 0,
                "total_heals": 0,
                "last_play_at": "",
            }

        room = board["rooms"][room_id]
        room["games"] += 1
        if result == "win":
            room["wins"] += 1
        else:
            room["losses"] += 1

        room["best_wave"] = max(room.get("best_wave", 0), wave)
        if mode == "normal":
            room["best_normal_wave"] = max(room.get("best_normal_wave", 0), wave)
        else:
            room["best_endless_wave"] = max(room.get("best_endless_wave", 0), wave)

        room["best_turn_survived"] = max(room.get("best_turn_survived", 0), turns)
        room["total_kills"] += kills
        room["total_gold_earned"] += gold_earned
        room["total_heals"] += heals
        room["last_play_at"] = now

        self.save_leaderboard(board)

    def get_player_rankings(self) -> List[dict]:
        board = self.load_leaderboard()
        players = []

        for user_id, stats in board.get("players", {}).items():
            games = int(stats.get("games", 0))
            wins = int(stats.get("wins", 0))
            losses = int(stats.get("losses", 0))
            best_wave = int(stats.get("best_wave", 0))
            best_normal_wave = int(stats.get("best_normal_wave", 0))
            best_endless_wave = int(stats.get("best_endless_wave", 0))
            best_turn_survived = int(stats.get("best_turn_survived", 0))
            total_kills = int(stats.get("total_kills", 0))
            total_gold_earned = int(stats.get("total_gold_earned", 0))
            total_heals = int(stats.get("total_heals", 0))
            last_result = stats.get("last_result", "")
            last_play_at = stats.get("last_play_at", "")
            win_rate = round((wins / games * 100), 2) if games > 0 else 0.0

            players.append(
                {
                    "user_id": user_id,
                    "games": games,
                    "wins": wins,
                    "losses": losses,
                    "best_wave": best_wave,
                    "best_normal_wave": best_normal_wave,
                    "best_endless_wave": best_endless_wave,
                    "best_turn_survived": best_turn_survived,
                    "total_kills": total_kills,
                    "total_gold_earned": total_gold_earned,
                    "total_heals": total_heals,
                    "last_result": last_result,
                    "last_play_at": last_play_at,
                    "win_rate": win_rate,
                }
            )

        players.sort(
            key=lambda x: (
                -x["wins"],
                -x["best_normal_wave"],
                -x["best_endless_wave"],
                -x["win_rate"],
                -x["total_kills"],
            )
        )
        return players

    def get_endless_rankings(self) -> List[dict]:
        rankings = self.get_player_rankings()
        rankings.sort(
            key=lambda x: (
                -x["best_endless_wave"],
                -x["best_turn_survived"],
                -x["total_kills"],
                -x["total_gold_earned"],
            )
        )
        return rankings

    def get_room_rankings(self) -> List[dict]:
        board = self.load_leaderboard()
        rooms = []

        for room_id, stats in board.get("rooms", {}).items():
            games = int(stats.get("games", 0))
            wins = int(stats.get("wins", 0))
            losses = int(stats.get("losses", 0))
            best_wave = int(stats.get("best_wave", 0))
            best_normal_wave = int(stats.get("best_normal_wave", 0))
            best_endless_wave = int(stats.get("best_endless_wave", 0))
            best_turn_survived = int(stats.get("best_turn_survived", 0))
            total_kills = int(stats.get("total_kills", 0))
            total_gold_earned = int(stats.get("total_gold_earned", 0))
            total_heals = int(stats.get("total_heals", 0))
            last_play_at = stats.get("last_play_at", "")
            win_rate = round((wins / games * 100), 2) if games > 0 else 0.0

            rooms.append(
                {
                    "room_id": room_id,
                    "games": games,
                    "wins": wins,
                    "losses": losses,
                    "best_wave": best_wave,
                    "best_normal_wave": best_normal_wave,
                    "best_endless_wave": best_endless_wave,
                    "best_turn_survived": best_turn_survived,
                    "total_kills": total_kills,
                    "total_gold_earned": total_gold_earned,
                    "total_heals": total_heals,
                    "last_play_at": last_play_at,
                    "win_rate": win_rate,
                }
            )

        rooms.sort(
            key=lambda x: (
                -x["wins"],
                -x["best_normal_wave"],
                -x["best_endless_wave"],
                -x["games"],
            )
        )
        return rooms

    def get_player_stats(self, user_id: str) -> dict:
        board = self.load_leaderboard()
        return board.get("players", {}).get(str(user_id), {})
