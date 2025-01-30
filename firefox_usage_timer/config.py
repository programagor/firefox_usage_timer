# firefox_usage_timer/config.py

import configparser
import os
from pathlib import Path

def load_config():
    """
    Loads the configuration from:
    1) The package's built-in config_default.ini,
    2) A user-specific ~/.config/firefox_usage_timer/config.ini if present,
    3) A system-wide /etc/firefox_usage_timer/config.ini if present.

    Returns:
        A configparser.ConfigParser object.
    """
    parser = configparser.ConfigParser()
    parser.optionxform = str  # preserve case if we want

    # Default config in the package (relative to this file's parent)
    default_config_path = Path(__file__).parent.parent / "config_default.ini"

    # User config path
    user_config_path = Path.home() / ".config" / "firefox_usage_timer" / "config.ini"

    # System-wide config path
    system_config_path = Path("/etc") / "firefox_usage_timer" / "config.ini"

    # 1) Read defaults
    parser.read(str(default_config_path))

    # 2) Read user config override if present
    if user_config_path.is_file():
        parser.read(user_config_path)

    # 3) Read system config override if present
    if system_config_path.is_file():
        parser.read(system_config_path)

    return parser