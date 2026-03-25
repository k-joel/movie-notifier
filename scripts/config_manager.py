#!/usr/bin/env python3
"""
Configuration Manager for Movie Notifier
Handles loading and managing configuration files
"""

import yaml
import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from utils import get_project_root

logger = logging.getLogger(__name__)


def prompt_with_default(prompt: str, default: Any, convert_type=None) -> Any:
    """
    Prompt user for input with default value shown in brackets.
    If user enters empty string, returns default.

    Args:
        prompt: The prompt message (without default)
        default: Default value to show
        convert_type: Type to convert input to (default: type of default)

    Returns:
        Converted user input or default
    """
    if convert_type is None:
        convert_type = type(default)

    default_str = str(default)
    full_prompt = f"{prompt} [{default_str}]: "
    user_input = input(full_prompt).strip()

    if user_input == "":
        return default

    try:
        # Handle boolean strings
        if convert_type == bool:
            lower = user_input.lower()
            if lower in ('true', 'yes', 'y', '1'):
                return True
            elif lower in ('false', 'no', 'n', '0'):
                return False
            else:
                raise ValueError(f"Cannot convert '{user_input}' to boolean")

        # Handle integer
        if convert_type == int:
            return int(user_input)

        # Handle float
        if convert_type == float:
            return float(user_input)

        # Default string
        return str(user_input)
    except ValueError as e:
        print(f"Error: {e}. Using default value '{default}'.")
        return default


@dataclass
class EmailConfig:
    """Email configuration"""
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    from_email: str
    to_email: str


@dataclass
class TMDBConfig:
    """TMDB API configuration"""
    read_access_token: str
    base_url: str


@dataclass
class NotificationConfig:
    """Notification settings"""
    check_interval: str  # Cron expression (e.g., "0 0 * * *" for daily)
    look_ahead_days: int
    include_upcoming: bool
    include_now_playing: bool


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str
    file: str
    max_size_mb: int
    backup_count: int


@dataclass
class N8NConfig:
    """n8n integration configuration"""
    url: str
    api_key: str


class ConfigManager:
    """Manages configuration loading and saving"""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize configuration manager

        Args:
            config_path: Path to configuration file (relative to project root)
        """
        if not os.path.isabs(config_path):
            config_path = os.path.join(get_project_root(), config_path)

        self.config_path = config_path
        self.config_data: Optional[Dict] = None
        self.email_config: Optional[EmailConfig] = None
        self.tmdb_config: Optional[TMDBConfig] = None
        self.notification_config: Optional[NotificationConfig] = None
        self.logging_config: Optional[LoggingConfig] = None
        self.n8n_config: Optional[N8NConfig] = None

    def load_config(self) -> bool:
        """
        Load configuration from YAML file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)

            if not self.config_data:
                logger.error("Configuration file is empty")
                return False

            # Load TMDB configuration
            tmdb_data = self.config_data.get('tmdb', {})
            self.tmdb_config = TMDBConfig(
                read_access_token=tmdb_data.get('read_access_token', ''),
                base_url=tmdb_data.get(
                    'base_url', 'https://api.themoviedb.org/3')
            )

            # Load email configuration
            email_data = self.config_data.get('email', {})
            self.email_config = EmailConfig(
                smtp_server=email_data.get('smtp_server', 'smtp.gmail.com'),
                smtp_port=email_data.get('smtp_port', 587),
                smtp_username=email_data.get('smtp_username', ''),
                smtp_password=email_data.get('smtp_password', ''),
                from_email=email_data.get('from_email', ''),
                to_email=email_data.get('to_email', '')
            )

            # Load notification configuration
            notification_data = self.config_data.get('notifications', {})
            self.notification_config = NotificationConfig(
                check_interval=notification_data.get(
                    'check_interval', "0 0 * * *"),
                look_ahead_days=notification_data.get('look_ahead_days', 30),
                include_upcoming=notification_data.get(
                    'include_upcoming', True),
                include_now_playing=notification_data.get(
                    'include_now_playing', True)
            )

            # Load logging configuration
            logging_data = self.config_data.get('logging', {})
            self.logging_config = LoggingConfig(
                level=logging_data.get('level', 'INFO'),
                file=logging_data.get('file', 'logs/movie_notifier.log'),
                max_size_mb=logging_data.get('max_size_mb', 10),
                backup_count=logging_data.get('backup_count', 5)
            )

            # Load n8n configuration
            n8n_data = self.config_data.get('n8n', {})
            self.n8n_config = N8NConfig(
                url=n8n_data.get('url', 'http://localhost:5678'),
                api_key=n8n_data.get('api_key', '')
            )

            logger.info(
                f"Configuration loaded successfully from {self.config_path}")
            return True

        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            return False
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return False

    def save_config(self) -> bool:
        """
        Save configuration to YAML file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(self.config_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            # Save to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_data, f,
                          default_flow_style=False, allow_unicode=True)

            logger.info(
                f"Configuration saved successfully to {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False

    def get_tmdb_config(self) -> Optional[TMDBConfig]:
        """
        Get TMDB configuration

        Returns:
            TMDBConfig or None if not loaded
        """
        return self.tmdb_config

    def get_email_config(self) -> Optional[EmailConfig]:
        """
        Get email configuration

        Returns:
            EmailConfig or None if not loaded
        """
        return self.email_config

    def get_notification_config(self) -> Optional[NotificationConfig]:
        """
        Get notification configuration

        Returns:
            NotificationConfig or None if not loaded
        """
        return self.notification_config

    def get_logging_config(self) -> Optional[LoggingConfig]:
        """
        Get logging configuration

        Returns:
            LoggingConfig or None if not loaded
        """
        return self.logging_config

    def get_n8n_config(self) -> Optional[N8NConfig]:
        """
        Get n8n configuration

        Returns:
            N8NConfig or None if not loaded
        """
        return self.n8n_config

    def update_config_value(self, section: str, key: str, value: Any) -> bool:
        """
        Update a configuration value

        Args:
            section: Configuration section (e.g., 'email', 'tmdb')
            key: Key within the section
            value: New value

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            if self.config_data:
                if section not in self.config_data:
                    self.config_data[section] = {}
                self.config_data[section][key] = value
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating configuration value: {e}")
            return False


def interactive_setup() -> bool:
    """
    Interactive configuration setup via console prompts.
    Prompts for each config setting with defaults in brackets.
    If user enters empty string, uses default.
    For to_email, if empty defaults to from_email.

    Returns:
        True if setup completed and saved successfully, False otherwise
    """
    import sys

    print("=== Movie Notifier Configuration Setup ===")
    print("Please provide the following configuration values.")
    print("Press Enter to accept the default value shown in brackets.")
    print()

    manager = ConfigManager()

    # Try to load existing config (optional)
    if manager.load_config():
        print(f"Loaded existing configuration from {manager.config_path}")
        print("You can update values below.")
    else:
        print("No existing configuration found or error loading.")
        print("Creating new configuration.")

    # Ensure config_data exists
    if manager.config_data is None:
        manager.config_data = {}

    # TMDB Configuration
    print("--- TMDB API Configuration ---")
    tmdb_defaults = {
        'read_access_token': manager.config_data.get('tmdb', {}).get('read_access_token', 'YOUR_TMDB_API_KEY_HERE'),
        'base_url': manager.config_data.get('tmdb', {}).get('base_url', 'https://api.themoviedb.org/3')
    }

    read_access_token = prompt_with_default(
        "Enter TMDB read access token", tmdb_defaults['read_access_token'])
    base_url = prompt_with_default(
        "Enter TMDB base URL", tmdb_defaults['base_url'])

    if 'tmdb' not in manager.config_data:
        manager.config_data['tmdb'] = {}
    manager.config_data['tmdb']['read_access_token'] = read_access_token
    manager.config_data['tmdb']['base_url'] = base_url

    # Email Configuration
    print("\n--- Email Configuration ---")
    email_defaults = {
        'smtp_server': manager.config_data.get('email', {}).get('smtp_server', 'smtp.gmail.com'),
        'smtp_port': manager.config_data.get('email', {}).get('smtp_port', 587),
        'smtp_username': manager.config_data.get('email', {}).get('smtp_username', 'YOUR_EMAIL@gmail.com'),
        'smtp_password': manager.config_data.get('email', {}).get('smtp_password', 'YOUR_APP_PASSWORD'),
        'from_email': manager.config_data.get('email', {}).get('from_email', 'YOUR_EMAIL@gmail.com'),
        'to_email': manager.config_data.get('email', {}).get('to_email', '')
    }

    smtp_server = prompt_with_default(
        "Enter SMTP server", email_defaults['smtp_server'])
    smtp_port = prompt_with_default(
        "Enter SMTP port", email_defaults['smtp_port'], int)
    smtp_username = prompt_with_default(
        "Enter SMTP username", email_defaults['smtp_username'])
    smtp_password = prompt_with_default(
        "Enter SMTP password", email_defaults['smtp_password'])
    from_email = prompt_with_default(
        "Enter from email address", email_defaults['from_email'])
    to_email = prompt_with_default("Enter to email address (leave empty to send to yourself)",
                                   email_defaults['to_email'])

    # Special handling: if to_email is empty, default to from_email
    if to_email == "":
        to_email = from_email
        print(f"  -> Using from_email as to_email: {to_email}")

    if 'email' not in manager.config_data:
        manager.config_data['email'] = {}
    manager.config_data['email']['smtp_server'] = smtp_server
    manager.config_data['email']['smtp_port'] = smtp_port
    manager.config_data['email']['smtp_username'] = smtp_username
    manager.config_data['email']['smtp_password'] = smtp_password
    manager.config_data['email']['from_email'] = from_email
    manager.config_data['email']['to_email'] = to_email

    # Notification Configuration
    print("\n--- Notification Settings ---")
    notification_defaults = {
        'check_interval': manager.config_data.get('notifications', {}).get('check_interval', "0 0 * * *"),
        'look_ahead_days': manager.config_data.get('notifications', {}).get('look_ahead_days', 30),
        'include_upcoming': manager.config_data.get('notifications', {}).get('include_upcoming', True),
        'include_now_playing': manager.config_data.get('notifications', {}).get('include_now_playing', True)
    }

    check_interval = prompt_with_default(
        "Enter check interval (cron format, e.g., '0 0 * * *' for daily)",
        notification_defaults['check_interval'], str)
    look_ahead_days = prompt_with_default(
        "Enter look ahead days", notification_defaults['look_ahead_days'], int)
    include_upcoming = prompt_with_default(
        "Include upcoming movies?", notification_defaults['include_upcoming'], bool)
    include_now_playing = prompt_with_default(
        "Include now playing movies?", notification_defaults['include_now_playing'], bool)

    if 'notifications' not in manager.config_data:
        manager.config_data['notifications'] = {}
    manager.config_data['notifications']['check_interval'] = check_interval
    manager.config_data['notifications']['look_ahead_days'] = look_ahead_days
    manager.config_data['notifications']['include_upcoming'] = include_upcoming
    manager.config_data['notifications']['include_now_playing'] = include_now_playing

    # Logging Configuration
    print("\n--- Logging Configuration ---")
    logging_defaults = {
        'level': manager.config_data.get('logging', {}).get('level', 'INFO'),
        'file': manager.config_data.get('logging', {}).get('file', 'logs/movie_notifier.log'),
        'max_size_mb': manager.config_data.get('logging', {}).get('max_size_mb', 10),
        'backup_count': manager.config_data.get('logging', {}).get('backup_count', 5)
    }

    level = prompt_with_default(
        "Enter logging level", logging_defaults['level'])
    log_file = prompt_with_default(
        "Enter log file path", logging_defaults['file'])
    max_size_mb = prompt_with_default(
        "Enter max log size (MB)", logging_defaults['max_size_mb'], int)
    backup_count = prompt_with_default(
        "Enter backup count", logging_defaults['backup_count'], int)

    if 'logging' not in manager.config_data:
        manager.config_data['logging'] = {}
    manager.config_data['logging']['level'] = level
    manager.config_data['logging']['file'] = log_file
    manager.config_data['logging']['max_size_mb'] = max_size_mb
    manager.config_data['logging']['backup_count'] = backup_count

    # n8n Configuration
    print("\n--- n8n Integration Configuration ---")
    n8n_defaults = {
        'url': manager.config_data.get('n8n', {}).get('url', 'http://localhost:5678'),
        'api_key': manager.config_data.get('n8n', {}).get('api_key', '')
    }

    n8n_url = prompt_with_default(
        "Enter n8n server URL", n8n_defaults['url'])
    n8n_api_key = prompt_with_default(
        "Enter n8n API key (leave empty if not using direct import)", n8n_defaults['api_key'])

    if 'n8n' not in manager.config_data:
        manager.config_data['n8n'] = {}
    manager.config_data['n8n']['url'] = n8n_url
    manager.config_data['n8n']['api_key'] = n8n_api_key

    # Save configuration
    print("\nSaving configuration...")
    if manager.save_config():
        print(f"Configuration saved successfully to {manager.config_path}")
        sys.exit(0)
    else:
        print("Failed to save configuration.")
        sys.exit(1)


if __name__ == "__main__":
    interactive_setup()
