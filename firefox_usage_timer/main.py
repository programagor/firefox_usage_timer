#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import time
import random
import subprocess
from datetime import datetime, date
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt, QCoreApplication
from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtGui import QFont, QMouseEvent

from firefox_usage_timer.config import load_config


class FirefoxUsageTimer(QWidget):
    def __init__(
        self,
        data_file,
        check_interval_ms,
        save_interval_s,
        reposition_interval_s,
        log_interval_ms,
        suspend_threshold,
        window_width,
        window_height,
        font_family,
        font_size
    ):
        super().__init__()

        # Store config
        self.data_file = data_file
        self.check_interval_ms = check_interval_ms
        self.save_interval_s = save_interval_s
        self.reposition_interval_s = reposition_interval_s
        self.log_interval_ms = log_interval_ms
        self.suspend_threshold = suspend_threshold

        # Create a frameless, always-on-top window that doesn't appear in the task bar
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setFixedSize(window_width, window_height)

        # The label that displays our timer text
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont(font_family, font_size, QFont.Weight.Bold))
        self.label.resize(self.size())

        # Usage tracking
        self.usage_seconds_today = 0
        self.running_date = date.today()
        self.last_update_ts = time.time()  # for detecting large time jumps (suspend)
        self.last_saved_ts = 0.0
        self.last_move_ts = time.time()

        # For dragging the window
        self._drag_pos = None

        # Load previously saved usage (if today’s date matches)
        self.load_usage_data()

        # Timer to check if Firefox is running, update usage, etc.
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.check_and_update)
        self.update_timer.start(self.check_interval_ms)

        # Timer for logging usage
        self.logging_timer = QTimer()
        self.logging_timer.timeout.connect(self.log_status)
        self.logging_timer.start(self.log_interval_ms)

        # Initially hidden until we detect Firefox
        self.hide()

        # Save on exit
        QCoreApplication.instance().aboutToQuit.connect(self.save_usage_data_forced)

    def load_usage_data(self):
        """Load usage data from JSON, if present and date matches today."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    stored_date = data.get("date", "")
                    stored_usage = data.get("time_used", 0)
                    if stored_date == date.today().isoformat():
                        self.usage_seconds_today = stored_usage
                    else:
                        self.usage_seconds_today = 0
            except Exception:
                self.usage_seconds_today = 0
        else:
            self.usage_seconds_today = 0

    def save_usage_data(self):
        """Save usage data to JSON (atomic replace via .tmp file)."""
        data = {
            "date": date.today().isoformat(),
            "time_used": self.usage_seconds_today
        }
        tmpfile = self.data_file + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(tmpfile, "w") as f:
                json.dump(data, f)
            os.replace(tmpfile, self.data_file)
        except Exception:
            pass  # log or handle errors if desired

    def save_usage_data_forced(self):
        """Called on exit to ensure final data is written."""
        self.save_usage_data()

    def check_firefox_running(self) -> bool:
        """Return True if firefox is running, otherwise False."""
        try:
            subprocess.run(["pgrep", "firefox"], check=True, stdout=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    def check_and_update(self):
        now = time.time()

        # Check if we crossed midnight -> reset usage
        if date.today() != self.running_date:
            self.usage_seconds_today = 0
            self.running_date = date.today()
            self.save_usage_data()

        # Detect if system was suspended
        delta = now - self.last_update_ts
        self.last_update_ts = now

        firefox_is_running = self.check_firefox_running()

        if firefox_is_running:
            # Only increment if we haven't "skipped" a large chunk
            if delta < self.suspend_threshold:
                self.usage_seconds_today += 1

            # Show the window if hidden
            if not self.isVisible():
                self.show()

            # If forcibly minimized, restore it
            if self.isMinimized():
                self.showNormal()

            # Update the label with new usage
            self.update_label()

        else:
            # Hide if Firefox is not running
            if self.isVisible():
                self.hide()

        # Periodically save usage
        if now - self.last_saved_ts > self.save_interval_s:
            self.save_usage_data()
            self.last_saved_ts = now

        # Periodically reposition
        if now - self.last_move_ts > self.reposition_interval_s:
            self.randomly_reposition()
            self.last_move_ts = now

    def update_label(self):
        """Render usage_seconds_today as HH:MM:SS in the label."""
        h = self.usage_seconds_today // 3600
        m = (self.usage_seconds_today % 3600) // 60
        s = self.usage_seconds_today % 60
        self.label.setText(f"Firefox Usage Today\n{h:02d}:{m:02d}:{s:02d}")

    def randomly_reposition(self):
        """Move the window to a random on-screen location, fully visible."""
        screen_geometry = QApplication.primaryScreen().geometry()
        max_x = screen_geometry.width() - self.width()
        max_y = screen_geometry.height() - self.height()
        new_x = random.randint(0, max_x)
        new_y = random.randint(0, max_y)
        self.move(new_x, new_y)

    def log_status(self):
        """Print once every log_interval_ms whether Firefox is running and usage so far."""
        firefox_is_running = self.check_firefox_running()
        if firefox_is_running:
            print(f"[{datetime.now()}] Firefox running. Usage: {self.usage_seconds_today}s today.")
        else:
            print(f"[{datetime.now()}] Firefox NOT running. Usage: {self.usage_seconds_today}s today.")

    # --- MOUSE HANDLING to drag frameless window ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if self._drag_pos is not None:
                diff = event.globalPosition().toPoint() - self._drag_pos
                self.move(self.pos() + diff)
                self._drag_pos = event.globalPosition().toPoint()


def main():
    # Set up the application
    app = QApplication(sys.argv)

    # Load config from config_default.ini plus any user/system overrides
    config = load_config()

    data_file = os.path.expanduser(config.get("General", "data_file"))
    check_interval_ms = config.getint("General", "check_interval_ms")
    save_interval_s = config.getint("General", "save_interval_s")
    reposition_interval_s = config.getint("General", "reposition_interval_s")
    log_interval_ms = config.getint("General", "log_interval_ms")
    suspend_threshold = config.getint("General", "suspend_threshold")

    window_width = config.getint("Window", "width")
    window_height = config.getint("Window", "height")
    font_family = config.get("Window", "font_family")
    font_size = config.getint("Window", "font_size")

    usage_timer = FirefoxUsageTimer(
        data_file=data_file,
        check_interval_ms=check_interval_ms,
        save_interval_s=save_interval_s,
        reposition_interval_s=reposition_interval_s,
        log_interval_ms=log_interval_ms,
        suspend_threshold=suspend_threshold,
        window_width=window_width,
        window_height=window_height,
        font_family=font_family,
        font_size=font_size
    )
    sys.exit(app.exec())


if __name__ == "__main__":
    main()