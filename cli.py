import json
import sys
from pathlib import Path

from gu_package.storage import StorageManager, load_env, read_config, save_config, save_env


def print_json(data):
    print(json.dumps(data, indent=2))


def main() -> None:
    base_dir = Path.cwd()
    env = load_env(base_dir / ".env")
    config = read_config(base_dir / "dbs.json")
    args = sys.argv[1:]

    if not args or args[0] in {"-h", "--help", "help"}:
        print("usage: gu <token|name|repo|sync|db|dbs|config> [arguments]")
        print("")
        print("Examples:")
        print("  gu token set MY_TOKEN")
        print("  gu name set MY_NAME")
        print("  gu repo set MY_REPO")
        print("  gu db create users")
        print("  gu db update users email=test@example.com")
        print("  gu db get users")
        print("  gu sync")
        return

    command = args[0].lower()

    if command == "token":
        if len(args) >= 3 and args[1].lower() == "set":
            env["GITHUB_TOKEN"] = args[2]
            save_env(base_dir / ".env", env)
            print("token set")
        elif len(args) == 2 and args[1].lower() == "get":
            print(env.get("GITHUB_TOKEN", ""))
        elif len(args) == 2:
            env["GITHUB_TOKEN"] = args[1]
            save_env(base_dir / ".env", env)
            print("token set")
        else:
            print(env.get("GITHUB_TOKEN", ""))
        return

    if command == "name":
        if len(args) >= 3 and args[1].lower() == "set":
            env["GITHUB_USERNAME"] = args[2]
            save_env(base_dir / ".env", env)
            print("name set")
        elif len(args) == 2 and args[1].lower() == "get":
            print(env.get("GITHUB_USERNAME", ""))
        elif len(args) == 2:
            env["GITHUB_USERNAME"] = args[1]
            save_env(base_dir / ".env", env)
            print("name set")
        else:
            print(env.get("GITHUB_USERNAME", ""))
        return

    if command == "repo":
        if len(args) >= 3 and args[1].lower() == "set":
            env["GITHUB_REPOSITORY"] = args[2]
            save_env(base_dir / ".env", env)
            print("repo set")
        elif len(args) == 2 and args[1].lower() == "get":
            print(env.get("GITHUB_REPOSITORY", ""))
        elif len(args) == 2:
            env["GITHUB_REPOSITORY"] = args[1]
            save_env(base_dir / ".env", env)
            print("repo set")
        else:
            print(env.get("GITHUB_REPOSITORY", ""))
        return

    if command == "sync":
        manager = StorageManager(base_dir=base_dir, repo_name=env.get("GITHUB_REPOSITORY", "default-repo"))
        result = manager.sync_repo(
            github_token=env.get("GITHUB_TOKEN", ""),
            github_username=env.get("GITHUB_USERNAME", ""),
            github_repository=env.get("GITHUB_REPOSITORY", "default-repo"),
        )
        print_json(result)
        return

    if command == "db":
        manager = StorageManager(base_dir=base_dir, repo_name=env.get("GITHUB_REPOSITORY", "default-repo"))
        if len(args) == 1 or (len(args) > 1 and args[1].lower() in {"list", "ls"}):
            print_json(manager.list_dbs())
            return
        if len(args) >= 2 and args[1].lower() == "create":
            if len(args) < 3:
                raise SystemExit("usage: db create <name>")
            result = manager.create_db(args[2])
            config.setdefault("dbs", [])
            if args[2] not in config["dbs"]:
                config["dbs"].append(args[2])
            save_config(base_dir / "dbs.json", config)
            print_json(result)
            return
        if len(args) >= 2 and args[1].lower() == "delete":
            if len(args) < 3:
                raise SystemExit("usage: db delete <name>")
            result = manager.delete_db(args[2])
            config.setdefault("dbs", [])
            config["dbs"] = [name for name in config["dbs"] if name != args[2]]
            save_config(base_dir / "dbs.json", config)
            print_json(result)
            return
        if len(args) >= 2 and args[1].lower() == "update":
            if len(args) < 4:
                raise SystemExit("usage: db update <name> <key=value>")
            parts = args[3].split("=", 1)
            if len(parts) != 2:
                raise SystemExit("usage: db update <name> <key=value>")
            print_json(manager.write_db_value(args[2], parts[0], parts[1]))
            return
        if len(args) >= 2 and args[1].lower() == "get":
            if len(args) < 3:
                print_json(manager.list_dbs())
                return
            print_json(manager.get_db(args[2]))
            return
        if len(args) >= 2:
            print_json(manager.get_db(args[1]))
            return
        print_json(manager.list_dbs())
        return

    if command == "dbs":
        print_json(read_config(base_dir / "dbs.json"))
        return

    if command == "config":
        if len(args) == 1:
            print_json(config)
            return
        if len(args) >= 3 and args[1].lower() == "set":
            config[args[2]] = args[3] if len(args) > 3 else ""
            save_config(base_dir / "dbs.json", config)
            print("config updated")
            return
        if len(args) >= 2:
            print(config.get(args[1], ""))
            return
        print_json(config)
        return

    print("unknown command")


if __name__ == "__main__":
    main()
