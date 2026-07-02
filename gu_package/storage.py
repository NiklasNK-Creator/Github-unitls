from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class StorageManager:
    def __init__(
        self,
        base_dir: Optional[Path | str] = None,
        repo_name: Optional[str] = None,
        chunk_limit_bytes: int = 100 * 1024 * 1024,
        repo_limit_bytes: int = 1024 * 1024 * 1024,
    ) -> None:
        start_path = Path(base_dir or Path.cwd()).resolve()
        current = start_path
        while True:
            if (current / ".env").exists() or (current / "dbs.json").exists() or (current / ".git").exists():
                self.base_dir = current
                break
            if current.parent == current:
                self.base_dir = start_path
                break
            current = current.parent
        self.repo_name = repo_name or os.getenv("GITHUB_REPOSITORY", "default-repo")
        self.chunk_limit_bytes = chunk_limit_bytes
        self.repo_limit_bytes = repo_limit_bytes
        self.repo_dir = self.base_dir / self.repo_name
        self.repo_dir.mkdir(parents=True, exist_ok=True)

    def _dir_size(self, path: Path) -> int:
        if not path.exists():
            return 0
        return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())

    def _resolve_repo_dir(self) -> Path:
        current = self.repo_dir
        if current.exists() and self._dir_size(current) < self.repo_limit_bytes:
            return current

        index = 1
        while True:
            candidate = self.base_dir / f"{self.repo_name}-{index}"
            if not candidate.exists():
                candidate.mkdir(parents=True, exist_ok=True)
                self.repo_dir = candidate
                return candidate
            if self._dir_size(candidate) < self.repo_limit_bytes:
                self.repo_dir = candidate
                return candidate
            index += 1

    def _bucket_path(self, db_name: str, bucket_index: int) -> Path:
        return self._resolve_repo_dir() / f"{db_name}-{bucket_index}.json"

    def _bucket_files(self, db_name: str) -> List[Path]:
        repo_dirs = [self.repo_dir]
        index = 1
        while True:
            candidate = self.base_dir / f"{self.repo_name}-{index}"
            if not candidate.exists():
                break
            repo_dirs.append(candidate)
            index += 1

        files: List[Path] = []
        for repo_dir in repo_dirs:
            files.extend(path for path in repo_dir.glob(f"{db_name}-*.json") if path.is_file())
        return sorted(files, key=lambda p: (p.parent.name, int(p.stem.split("-")[-1])))

    def _bucket_size(self, path: Path) -> int:
        try:
            return path.stat().st_size
        except FileNotFoundError:
            return 0

    def _load_bucket(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_bucket(self, path: Path, data: Dict[str, Any]) -> None:
        path.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")

    def _bucket_index_for_size(self, db_name: str, new_value: Any) -> Tuple[int, Dict[str, Any], Path]:
        payload = json.dumps(new_value, ensure_ascii=False)
        size = len(payload.encode("utf-8"))
        existing = self._bucket_files(db_name)
        if not existing:
            return 0, {}, self._bucket_path(db_name, 0)

        for path in existing:
            data = self._load_bucket(path)
            updated = dict(data)
            updated["__tmp__"] = new_value
            updated_size = len(json.dumps(updated, ensure_ascii=False).encode("utf-8"))
            if updated_size <= self.chunk_limit_bytes:
                return int(path.stem.split("-")[-1]), data, path

        next_index = len(existing)
        return next_index, {}, self._bucket_path(db_name, next_index)

    def write_db_value(self, db_name: str, key: str, value: Any) -> Dict[str, Any]:
        bucket_id, data, path = self._bucket_index_for_size(db_name, value)
        data[key] = value
        self._save_bucket(path, data)
        return {"db": db_name, "bucket": bucket_id, "path": str(path)}

    def get_db(self, db_name: str) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for path in self._bucket_files(db_name):
            merged.update(self._load_bucket(path))
        return merged

    def create_db(self, db_name: str) -> Dict[str, Any]:
        path = self._bucket_path(db_name, 0)
        self._save_bucket(path, {})
        return {"db": db_name, "path": str(path)}

    def delete_db(self, db_name: str) -> Dict[str, Any]:
        removed = []
        for path in self._bucket_files(db_name):
            path.unlink(missing_ok=True)
            removed.append(str(path))
        return {"db": db_name, "removed": removed}

    def list_dbs(self) -> List[str]:
        names = set()
        repo_dirs = [self.repo_dir]
        index = 1
        while True:
            candidate = self.base_dir / f"{self.repo_name}-{index}"
            if not candidate.exists():
                break
            repo_dirs.append(candidate)
            index += 1

        for repo_dir in repo_dirs:
            for path in repo_dir.glob("*-*.json"):
                stem = path.stem
                db_name = stem.rsplit("-", 1)[0]
                names.add(db_name)
        return sorted(names)

    def repo_size_bytes(self) -> int:
        return self._dir_size(self._resolve_repo_dir())

    def sync_repo(self, github_token: str, github_username: str, github_repository: str, branch: str = "main") -> Dict[str, Any]:
        repo_url = f"https://github.com/{github_username}/{github_repository}.git"
        auth_repo_url = f"https://{github_token}@github.com/{github_username}/{github_repository}.git"
        repo_path = self.base_dir.resolve()
        git_dir = repo_path / ".git"

        commands = []
        if not git_dir.exists():
            commands.append(["git", "init"])
        commands.extend(
            [
                ["git", "config", "user.name", github_username],
                ["git", "config", "user.email", f"{github_username}@users.noreply.github.com"],
                ["git", "config", "credential.helper", "store"],
            ]
        )

        if subprocess.run(["git", "remote"], cwd=repo_path, capture_output=True, text=True).returncode == 0:
            remote_output = subprocess.run(["git", "remote"], cwd=repo_path, capture_output=True, text=True).stdout
            if "origin" in remote_output.splitlines():
                commands.append(["git", "remote", "remove", "origin"])

        commands.extend(
            [
                ["git", "remote", "add", "origin", auth_repo_url],
                ["git", "add", ".env", "dbs.json", "cli.py", "README.md", "pyproject.toml", "sync.bat", "gu_package", "tests"],
                ["git", "commit", "-m", "Auto-sync update"],
                ["git", "branch", "-M", branch],
                ["git", "push", "-u", "origin", branch],
            ]
        )

        result: Dict[str, Any] = {
            "repo": github_repository,
            "branch": branch,
            "repo_url": repo_url,
            "status": "ok",
            "commands": [],
        }

        try:
            for command in commands:
                subprocess.run(command, cwd=repo_path, check=True, capture_output=True, text=True)
                result["commands"].append(" ".join(command))
        except subprocess.CalledProcessError as exc:
            result["status"] = "error"
            error_text = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            result["error"] = error_text
            if "Authentication failed" in error_text or "Repository not found" in error_text or "could not read Username" in error_text:
                result["login_help"] = (
                    "Use a GitHub PAT in GITHUB_TOKEN and make sure the repo exists. "
                    "If you still get prompted, run: git config --global credential.helper store"
                )
            return result

        return result


def load_env(path: Optional[Path | str] = None) -> Dict[str, str]:
    env_path = Path(path or Path.cwd() / ".env")
    if not env_path.exists():
        return {}
    data: Dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def save_env(path: Optional[Path | str], values: Dict[str, str]) -> None:
    env_path = Path(path or Path.cwd() / ".env")
    env_path.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n", encoding="utf-8")


def read_config(path: Optional[Path | str] = None) -> Dict[str, Any]:
    config_path = Path(path or Path.cwd() / "dbs.json")
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def save_config(path: Optional[Path | str], values: Dict[str, Any]) -> None:
    config_path = Path(path or Path.cwd() / "dbs.json")
    config_path.write_text(json.dumps(values, indent=2), encoding="utf-8")
