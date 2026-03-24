import os
import sys
import platform
import subprocess
import logging
import cron_converter
import yaml
from typing import Optional, Tuple


class Scheduler:
    """Cross-platform task scheduler using cron (Linux) or Task Scheduler (Windows)"""

    JOB_NAME = "movie_notifier"

    # Map cron converter schedule to schtasks schedule type
    SCHEDULE_TYPE_MAP = {
        "minutely": "MINUTE",
        "hourly": "HOURLY",
        "daily": "DAILY",
        "weekly": "WEEKLY",
        "monthly": "MONTHLY",
    }

    # Map cron day of week to schtasks day of week
    DOW_MAP = {
        0: "SUN",
        1: "MON",
        2: "TUE",
        3: "WED",
        4: "THU",
        5: "FRI",
        6: "SAT",
        7: "SUN",  # Some systems use 0-6, some 0-7
    }

    def __init__(self, cron_interval: str = "0 0 * * *", script_path: Optional[str] = None,
                 send_email: bool = False, verbose: bool = False, force_notify: bool = False):
        """
        Initialize scheduler

        Args:
            cron_interval: Cron expression for schedule (e.g., "0 0 * * *" for daily)
            script_path: Path to the movie_notifier script
            send_email: If True, send email notifications
            verbose: Enable verbose logging
            force_notify: Ignore last_checked timestamp
        """
        self.platform = platform.system().lower()
        self.logger = logging.getLogger(__name__)

        self.cron_interval = cron_interval
        self.send_email = send_email
        self.verbose = verbose
        self.force_notify = force_notify

        if script_path is None:
            script_path = os.path.join(
                os.path.dirname(__file__), "movie_notifier.py")
        self.script_path = os.path.abspath(script_path)

        self.python_exe = sys.executable

    def _is_linux(self) -> bool:
        return self.platform == "linux"

    def _is_windows(self) -> bool:
        return self.platform == "windows"

    def _build_arguments_string(self) -> str:
        """Build command line arguments string from instance attributes"""
        args = []
        if self.send_email:
            args.append("--send-email")
        if self.verbose:
            args.append("--verbose")
        if self.force_notify:
            args.append("--force-notify")
        return " ".join(args)

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
                self.logger.info(
                    f"Updating existing cron job: {self.JOB_NAME}")
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
                self.logger.error(
                    f"Failed to create cron job: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error setting up cron job: {e}")
            return False

    def _build_cron_entry(self) -> str:
        """Build cron entry string using the configured cron_interval and instance arguments"""
        args_str = self._build_arguments_string()
        return f"{self.cron_interval} {self.python_exe} {self.script_path} --once {args_str}"

    def _parse_cron_for_schtasks(self) -> Tuple[str, str, Optional[str], Optional[str]]:
        """
        Parse cron expression and convert to schtasks format.

        Returns:
            Tuple of (schedule_type, modifier, day_of_week, time)

        Raises:
            ValueError: If cron expression cannot be converted to schtasks format
        """
        try:
            cron = cron_converter.Cron(self.cron_interval)
            schedule = cron.schedule()

            # Get schedule type
            schedule_type_str = schedule.__class__.__name__.lower().replace("schedule", "")
            schedule_type = self.SCHEDULE_TYPE_MAP.get(
                schedule_type_str, "DAILY")

            # Get time components
            start_time = schedule.start_time
            time_str = f"{start_time.hour:02d}:{start_time.minute:02d}"

            # Determine modifier based on schedule type
            modifier = "1"
            day_of_week = None

            if schedule_type_str == "hourly":
                # Extract hour from cron (e.g., "0 * * * *" = every hour = HOURLY with MODIFIER 1)
                # For complex hourly patterns, we need special handling
                parts = self.cron_interval.split()
                if len(parts) >= 5:
                    minute = parts[0]
                    hour = parts[1]
                    if hour.startswith("*"):
                        if "/" in hour:
                            modifier = hour.split("/")[1]
                        else:
                            modifier = "1"
                    elif "*" not in hour and minute == "*":
                        # Specific hours: "0 1,3,5 * * *" - can't map to simple HOURLY
                        # Fall back to DAILY with multiple runs or warn user
                        raise ValueError(
                            f"Complex hourly pattern '{self.cron_interval}' cannot be converted to schtasks. "
                            f"Consider using a simpler schedule like '0 * * *' (hourly) or '0 0 * * *' (daily)."
                        )

            elif schedule_type_str == "daily":
                parts = self.cron_interval.split()
                if len(parts) >= 5:
                    hour = parts[1]
                    if "/" in hour:
                        # e.g., "0 */2 * * *" - every 2 days
                        modifier = hour.split("/")[1]

            elif schedule_type_str == "weekly":
                parts = self.cron_interval.split()
                if len(parts) >= 5:
                    dow = parts[4]
                    if dow not in ("*", "0-6", "1-5"):
                        # Single day: "0 0 * * 0" = weekly on Sunday
                        # Map to first day (0=SUN, 1=MON, etc.)
                        try:
                            dow_num = int(dow)
                            day_of_week = self.DOW_MAP.get(dow_num, "SUN")
                        except ValueError:
                            # Multiple days: "0 0 * * 0,6" - can't map
                            raise ValueError(
                                f"Multiple days in weekly schedule '{self.cron_interval}' cannot be converted to schtasks. "
                                f"Use a single day like '0 0 * * 0' (weekly on Sunday)."
                            )

            elif schedule_type_str == "minutely":
                # Minutely not well supported by schtasks
                raise ValueError(
                    "Minutely schedules are not supported by Windows Task Scheduler. "
                    "Use a minimum of hourly: '0 * * * *'"
                )

            elif schedule_type_str == "monthly":
                # Monthly schedules - extract day of month
                parts = self.cron_interval.split()
                if len(parts) >= 3:
                    day = parts[2]
                    if day.isdigit():
                        modifier = day

            return schedule_type, modifier, day_of_week, time_str

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(
                f"Failed to parse cron expression '{self.cron_interval}': {e}")

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
            args_str = self._build_arguments_string()
            command = f'"{self.python_exe}" "{self.script_path}" --once {args_str}'

            if self._check_windows_task_exists():
                self.logger.info(
                    f"Updating existing Windows task: {self.JOB_NAME}")
                self._remove_windows_task()

            # Parse cron and convert to schtasks format
            schedule_type, modifier, day_of_week, time_str = self._parse_cron_for_schtasks()

            # Build schtasks command
            schtasks_args = [
                "schtasks",
                "/Create",
                "/TN", self.JOB_NAME,
                "/TR", command,
                "/SC", schedule_type,
                "/MO", modifier,
                "/ST", time_str,
                "/F",
                "/ZIP"  # Run task as soon as possible after a scheduled start is missed
            ]

            # Add day of week for weekly schedules
            if day_of_week:
                schtasks_args.extend(["/D", day_of_week])

            result = subprocess.run(
                schtasks_args,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.logger.info(f"Windows task created: {self.JOB_NAME}")
                return True
            else:
                self.logger.error(
                    f"Failed to create Windows task: {result.stderr}")
                return False

        except ValueError as e:
            # Cron could not be converted - return error message
            self.logger.error(
                f"Cannot convert cron to Windows Task Scheduler: {e}")
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


def setup_scheduled_task(cron_interval: str = "0 0 * * *", script_path: Optional[str] = None,
                         send_email: bool = False, verbose: bool = False, force_notify: bool = False) -> bool:
    """
    Convenience function to setup the scheduled task

    Args:
        cron_interval: Cron expression for schedule (e.g., "0 0 * * *" for daily)
        script_path: Path to the movie_notifier script
        send_email: If True, send email notifications
        verbose: Enable verbose logging
        force_notify: Ignore last_checked timestamp

    Returns:
        True if successful, False otherwise
    """
    scheduler = Scheduler(cron_interval, script_path,
                          send_email, verbose, force_notify)
    return scheduler.setup()


def remove_scheduled_task() -> bool:
    """
    Convenience function to remove the scheduled task

    Returns:
        True if successful, False otherwise
    """
    scheduler = Scheduler()
    return scheduler.remove()


def cron_to_minutes(cron_expr: str) -> int:
    """
    Parse a cron expression and return the interval in minutes.

    Args:
        cron_expr: Cron expression (e.g., "0 0 * * *" for daily, "0 */6 * * *" for every 6 hours)

    Returns:
        Interval in minutes (minimum 1 minute)
    """
    try:
        cron = cron_converter.Cron(cron_expr)
        schedule = cron.schedule()

        # Get schedule type from class name
        schedule_type = schedule.__class__.__name__.lower().replace("schedule", "")

        # Parse cron parts
        parts = cron_expr.split()
        if len(parts) < 5:
            return 1440  # Default to 24 hours

        minute = parts[0]
        hour = parts[1]
        day_of_month = parts[2]
        month = parts[3]
        day_of_week = parts[4]

        if schedule_type == "minutely":
            # Every N minutes: "*/N * * * *"
            if minute.startswith("*/"):
                return int(minute.split("/")[1])
            return 1

        elif schedule_type == "hourly":
            # Every N hours: "0 */N * * *"
            if hour.startswith("*/"):
                return int(hour.split("/")[1]) * 60
            # Specific minute past every hour: "30 * * * *"
            if minute != "*" and hour == "*":
                return 60
            return 60

        elif schedule_type == "daily":
            # Every N days: "0 0 */N * * *"
            if "/" in day_of_month:
                return int(day_of_month.split("/")[1]) * 1440
            # Specific time daily: "0 0 * * *"
            return 1440

        elif schedule_type == "weekly":
            # Weekly - return 10080 minutes (7 days) as the interval
            return 10080

        elif schedule_type == "monthly":
            # Monthly - return 43200 minutes (30 days) as the interval
            return 43200

        # Default fallback
        return 1440

    except Exception:
        # If parsing fails, default to 24 hours (1440 minutes)
        return 1440
