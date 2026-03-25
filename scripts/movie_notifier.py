#!/usr/bin/env python3
"""
Movie Notifier - Main Orchestrator
Checks for new movie releases and sends email notifications
"""

from email_notifier import EmailNotifier
from people_manager import PeopleManager, PersonConfig
from config_manager import ConfigManager
from tmdb_client import TMDBClient
from scheduler import Scheduler, setup_scheduled_task, cron_to_minutes
import logging
import logging.handlers
import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class MovieNotifier:
    """Main orchestrator for movie notifications"""

    def __init__(self, config_path: str = "config/config.yaml", people_path: str = "config/people.yaml", send_email: bool = False,
                 force_notify: bool = False, verbose: bool = False):
        """
        Initialize movie notifier

        Args:
            config_path: Path to configuration file
            send_email: If True, send email notifications; otherwise just dump to console
            force_notify: If True, ignore last_checked timestamp and last_notified_releases (for testing)
            verbose: Enable verbose logging (DEBUG level)
        """
        self.config_manager = ConfigManager(config_path)
        self.people_manager = PeopleManager(people_path)
        self.tmdb_client = None
        self.email_notifier = None
        self.send_email = send_email
        self.force_notify = force_notify
        self.verbose = verbose
        self.setup_logging()

        # Set logging level based on verbose flag
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    def setup_logging(self):
        """Setup logging configuration"""
        # Load config to get logging settings
        if not self.config_manager.load_config():
            # Default logging if config can't be loaded
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout),
                    logging.FileHandler('movie_notifier.log', encoding='utf-8')
                ]
            )
            return

        # Use config logging settings
        log_config = self.config_manager.get_logging_config()
        if not log_config:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(sys.stdout),
                    logging.FileHandler('movie_notifier.log', encoding='utf-8')
                ]
            )
            return

        log_level = getattr(logging, log_config.level.upper(), logging.INFO)

        # Create logger
        logger = logging.getLogger()
        logger.setLevel(log_level)

        # Clear existing handlers
        logger.handlers.clear()

        # Console handler - create handler first, then reconfigure the stream
        console_handler = logging.StreamHandler(sys.stdout)
        # Reconfigure stdout to use UTF-8 encoding
        if hasattr(console_handler.stream, 'reconfigure'):
            console_handler.stream.reconfigure(  # type: ignore
                encoding='utf-8')
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler with rotation
        if log_config.file:
            log_dir = os.path.dirname(log_config.file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            file_handler = logging.handlers.RotatingFileHandler(
                log_config.file,
                maxBytes=log_config.max_size_mb * 1024 * 1024,
                backupCount=log_config.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        logger.info("Logging setup complete")

    def initialize_components(self) -> bool:
        """
        Initialize all components

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load configuration
            if not self.config_manager.load_config():
                logging.error("Failed to load configuration")
                return False

            # Load people configuration
            if not self.people_manager.load_people():
                logging.error("Failed to load people configuration")
                return False

            # Check if available_roles is populated, if not, fetch from TMDB
            if not self.people_manager.available_roles:
                logging.info(
                    "Available roles not found in config, fetching from TMDB...")
                # Get TMDB client first
                tmdb_config = self.config_manager.get_tmdb_config()
                if tmdb_config and tmdb_config.read_access_token:
                    temp_client = TMDBClient(
                        read_access_token=tmdb_config.read_access_token,
                        base_url=tmdb_config.base_url
                    )
                    self.people_manager.load_available_roles(temp_client)

            # Check for required read access token
            tmdb_config = self.config_manager.get_tmdb_config()
            if not tmdb_config or not tmdb_config.read_access_token or tmdb_config.read_access_token == "YOUR_TMDB_READ_ACCESS_TOKEN":
                logging.error(
                    "TMDB read access token not configured. Please update config/config.yaml")
                logging.error(
                    "Get a read access token from: https://www.themoviedb.org/settings/api")
                return False

            # Initialize TMDB client
            self.tmdb_client = TMDBClient(
                read_access_token=tmdb_config.read_access_token,
                base_url=tmdb_config.base_url
            )

            # Initialize email notifier
            email_config = self.config_manager.get_email_config()
            if not email_config:
                logging.error("Email configuration not found")
                return False

            self.email_notifier = EmailNotifier(email_config)

            logging.info("All components initialized successfully")
            return True

        except Exception as e:
            logging.error(f"Error initializing components: {e}")
            return False

    def send_console_notification(self, notifications: List[Dict]) -> Dict[str, bool]:
        """
        Send notifications to console instead of email

        Args:
            notifications: List of notification dictionaries

        Returns:
            Dictionary with success status for each notification
        """
        results = {}
        for i, notification in enumerate(notifications):
            try:
                person_name = notification.get("person_name", "Unknown")
                movie_type = notification.get("notification_type", "unknown")
                movies = notification.get("movies", [])

                print("\n" + "=" * 60)
                print(f"NOTIFICATION #{i + 1}")
                print(f"Person: {person_name}")
                print(f"Type: {movie_type}")
                print(f"Releases ({len(movies)}):")
                print("-" * 40)

                for movie in movies:
                    # For TV shows, TMDB uses 'name' as the title; for movies, it uses 'title'
                    title = movie.get('title') or movie.get(
                        'name') or 'Unknown Title'
                    # For TV shows, use first_air_date; for movies, use release_date
                    media_type = movie.get('media_type', 'movie')
                    if media_type == 'tv':
                        release_date = movie.get(
                            'first_air_date', 'Unknown Date')
                    else:
                        release_date = movie.get(
                            'release_date', 'Unknown Date')
                    # Use departments list for crew, otherwise credit_type for cast
                    departments = movie.get("departments", [])
                    if departments:
                        # Show departments as comma-separated list (e.g., "directing, writing")
                        dept_str = ", ".join(departments)
                        print(f"  - {title} ({release_date}) [{dept_str}]")
                    else:
                        # For cast (acting), show the credit_type
                        credit_type = movie.get("credit_type", "")
                        print(f"  - {title} ({release_date}) [{credit_type}]")

                print("=" * 60 + "\n")
                results[str(i)] = True

            except Exception as e:
                logging.error(f"Error sending console notification: {e}")
                results[str(i)] = False

        return results

    def _filter_movies_by_credit_type(self, movies: List[Dict], person: PersonConfig) -> List[Dict]:
        """Filter movies based on credit type and notification preferences."""
        # Debug: Log input movies to diagnose duplicates
        logging.debug(f"Input movies count: {len(movies)}")
        movie_ids = [m.get("id") for m in movies if m.get("id")]
        logging.debug(f"Input movie IDs: {movie_ids}")

        # First pass: filter movies based on credit type and department
        filtered = []
        already_notified_count = 0
        for movie in movies:
            credit_type = movie.get("credit_type", "")
            # Use department for crew filtering (e.g., "Directing", "Writing", "Production")
            department = movie.get("department", "").lower(
            ) if movie.get("department") else ""

            # Check if this movie matches any of the notify_for roles
            should_include = False

            if credit_type == "cast":
                # For cast (acting), check if "acting" or similar is in notify_for
                for role in person.notify_for:
                    if role.lower() in ["acting", "actor", "actress"]:
                        should_include = True
                        break
            elif credit_type == "crew" and department:
                # For crew, check if the department matches any notify_for role
                # TMDB uses "Directing", "Writing", "Production" which should match
                # "directing", "writing", "producing" in config
                for role in person.notify_for:
                    role_lower = role.lower()
                    # Check department match
                    if department == role_lower or department.startswith(role_lower):
                        should_include = True
                        break

            # Check if already notified (unless force_notify is enabled)
            if should_include:
                if self.force_notify or not self.people_manager.is_release_notified(person.id, movie["id"]):
                    filtered.append(movie)
                else:
                    already_notified_count += 1

        # Log filtered count info (only when not using force_notify)
        if not self.force_notify and already_notified_count > 0:
            logging.info(
                f"Filtered out {already_notified_count} already notified releases for {person.name}")

        # Second pass: deduplicate by movie ID, combining departments
        deduplicated = {}
        for movie in filtered:
            movie_id = movie.get("id")
            if not movie_id:
                continue

            if movie_id not in deduplicated:
                # First occurrence of this movie - add it
                deduplicated[movie_id] = movie.copy()
                # Initialize departments list with the department from this credit
                dept = movie.get("department", "")
                if dept:
                    deduplicated[movie_id]["departments"] = [dept]
                else:
                    deduplicated[movie_id]["departments"] = []
            else:
                # Duplicate movie - add department to existing entry
                dept = movie.get("department", "")
                if dept and dept not in deduplicated[movie_id]["departments"]:
                    deduplicated[movie_id]["departments"].append(dept)

        result = list(deduplicated.values())

        # Debug: Log filtered results
        logging.debug(f"Filtered movies count after dedup: {len(result)}")
        return result

    def check_person_releases(self, person: PersonConfig) -> Dict[str, List[Dict]]:
        """Check for new movies and TV shows for a specific person."""
        if self.tmdb_client is None:
            logging.error(
                "TMDB client not initialized. Call initialize_components() first.")
            return {"new_release": [], "upcoming": [], "now_playing": []}

        movies_by_type = {"new_release": [], "upcoming": [], "now_playing": []}

        try:
            notification_config = self.config_manager.get_notification_config()
            if not notification_config:
                return movies_by_type

            # Check if person has any notify_for roles configured
            if person.notify_for:
                recent_movies = self.tmdb_client.get_recent_movies_for_person(
                    person.id,
                    days_back=notification_config.look_ahead_days
                )
                movies_by_type["new_release"] = self._filter_movies_by_credit_type(
                    recent_movies, person)

                if notification_config.include_upcoming:
                    upcoming_movies = self.tmdb_client.get_upcoming_movies_for_person(
                        person.id,
                        days_ahead=notification_config.look_ahead_days
                    )
                    movies_by_type["upcoming"] = self._filter_movies_by_credit_type(
                        upcoming_movies, person)

            logging.info(f"Found {len(movies_by_type['new_release'])} new releases, "
                         f"{len(movies_by_type['upcoming'])} upcoming releases for {person.name}")

        except Exception as e:
            logging.error(f"Error checking movies for {person.name}: {e}")

        return movies_by_type

    def process_person(self, person: PersonConfig) -> List[Dict]:
        """
        Process a single person and prepare notifications

        Args:
            person: Person configuration

        Returns:
            List of notification dictionaries
        """
        notifications = []

        # Check if it's time to check this person (unless force_notify is set)
        if not self.force_notify and person.last_checked:
            time_since_last_check = datetime.now() - person.last_checked
            minutes_since_check = time_since_last_check.total_seconds() / 60

            # Get notification config
            notification_config = self.config_manager.get_notification_config()
            # Parse cron interval to determine if we should skip
            interval_minutes = 1440  # Default 24 hours
            if notification_config and notification_config.check_interval:
                interval_minutes = cron_to_minutes(
                    notification_config.check_interval)

            if minutes_since_check < interval_minutes:
                logging.info(
                    f"Skipping {person.name} - checked {minutes_since_check:.2f} minutes ago (interval: {interval_minutes}m)")
                return notifications

        # Check for releases
        releases_by_type = self.check_person_releases(person)

        # Prepare notifications for each release type
        for release_type, releases in releases_by_type.items():
            if releases:
                notifications.append({
                    "person_name": person.name,
                    "movies": releases,
                    "notification_type": release_type,
                    "person_id": person.id
                })

        # Update last checked timestamp
        self.people_manager.update_person_last_checked(
            person.id, datetime.now())

        # Mark movies as notified in configuration
        for notification in notifications:
            for movie in notification["movies"]:
                self.people_manager.add_notified_release(
                    notification["person_id"], movie["id"])

        return notifications

    def run_check(self) -> bool:
        """
        Run a complete check for all tracked people

        Returns:
            True if successful, False otherwise
        """
        logging.info("Starting movie notification check")

        # Get all persons
        persons = self.people_manager.get_all_persons()
        logging.info(f"Tracking {len(persons)} people")

        all_notifications = []

        # Process each person
        for person in persons:
            try:
                notifications = self.process_person(person)
                all_notifications.extend(notifications)

                if notifications:
                    logging.info(f"Found {sum(len(n['movies']) for n in notifications)} "
                                 f"new releases for {person.name}")

            except Exception as e:
                logging.error(f"Error processing {person.name}: {e}")

        # Send notifications
        if all_notifications:
            logging.info(f"Sending {len(all_notifications)} notifications")
            # Always dump notifications to console
            console_results = self.send_console_notification(all_notifications)

            # Optionally send email
            if self.send_email:
                if self.email_notifier is None:
                    logging.error(
                        "Email notifier not initialized. Call initialize_components() first.")
                    return False
                email_results = self.email_notifier.send_batch_notifications(
                    all_notifications)
                # Log email results
                success_count = sum(
                    1 for success in email_results.values() if success)
                logging.info(
                    f"Email notifications sent: {success_count}/{len(email_results)} successful")
            else:
                # Log console results
                success_count = sum(
                    1 for success in console_results.values() if success)
                logging.info(
                    f"Console output: {success_count}/{len(console_results)} successful")
        else:
            logging.info("No new releases found for notification")

        # Save people configuration with updated timestamps
        self.people_manager.save_people()

        logging.info("Movie notification check completed")
        return True

    def run_once(self) -> bool:
        """
        Run the notifier once and exit

        Returns:
            True if successful, False otherwise
        """
        if not self.initialize_components():
            return False

        return self.run_check()

    def run_scheduled(self, cron_interval: Optional[str] = None):
        """
        Run the notifier on a schedule using built-in sleep loop

        Args:
            cron_interval: Cron expression for schedule (e.g., "0 0 * * *" for daily).
                          If None, uses config value.
        """
        # Get cron interval from config if not provided
        if cron_interval is None:
            notification_config = self.config_manager.get_notification_config()
            cron_interval = notification_config.check_interval if notification_config else "0 0 * * *"

        if not self.initialize_components():
            logging.error("Failed to initialize components. Exiting.")
            return

        logging.info(
            f"Starting scheduled movie notifier with cron: {cron_interval}")

        # Get interval in minutes from cron for fallback loop
        interval_minutes = cron_to_minutes(cron_interval)

        try:
            while True:
                self.run_check()
                logging.info(f"Next check in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            logging.info("Movie notifier stopped by user")
        except Exception as e:
            logging.error(f"Error in scheduled run: {e}")

    def run_scheduled_native(self, cron_interval: Optional[str] = None):
        """
        Run the notifier using OS-native scheduler (cron on Linux, Task Scheduler on Windows)

        Args:
            cron_interval: Cron expression for schedule (e.g., "0 0 * * *" for daily).
                          If None, uses config value.
        """
        # Get cron interval from config if not provided
        if cron_interval is None:
            notification_config = self.config_manager.get_notification_config()
            cron_interval = notification_config.check_interval if notification_config else "0 0 * * *"

        script_path = os.path.join(
            os.path.dirname(__file__), "movie_notifier.py")
        success = setup_scheduled_task(
            cron_interval, script_path,
            send_email=self.send_email, verbose=self.verbose, force_notify=self.force_notify)
        if success:
            logging.info(
                f"Task scheduled using OS scheduler with cron: {cron_interval}")
            logging.info(
                "The scheduled task will run independently. You can close this process.")
        else:
            logging.warning(
                "Failed to setup OS scheduler, falling back to built-in loop")
            # Fall back to built-in loop
            self.run_scheduled(cron_interval)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Movie Notifier - Get email notifications for new movie releases")
    parser.add_argument("--config", "-c", default="config/config.yaml",
                        help="Path to configuration file")
    parser.add_argument("--people", "-p", default="config/people.yaml",
                        help="Path to people configuration file")
    parser.add_argument("--once", "-o", action="store_true",
                        help="Run once and exit (default)")
    parser.add_argument("--schedule", "-s", action="store_true",
                        help="Run on a schedule (default: every 24 hours)")
    parser.add_argument("--schedule-native", "-n", dest="schedule_native", action="store_true",
                        help="Use OS-native scheduler (cron on Linux, Task Scheduler on Windows)")
    parser.add_argument("--schedule-remove", "-r", dest="schedule_remove", action="store_true",
                        help="Remove the scheduled task")
    parser.add_argument("--interval", "-i", type=str, default=None,
                        help="Cron expression for schedule (e.g., '0 0 * * *' for daily)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--send-email", "-e", dest="send_email", action="store_true",
                        help="Send email notifications (default: just dump to console)")
    parser.add_argument("--force-notify", "-f", action="store_true",
                        help="Ignore last_checked timestamp and last_notified_releases (for testing)")

    args = parser.parse_args()

    # Create notifier
    notifier = MovieNotifier(args.config, args.people, send_email=args.send_email,
                             force_notify=args.force_notify, verbose=args.verbose)

    # Handle remove schedule - doesn't need --schedule or --schedule-native
    if args.schedule_remove:
        from scheduler import remove_scheduled_task
        success = remove_scheduled_task()
        if success:
            print("Scheduled task removed successfully.")
        else:
            print("Failed to remove scheduled task. It may not exist.")
        return

    # Run based on arguments
    if args.schedule_native:
        notifier.run_scheduled_native(cron_interval=args.interval)
    elif args.schedule:
        notifier.run_scheduled(cron_interval=args.interval)
    else:
        # Default: run once
        notifier.run_once()


if __name__ == "__main__":
    main()
