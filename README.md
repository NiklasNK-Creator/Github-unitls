# GU Package

Small cross-language utility to store a GitHub token + repo metadata and sync a small project directory to GitHub.

Key features
- Stores `GITHUB_TOKEN`, `GITHUB_USERNAME`, and `GITHUB_REPOSITORY` in an env file.
- Splits DB data into bucketed JSON files under repo directories (repo-name, repo-name-1, ...).
- Bundled single-file executable (`dist\gu.exe`) that can be called from any language or script.

Usage

CLI (during development)

```powershell
python cli.py --path "C:\path\to\project" token set <PAT>
python cli.py --path "C:\path\to\project" name set <owner>
python cli.py --path "C:\path\to\project" repo set <repo>
python cli.py --path "C:\path\to\project" sync
```

Portable exe (recommended for distribution)

Place `gu.exe` somewhere and use the `gu.env` file next to the exe to carry credentials (so it doesn't conflict with project `.env` files):

Create `gu.env` next to `gu.exe` with:

```
GITHUB_TOKEN=ghp_...
GITHUB_USERNAME=your-username
GITHUB_REPOSITORY=your-repo
```

Then run:

```powershell
dist\gu.exe --path "C:\path\to\project" token get
dist\gu.exe --path "C:\path\to\project" name get
dist\gu.exe --path "C:\path\to\project" repo get
dist\gu.exe --path "C:\path\to\project" sync
```

Sync behavior (what the exe does)
- Adds/removes the `origin` remote to use an authenticated HTTPS URL that embeds the PAT.
- Runs `git fetch origin` and then `git pull --rebase origin <branch>` before `git push` to avoid rejected pushes.
- Uses a non-interactive git environment (`GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`) to avoid browser/device prompts from Git Credential Manager.
- If there are merge conflicts during pull, the sync stops and reports the error for manual resolution.

Troubleshooting
- If you still see interactive prompts, run once to store credentials:

```powershell
git config --global credential.helper store
# then run the sync; the credential (https://<token>@github.com/...) will be written to your credential store
```

- To force purely non-interactive mode for testing:

```powershell
setx GIT_TERMINAL_PROMPT 0
setx GCM_INTERACTIVE never
```

Notes
- DB files and repo buckets are stored under the project base (determined by `dbs.json`/.env/.git presence). Read operations merge all matching bucket files.
- If you want `gu.exe` to manage `gu.env` automatically when you run `token set`, ask and I'll add that convenience.

See [sync.bat](sync.bat) for the old wrapper usage and examples.
