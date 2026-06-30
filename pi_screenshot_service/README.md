# Pi screenshot service

Standalone HTTP service for taking a screenshot of a `cedb.me` game page via
headless Chrome. Runs on the Raspberry Pi, reachable from the GCP VM over
Tailscale. Deliberately kept dependency-light (stdlib `http.server`, no web
framework) since it only needs to serve one route.

## Setup on the Pi

1. Clone this repo onto the Pi and create a venv:
   ```
   python3 -m venv .venv
   .venv/bin/pip install -r pi_screenshot_service/requirements.txt
   ```
2. Install Chromium + a matching chromedriver:
   ```
   sudo apt install chromium-browser chromium-chromedriver
   ```
3. Install and authenticate Tailscale on the Pi so the GCP VM can reach it.
4. Install the systemd unit so it survives reboots/power loss:
   ```
   sudo cp pi_screenshot_service/pi-screenshot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now pi-screenshot
   ```

## Usage

```
GET http://<pi-tailscale-ip>:8731/screenshot/<game_id>
```

Returns the PNG on success (200), or a 4xx/5xx with a plain-text error body.
Only one screenshot runs at a time — concurrent requests queue rather than
spawning multiple Chrome instances, since the Pi doesn't have RAM for that.
A capture that exceeds 20s is treated as failed and the underlying Chrome
process is always killed, so a stuck page can't leak memory across requests.
