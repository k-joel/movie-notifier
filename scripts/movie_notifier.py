#!/usr/bin/env python3
"""
Movie Notifier - Main Orchestrator
Checks for new movie releases and sends email notifications
"""

from email_notifier import EmailNotifier
from people_manager import PeopleManager, PersonConfig
from config_manager import ConfigManager
from tmdb_client import TMDBClient
from scheduler import Scheduler, setup_scheduled_task, remove_scheduled_task
import logging
import logging.handlers
import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class MovieNotifier:
    """Main orchestrator for movie notifications"""

    def __init__(self, config_path: str = "config/config.yaml", console_mode: bool = False):
        """
        Initialize movie notifier

        Args:
            config_path: Path to configuration file
            console_mode: If True, output notifications to console instead of sending emails
        """
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self.people_manager = PeopleManager("config/people.yaml")
        self.tmdb_client = None
        self.email_notifier = None
        self.console_mode = console_mode
        self.setup_logging()

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
                    logging.FileHandler('movie_notifier.log')
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
                    logging.FileHandler('movie_notifier.log')
                ]
            )
            return

        log_level = getattr(logging, log_config.level.upper(), logging.INFO)

        # Create logger
        logger = logging.getLogger()
        logger.setLevel(log_level)

        # Clear existing handlers
        logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
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
                backupCount=log_config.backup_count
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

            if should_include and not self.people_manager.is_movie_notified(person.id, movie["id"]):
                filtered.append(movie)

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

    def check_person_movies(self, person: PersonConfig) -> Dict[str, List[Dict]]:
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
                    days_back=notification_config.check_interval_days
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

        # Check if it's time to check this person
        if person.last_checked:
            time_since_last_check = datetime.now() - person.last_checked
            hours_since_check = time_since_last_check.total_seconds() / 3600

            # Get notification config
            notification_config = self.config_manager.get_notification_config()
            interval_hours = (
                notification_config.check_interval_days * 24) if notification_config else 24
            if hours_since_check < interval_hours:
                logging.debug(
                    f"Skipping {person.name} - checked {hours_since_check:.1f} hours ago")
                return notifications

        # Check for movies
        movies_by_type = self.check_person_movies(person)

        # Prepare notifications for each movie type
        for movie_type, movies in movies_by_type.items():
            if movies:
                notifications.append({
                    "person_name": person.name,
                    "movies": movies,
                    "notification_type": movie_type,
                    "person_id": person.id
                })

        # Update last checked timestamp
        self.people_manager.update_person_last_checked(
            person.id, datetime.now())

        # Mark movies as notified in configuration
        for notification in notifications:
            for movie in notification["movies"]:
                self.people_manager.add_notified_movie(
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
            if self.console_mode:
                results = self.send_console_notification(all_notifications)
            else:
                if self.email_notifier is None:
                    logging.error(
                        "Email notifier not initialized. Call initialize_components() first.")
                    return False
                results = self.email_notifier.send_batch_notifications(
                    all_notifications)

            # Log results
            success_count = sum(1 for success in results.values() if success)
            logging.info(
                f"Notifications sent: {success_count}/{len(results)} successful")
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

    def run_scheduled(self, interval_hours: int = 24, use_os_scheduler: bool = True):
        """
        Run the notifier on a schedule

        Args:
            interval_hours: Hours between checks
            use_os_scheduler: If True, use OS-native scheduler (cron/Task Scheduler).
                            If False, use built-in sleep loop.
        """
        if use_os_scheduler:
            script_path = os.path.join(
                os.path.dirname(__file__), "movie_notifier.py")
            success = setup_scheduled_task(interval_hours, script_path)
            if success:
                logging.info(
                    f"Task scheduled using OS scheduler. Will run every {interval_hours} hours.")
                logging.info(
                    "The scheduled task will run independently. You can close this process.")
            else:
                logging.warning(
                    "Failed to setup OS scheduler, falling back to built-in loop")
                use_os_scheduler = False
            return

        if not self.initialize_components():
            logging.error("Failed to initialize components. Exiting.")
            return

        logging.info(
            f"Starting scheduled movie notifier (checking every {interval_hours} hours)")

        try:
            while True:
                self.run_check()
                logging.info(f"Next check in {interval_hours} hours...")
                time.sleep(interval_hours * 3600)

        except KeyboardInterrupt:
            logging.info("Movie notifier stopped by user")
        except Exception as e:
            logging.error(f"Error in scheduled run: {e}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Movie Notifier - Get email notifications for new movie releases")
    parser.add_argument("--config", "-c", default="config/config.yaml",
                        help="Path to configuration file")
    parser.add_argument("--once", "-o", action="store_true",
                        help="Run once and exit")
    parser.add_argument("--schedule", "-s", action="store_true",
                        help="Run on a schedule (default: every 24 hours)")
    parser.add_argument("--native", "-n", dest="native_schedule", action="store_true",
                        help="Use OS-native scheduler (cron on Linux, Task Scheduler on Windows)")
    parser.add_argument("--interval", "-i", type=int, default=24,
                        help="Hours between checks when running on schedule")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--console", dest="console", action="store_true",
                        help="Output notifications to console instead of sending emails")

    args = parser.parse_args()

    # Create notifier
    notifier = MovieNotifier(args.config, console_mode=args.console)

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run based on arguments
    if args.once:
        notifier.run_once()
    elif args.schedule:
        notifier.run_scheduled(
            args.interval, use_os_scheduler=args.native_schedule)
    else:
        # Default: run once
        notifier.run_once()


if __name__ == "__main__":
    main()
