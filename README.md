# Firefox Usage Timer

A PyQt6 application that tracks daily Firefox usage time, displaying a small,
frameless window on top of all windows while Firefox is running. It can also
auto-move every 30 minutes and logs usage to stdout periodically.

## Features
- Detects whether Firefox is running
- Shows a small on-top timer
- Hides when Firefox closes
- Avoids counting usage during suspend/hibernate
- Resets at midnight
- Logs usage to stdout every minute
- Supports random repositioning of the timer window
- Configurable via `config_default.ini` or user/system overrides

## Building a DEB via GitHub Actions
- When you push to `main` or open a pull request, GitHub Actions (`.github/workflows/build-deb.yml`)
  will automatically build a `.deb` package using stdeb and upload it as an artifact.

## Installation
1. Download the `.deb` artifact from the GitHub Actions run.
2. Install with `sudo apt install ./firefox_usage_timer-0.1.0-1_all.deb` (adjust version as needed).
3. Run the command `firefox-usage-timer` to start the app or configure it as a systemd user service.

## Systemd User Service
Create a file `~/.config/systemd/user/firefox-usage-timer.service` with:

```
[Unit]
Description=Firefox Usage Timer

[Service]
Type=simple
ExecStart=/usr/bin/firefox-usage-timer

[Install]
WantedBy=default.target
```

Then enable it:

```
systemctl --user daemon-reload
systemctl --user enable firefox-usage-timer
systemctl --user start firefox-usage-timer
```

## Configuration
Edit `~/.config/firefox_usage_timer/config.ini` or `/etc/firefox_usage_timer/config.ini` to override defaults from `config_default.ini`.

```
[General]
data_file = ~/.local/share/firefox_usage_timer.json
...
```

```
[Window]
width = 200
height = 80
...
```

## License
See [LICENSE](LICENSE).
