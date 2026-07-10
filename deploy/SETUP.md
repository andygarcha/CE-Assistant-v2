# One-Time VM Setup for Auto-Deploy

Run once on the GCP VM to switch `main.py`/`scraper_main.py` from tmux to
systemd + auto-deploy. See `scripts/deploy.sh`, `.github/workflows/deploy.yml`,
and `deploy/ce-*.service` for what this wires together.

## 1. Set up SSH-based deploy access (no self-hosted runner)

**Do not register a self-hosted GitHub Actions runner on the VM.** This repo
is public, and GitHub explicitly warns against self-hosted runners on public
repos: any workflow file in the repo — including one a malicious fork PR
adds or modifies — can target a shared self-hosted runner, potentially
executing arbitrary code on the VM before anyone merges anything. Instead,
`.github/workflows/deploy.yml` runs on GitHub's own `ubuntu-latest` and
connects out to the VM over SSH to run `scripts/deploy.sh` there.

1. Generate a dedicated deploy keypair (don't reuse your personal key):
   ```bash
   ssh-keygen -t ed25519 -f ./ce-deploy-key -N "" -C "ce-assistant-deploy"
   ```
2. Add the public key (`ce-deploy-key.pub`) to the deploy user's
   `~/.ssh/authorized_keys` on the VM.
3. Get the VM's host key so GitHub's runner can verify it (run this from
   your own machine, not the VM, so you capture the key the way an external
   client sees it):
   ```bash
   ssh-keyscan -t ed25519 <vm-host-or-ip> > ce-deploy-known-hosts
   ```
4. In this repo's GitHub Settings -> Secrets and variables -> Actions, add:
   - `DEPLOY_SSH_KEY` — contents of `ce-deploy-key` (the private key)
   - `DEPLOY_KNOWN_HOSTS` — contents of `ce-deploy-known-hosts`
   - `DEPLOY_HOST` — the VM's hostname or IP
   - `DEPLOY_USER` — the deploy user on the VM
   - `DEPLOY_PATH` — absolute path to this repo's persistent clone on the VM
     (same path the systemd units below use)
5. Delete the local `ce-deploy-key`/`ce-deploy-key.pub`/`ce-deploy-known-hosts`
   files once they're stored as secrets — don't leave a copy of the private
   key on disk anywhere outside the VM's `authorized_keys` and GitHub's
   secret store.
6. Make sure the VM's firewall/security group allows inbound SSH from
   GitHub-hosted runner IP ranges (or at minimum, from the internet on the
   deploy port, since GitHub-hosted runner IPs rotate — restricting to
   GitHub's published ranges is more secure if your firewall supports IP
   sets that get updated, otherwise standard key-only SSH auth is the real
   defense here).

**`DEPLOY_PATH` on the VM must be a persistent clone of this repo checked
out to `main`, with `origin` reachable** — `scripts/deploy.sh` does
`git fetch origin main && git reset --hard origin/main` in place rather than
a fresh checkout every run. Clone it there once by hand if it doesn't
already exist:
```bash
git clone <this-repo-url> <repo-path-on-vm>
cd <repo-path-on-vm>
git checkout main
```

## 2. Fill in and install the systemd unit files

`deploy/ce-bot.service` and `deploy/ce-scraper.service` have three
placeholders each: `<deploy-user>`, `<repo-path-on-vm>` (appears multiple
times per file). Replace them with the actual Linux user the bot should run
as and the absolute path to this repo's clone on the VM (the same
`DEPLOY_PATH` value from step 1), then:

```bash
sudo cp deploy/ce-bot.service deploy/ce-scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ce-bot ce-scraper
sudo systemctl status ce-bot ce-scraper   # confirm both show "active (running)"
```

The deploy workflow (`.github/workflows/deploy.yml`) SSHes in and sets
`PIP_BIN`/`PYTHON_BIN`/`PYTEST_BIN` to `<repo-path-on-vm>/.venv/bin/{pip,python,pytest}`
(derived from the `DEPLOY_PATH` secret) — the same venv the systemd units
above run the services from (their `ExecStart` uses
`<repo-path-on-vm>/.venv/bin/python`). This venv must already exist on the
VM before the first deploy runs; if it doesn't, create it
(`python3 -m venv <repo-path-on-vm>/.venv && <repo-path-on-vm>/.venv/bin/pip
install -r requirements.txt`) and confirm with:

```bash
ls <repo-path-on-vm>/.venv/bin/python
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
