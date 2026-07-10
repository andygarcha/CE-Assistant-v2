# One-Time VM Setup for Auto-Deploy

Run once on the GCP VM to switch `main.py`/`scraper_main.py` from tmux to
systemd + auto-deploy. See `scripts/deploy.sh`, `.github/workflows/deploy.yml`,
and `deploy/ce-*.service` for what this wires together.

## 1. Register a self-hosted GitHub Actions runner

Follow GitHub's official flow: repo Settings -> Actions -> Runners -> New
self-hosted runner, choosing Linux/x64. It gives you a `./config.sh` command
with a repo-specific token — run that on the VM. Install it as a systemd
service too (the runner setup script offers `./svc.sh install && ./svc.sh
start`), so it survives VM reboots.

The runner's working directory becomes `_work/<repo>/<repo>` under wherever
you installed it. **This must be a persistent clone of this repo checked out
to `main`, with `origin` reachable** — `scripts/deploy.sh` does `git fetch
origin main && git reset --hard origin/main` in place rather than a fresh
checkout every run. If the runner's default working directory isn't already
a proper clone with a remote, `cd` into it after the first run and:

```bash
git remote -v   # confirm origin points at this repo
git checkout main
```

## 2. Fill in and install the systemd unit files

`deploy/ce-bot.service` and `deploy/ce-scraper.service` have three
placeholders each: `<deploy-user>`, `<repo-path-on-vm>` (appears multiple
times per file). Replace them with the actual Linux user the bot should run
as and the absolute path to this repo's clone on the VM (the same path the
runner uses — see step 1), then:

```bash
sudo cp deploy/ce-bot.service deploy/ce-scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ce-bot ce-scraper
sudo systemctl status ce-bot ce-scraper   # confirm both show "active (running)"
```

## 3. Retire the tmux sessions

Once `systemctl status` confirms both services are up and the bot is
responding in Discord, kill the old tmux sessions so there's no chance of
two copies of the bot running against the same Discord token:

```bash
tmux ls               # find the session names
tmux kill-session -t <bot-session-name>
tmux kill-session -t <scraper-session-name>
```

## 4. Verify the full loop

Push a trivial commit to `main` (e.g. a comment change) from your dev
machine and confirm:

- The `Deploy` workflow run appears and goes green in the repo's Actions tab.
- `sudo systemctl status ce-bot ce-scraper` on the VM shows both `active`
  and started recently (`systemctl show -p ActiveEnterTimestamp ce-bot`).
- `git -C <repo-path-on-vm> rev-parse HEAD` on the VM matches the new
  commit's SHA.

Then push one deliberately broken commit (e.g. an unmatched parenthesis in
`main.py`) to confirm the rollback path: the `Deploy` run should go red,
but `systemctl status ce-bot ce-scraper` should still show the *previous*
commit's SHA and both services still `active`. Revert the broken commit
afterward.
