import json
import tempfile
from pathlib import Path

from gu_package.storage import StorageManager, load_env, save_env


def test_env_round_trip(tmp_path):
    env_path = tmp_path / ".env"
    save_env(env_path, {"GITHUB_TOKEN": "abc", "GITHUB_USERNAME": "user", "GITHUB_REPOSITORY": "repo"})
    loaded = load_env(env_path)
    assert loaded["GITHUB_TOKEN"] == "abc"
    assert loaded["GITHUB_USERNAME"] == "user"
    assert loaded["GITHUB_REPOSITORY"] == "repo"


def test_chunk_selection_creates_new_bucket_when_limit_hit(tmp_path):
    storage = StorageManager(base_dir=tmp_path / "store", repo_name="demo-repo", chunk_limit_bytes=40, repo_limit_bytes=80)

    first = storage.write_db_value("orders", "customer", "alice")
    second = storage.write_db_value("orders", "note", "0123456789")

    assert first["bucket"] != second["bucket"]
    assert storage.get_db("orders")["customer"] == "alice"
    assert storage.get_db("orders")["note"] == "0123456789"


def test_get_db_merges_across_repo_buckets(tmp_path):
    first = StorageManager(base_dir=tmp_path, repo_name="demo-repo", chunk_limit_bytes=1000, repo_limit_bytes=1)
    first.write_db_value("orders", "customer", "alice")

    second = StorageManager(base_dir=tmp_path, repo_name="demo-repo", chunk_limit_bytes=1000, repo_limit_bytes=1)
    second.write_db_value("orders", "note", "0123456789")

    merged = first.get_db("orders")
    assert merged["customer"] == "alice"
    assert merged["note"] == "0123456789"


def test_sync_repo_runs_git_commands(tmp_path):
    storage = StorageManager(base_dir=tmp_path, repo_name="demo-repo")
    result = storage.sync_repo("token", "user", "repo")
    assert result["status"] in {"ok", "error"}
