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
2. Add the public key to the deploy user's `~/.ssh/authorized_keys` on the
   VM — but restrict what it can do. This key only ever needs to run one
   command, so prefix its `authorized_keys` line with a forced command and
   disable everything else it doesn't need (replace `<repo-path-on-vm>` with
   the real, absolute path to this repo's clone on the VM):
   ```
   command="cd <repo-path-on-vm> && PIP_BIN=<repo-path-on-vm>/.venv/bin/pip PYTHON_BIN=<repo-path-on-vm>/.venv/bin/python PYTEST_BIN=<repo-path-on-vm>/.venv/bin/pytest bash scripts/deploy.sh",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty ssh-ed25519 AAAA...(contents of ce-deploy-key.pub)
   ```
   A forced command **replaces** whatever command the client sends (SSH
   ignores the command in `.github/workflows/deploy.yml`'s `ssh` invocation
   entirely once this is set — that workflow step only needs to establish
   the connection, not specify what runs). This is why the venv paths are
   hardcoded here rather than passed in from the workflow: with this in
   place, even if `DEPLOY_SSH_KEY` leaks, it can only ever run
   `scripts/deploy.sh` with these exact paths — not an arbitrary
   interactive shell. Also run the bot/scraper/deploy process under a
   dedicated, non-sudo Linux user rather than an account with broader
   system access.
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

   Note there's no `DEPLOY_PATH` secret — the repo path is baked directly
   into the forced command in `authorized_keys` (step 2), not sent from
   GitHub, since the forced command overrides anything the workflow sends
   anyway. Keep the path used there and the path used in step 2's systemd
   units in sync if you ever move the VM's clone.
5. Delete the local `ce-deploy-key`/`ce-deploy-key.pub`/`ce-deploy-known-hosts`
   files once they're stored as secrets — don't leave a copy of the private
   key on disk anywhere outside the VM's `authorized_keys` and GitHub's
   secret store.
6. Make sure the VM's firewall/security group allows inbound SSH from
   GitHub-hosted runner IP ranges (or at minimum, from the internet on the
   deploy port — GitHub-hosted runner IPs rotate, so if your firewall can't
   maintain an up-to-date allowlist of GitHub's published ranges, restrict
   to key-only auth instead: disable `PasswordAuthentication` entirely in
   `sshd_config` so an open port can't be brute-forced, and rely on the
   forced-command key restriction above to limit what a leaked key can do).

**The repo path used above must be a persistent clone of this repo checked
out to `main`, with `origin` reachable** — `scripts/deploy.sh` does
`git fetch origin main && git reset --hard origin/main` in place rather than
a fresh checkout every run. Clone it there once by hand if it doesn't
already exist:
```bash
git clone <this-repo-url> <repo-path-on-vm>
cd <repo-path-on-vm>
git checkout main
```

## 2. Fill in and install the systemd **user** unit files

`deploy/ce-bot.service` and `deploy/ce-scraper.service` are **user** units
(no `User=` directive, `WantedBy=default.target`), not system units. This is
deliberate: `scripts/deploy.sh` restarts them via `systemctl --user`, which
the deploy key can do without any `sudo`/root access at all — the forced
command from step 1 never needs privilege escalation for anything, which is
the whole point of restricting it there. Fill in the one placeholder,
`<repo-path-on-vm>` (appears multiple times per file), with the absolute
path to this repo's clone on the VM (the same path used in step 1's forced
command), then, **as the deploy user, no sudo**:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/ce-bot.service deploy/ce-scraper.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now ce-bot ce-scraper
systemctl --user status ce-bot ce-scraper   # confirm both show "active (running)"
```

User units normally only run while that user has an active login session.
Since this bot must survive reboots and SSH disconnects with nobody logged
in, enable lingering **once**, as root (this is the one step in this whole
setup that touches root, and it's a one-time bootstrap action — not
something the recurring deploy key ever needs to do):

```bash
sudo loginctl enable-linger <deploy-user>
loginctl show-user <deploy-user> -p Linger   # confirm "Linger=yes"
```

Step 1's forced command already sets `PIP_BIN`/`PYTHON_BIN`/`PYTEST_BIN` to
`<repo-path-on-vm>/.venv/bin/{pip,python,pytest}` — the same venv the
systemd units above run the services from (their `ExecStart` uses
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
- `systemctl --user status ce-bot ce-scraper` (run as the deploy user, no
  sudo) on the VM shows both `active` and started recently
  (`systemctl --user show -p ActiveEnterTimestamp ce-bot`).
- `git -C <repo-path-on-vm> rev-parse HEAD` on the VM matches the new
  commit's SHA.

Then push one deliberately broken commit (e.g. an unmatched parenthesis in
`main.py`) to confirm the rollback path: the `Deploy` run should go red,
but `systemctl --user status ce-bot ce-scraper` should still show the
*previous* commit's SHA and both services still `active`. Revert the broken
commit afterward.
