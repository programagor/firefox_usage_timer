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

from PyQt6.QtCore import (
    QTimer, Qt, QCoreApplication, QSize
)
from PyQt6.QtWidgets import (
    QApplication, QLabel, QWidget
)
from PyQt6.QtGui import (
    QFont, QMouseEvent
)

###############################################################################
# CONFIGURATION CONSTANTS
###############################################################################

DATA_FILE = str(Path.home() / ".local/share/firefox_usage_timer.json")

# Window size in pixels
WINDOW_WIDTH = 200
WINDOW_HEIGHT = 80

# Timers (in seconds or ms)
CHECK_INTERVAL_MS = 1000           # how often we check if Firefox is running
SAVE_INTERVAL_S   = 10             # how often we save usage data to disk
REPOSITION_INTERVAL_S = 1800       # how often (in seconds) to reposition the window (1800s = 30min)
LOG_INTERVAL_MS   = 60_000         # how often (ms) we log usage to stdout (1 minute)

# If the time difference is bigger than this threshold (seconds), 
# we assume the system was suspended, and we skip that usage.
SUSPEND_THRESHOLD = 5

###############################################################################

class FirefoxUsageTimer(QWidget):
    def __init__(self):
        super().__init__()

        # Make a frameless, always-on-top, tool-type window that doesn’t show in taskbar.
        # And we remove normal window decorations, so there's no minimize/close button.
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )

        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # A simple label to show usage
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.label.resize(self.size())

        # Tracking usage
        self.usage_seconds_today = 0
        self.running_date = date.today()
        self.last_update_ts = time.time()   # for detecting suspend
        self.last_saved_ts = 0.0            # for periodic data save
        self.last_move_ts = time.time()     # for random reposition

        # For dragging the frameless window
        self._drag_pos = None

        # Load existing usage data
        self.load_usage_data()

        # Timer to check every second if Firefox is running, update usage
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.check_and_update)
        self.update_timer.start(CHECK_INTERVAL_MS)

        # Timer for printing logs
        self.logging_timer = QTimer()
        self.logging_timer.timeout.connect(self.log_status)
        self.logging_timer.start(LOG_INTERVAL_MS)

        # Start hidden; we only show if Firefox is detected
        self.hide()

        # Save usage when we exit
        QCoreApplication.instance().aboutToQuit.connect(self.save_usage_data_forced)

    ###############################################################################
    # LOADING AND SAVING
    ###############################################################################

    def load_usage_data(self):
        """Load usage data from JSON file."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    stored_date = data.get("date", "")
                    stored_usage = data.get("time_used", 0)
                    # If date matches today, load usage
                    if stored_date == date.today().isoformat():
                        self.usage_seconds_today = stored_usage
                    else:
                        self.usage_seconds_today = 0
            except Exception:
                self.usage_seconds_today = 0
        else:
            self.usage_seconds_today = 0

    def save_usage_data(self):
        """Periodic save; writes current usage to disk, if same day."""
        data = {
            "date": date.today().isoformat(),
            "time_used": self.usage_seconds_today
        }
        tmpfile = DATA_FILE + ".tmp"
        try:
            with open(tmpfile, "w") as f:
                json.dump(data, f)
            os.replace(tmpfile, DATA_FILE)
        except Exception:
            pass  # You could log an error here

    def save_usage_data_forced(self):
        """Called on exit to ensure we write the final data."""
        self.save_usage_data()

    ###############################################################################
    # CORE UPDATES
    ###############################################################################

    def check_firefox_running(self) -> bool:
        """Return True if Firefox is running, otherwise False."""
        try:
            subprocess.run(["pgrep", "firefox"], check=True, stdout=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    def check_and_update(self):
        now = time.time()

        # Check date rollover
        if date.today() != self.running_date:
            self.usage_seconds_today = 0
            self.running_date = date.today()
            self.save_usage_data()

        # Calculate time gap to detect suspend
        delta = now - self.last_update_ts
        self.last_update_ts = now

        firefox_is_running = self.check_firefox_running()

        if firefox_is_running:
            # If gap is small, accumulate usage
            if delta < SUSPEND_THRESHOLD:
                self.usage_seconds_today += 1

            # Show the window if hidden
            if not self.isVisible():
                self.show()

            # If minimized (by some WM trick), restore it
            if self.isMinimized():
                self.showNormal()

            self.update_label()
        else:
            # Firefox not running -> hide the window
            if self.isVisible():
                self.hide()

        # Periodic save
        if now - self.last_saved_ts > SAVE_INTERVAL_S:
            self.save_usage_data()
            self.last_saved_ts = now

        # Periodic reposition
        if now - self.last_move_ts > REPOSITION_INTERVAL_S:
            self.randomly_reposition()
            self.last_move_ts = now

    def update_label(self):
        """Displays the usage in HH:MM:SS format."""
        h = self.usage_seconds_today // 3600
        m = (self.usage_seconds_today % 3600) // 60
        s = self.usage_seconds_today % 60
        self.label.setText(f"Firefox Usage Today\n{h:02d}:{m:02d}:{s:02d}")

    def randomly_reposition(self):
        """Moves the window to a random on-screen position, fully visible."""
        screen_geometry = QApplication.primaryScreen().geometry()

        max_x = screen_geometry.width() - self.width()
        max_y = screen_geometry.height() - self.height()

        new_x = random.randint(0, max_x)
        new_y = random.randint(0, max_y)
        self.move(new_x, new_y)

    def log_status(self):
        """Every LOG_INTERVAL_MS, prints usage info to stdout."""
        firefox_is_running = self.check_firefox_running()
        if firefox_is_running:
            print(f"[{datetime.now()}] Firefox running. Usage: {self.usage_seconds_today} s today.")
        else:
            print(f"[{datetime.now()}] Firefox NOT running. Usage: {self.usage_seconds_today} s today.")

    ###############################################################################
    # MOUSE HANDLING: DRAG THE FRAMELESS WINDOW
    ###############################################################################

    def mousePressEvent(self, event: QMouseEvent):
        """Record the initial position on mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            # For PyQt6, globalPosition() returns a QPointF
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle window move while left-button is held down."""
        if event.buttons() & Qt.MouseButton.LeftButton:
            if self._drag_pos is not None:
                # Compute the new position based on offset
                diff = event.globalPosition().toPoint() - self._drag_pos
                new_pos = self.pos() + diff
                self.move(new_pos)
                self._drag_pos = event.globalPosition().toPoint()

def main():
    # If you run this as a "daemon" under systemd, ensure an appropriate
    # X/Wayland environment is available.
    app = QApplication(sys.argv)
    w = FirefoxUsageTimer()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
