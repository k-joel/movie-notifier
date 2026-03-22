import os
import sys
import platform
import subprocess
import logging
from typing import Optional


class Scheduler:
    """Cross-platform task scheduler using cron (Linux) or Task Scheduler (Windows)"""

    JOB_NAME = "movie_notifier"

    def __init__(self, interval_hours: int = 24, script_path: Optional[str] = None):
        """
        Initialize scheduler

        Args:
            interval_hours: Hours between scheduled runs
            script_path: Path to the movie_notifier script
        """
        self.interval_hours = interval_hours
        self.platform = platform.system().lower()
        
        if script_path is None:
            script_path = os.path.join(os.path.dirname(__file__), "movie_notifier.py")
        self.script_path = os.path.abspath(script_path)
        
        self.python_exe = sys.executable
        self.logger = logging.getLogger(__name__)

    def _is_linux(self) -> bool:
        return self.platform == "linux"

    def _is_windows(self) -> bool:
        return self.platform == "windows"

    def setup(self) -> bool:
        """
        Setup the scheduled task

        Returns:
            True if successful, False otherwise
        """
        if self._is_linux():
            return self._setup_cron()
        elif self._is_windows():
            return self._setup_windows_task()
        else:
            self.logger.error(f"Unsupported platform: {self.platform}")
            return False

    def remove(self) -> bool:
        """
        Remove the scheduled task

        Returns:
            True if successful, False otherwise
        """
        if self._is_linux():
            return self._remove_cron()
        elif self._is_windows():
            return self._remove_windows_task()
        else:
            self.logger.error(f"Unsupported platform: {self.platform}")
            return False

    def check_exists(self) -> bool:
        """
        Check if the scheduled task already exists

        Returns:
            True if exists, False otherwise
        """
        if self._is_linux():
            return self._check_cron_exists()
        elif self._is_windows():
            return self._check_windows_task_exists()
        return False

    def _setup_cron(self) -> bool:
        """Setup cron job for Linux"""
        try:
            cron_entry = self._build_cron_entry()
            
            if self._check_cron_exists():
                self.logger.info(f"Updating existing cron job: {self.JOB_NAME}")
                self._remove_cron()
            
            result = subprocess.run(
                f'(crontab -l 2>/dev/null || echo "") | grep -v "{self.JOB_NAME}" | crontab -',
                shell=True,
                capture_output=True,
                text=True
            )
            
            result = subprocess.run(
                f'(crontab -l 2>/dev/null; echo "{cron_entry}") | crontab -',
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info(f"Cron job created: {cron_entry}")
                return True
            else:
                self.logger.error(f"Failed to create cron job: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error setting up cron job: {e}")
            return False

    def _build_cron_entry(self) -> str:
        """Build cron entry string"""
        minutes = 0
        hours = f"*/{self.interval_hours}"
        return f"{minutes} {hours} * * * {self.python_exe} {self.script_path} --once"

    def _check_cron_exists(self) -> bool:
        """Check if cron job exists"""
        try:
            result = subprocess.run(
                "crontab -l",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and self.JOB_NAME in result.stdout:
                return True
            return False
        except Exception:
            return False

    def _remove_cron(self) -> bool:
        """Remove cron job"""
        try:
            result = subprocess.run(
                f'crontab -l 2>/dev/null | grep -v "{self.JOB_NAME}" | crontab -',
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.logger.info("Cron job removed")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing cron job: {e}")
            return False

    def _setup_windows_task(self) -> bool:
        """Setup Windows Task Scheduler"""
        try:
            command = f'"{self.python_exe}" "{self.script_path}" --once'
            
            if self._check_windows_task_exists():
                self.logger.info(f"Updating existing Windows task: {self.JOB_NAME}")
                self._remove_windows_task()
            
            result = subprocess.run(
                [
                    "schtasks",
                    "/Create",
                    "/TN", self.JOB_NAME,
                    "/TR", command,
                    "/SC", "HOURLY",
                    "/MO", str(self.interval_hours),
                    "/F"
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.info(f"Windows task created: {self.JOB_NAME}")
                return True
            else:
                self.logger.error(f"Failed to create Windows task: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error setting up Windows task: {e}")
            return False

    def _check_windows_task_exists(self) -> bool:
        """Check if Windows task exists"""
        try:
            result = subprocess.run(
                ["schtasks", "/Query", "/TN", self.JOB_NAME],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def _remove_windows_task(self) -> bool:
        """Remove Windows task"""
        try:
            result = subprocess.run(
                ["schtasks", "/Delete", "/TN", self.JOB_NAME, "/F"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.logger.info("Windows task removed")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing Windows task: {e}")
            return False


def setup_scheduled_task(interval_hours: int = 24, script_path: Optional[str] = None) -> bool:
    """
    Convenience function to setup the scheduled task

    Args:
        interval_hours: Hours between scheduled runs
        script_path: Path to the movie_notifier script

    Returns:
        True if successful, False otherwise
    """
    scheduler = Scheduler(interval_hours, script_path)
    return scheduler.setup()


def remove_scheduled_task() -> bool:
    """
    Convenience function to remove the scheduled task

    Returns:
        True if successful, False otherwise
    """
    scheduler = Scheduler()
    return scheduler.remove()
