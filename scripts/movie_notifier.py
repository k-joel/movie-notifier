#!/usr/bin/env python3
"""
Movie Notifier - Main Orchestrator
Checks for new movie releases and sends email notifications
"""

import logging
import logging.handlers
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tmdb_client import TMDBClient
from config_manager import ConfigManager, PersonConfig
from email_notifier import EmailNotifier

class MovieNotifier:
    """Main orchestrator for movie notifications"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize movie notifier
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self.tmdb_client = None
        self.email_notifier = None
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
        log_config = self.config_manager.logging_config
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
            
            # Check for required API key
            if not self.config_manager.tmdb_config.api_key or self.config_manager.tmdb_config.api_key == "YOUR_TMDB_API_KEY_HERE":
                logging.error("TMDB API key not configured. Please update config/config.yaml")
                logging.error("Get an API key from: https://www.themoviedb.org/settings/api")
                return False
            
            # Initialize TMDB client
            self.tmdb_client = TMDBClient(
                api_key=self.config_manager.tmdb_config.api_key,
                base_url=self.config_manager.tmdb_config.base_url
            )
            
            # Initialize email notifier
            self.email_notifier = EmailNotifier(self.config_manager.email_config)
            
            logging.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error initializing components: {e}")
            return False
    
    def check_person_movies(self, person: PersonConfig) -> Dict[str, List[Dict]]:
        """
        Check for new movies for a specific person
        
        Args:
            person: Person configuration
            
        Returns:
            Dictionary with movie lists by type
        """
        movies_by_type = {
            "new_release": [],
            "upcoming": [],
            "now_playing": []
        }
        
        try:
            # Get recent movies (released in the last X days)
            if "acting" in person.notify_for or "directing" in person.notify_for:
                recent_movies = self.tmdb_client.get_recent_movies_for_person(
                    person.id, 
                    days_back=self.config_manager.notification_config.check_interval_days
                )
                
                for movie in recent_movies:
                    # Filter by credit type
                    credit_type = movie.get("credit_type", "")
                    if (credit_type == "cast" and "acting" in person.notify_for) or 
                       (credit_type == "crew" and "directing" in person.notify_for):
                        
                        # Check if we've already notified about this movie
                        if not self.config_manager.is_movie_notified(person.id, movie["id"]):
                            movies_by_type["new_release"].append(movie)
            
            # Get upcoming movies
            if self.config_manager.notification_config.include_upcoming:
                upcoming_movies = self.tmdb_client.get_upcoming_movies_for_person(
                    person.id,
                    days_ahead=self.config_manager.notification_config.look_ahead_days
                )
                
                for movie in upcoming_movies:
                    # Filter by credit type
                    credit_type = movie.get("credit_type", "")
                    if (credit_type == "cast" and "acting" in person.notify_for) or 
                       (credit_type == "crew" and "directing" in person.notify_for):
                        
                        # Check if we've already notified about this movie
                        if not self.config_manager.is_movie_notified(person.id, movie["id"]):
                            movies_by_type["upcoming"].append(movie)
            
            logging.info(f"Found {len(movies_by_type['new_release'])} new releases, "
                        f"{len(movies_by_type['upcoming'])} upcoming movies for {person.name}")
            
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
            if time_since_last_check.days < self.config_manager.notification_config.check_interval_days:
                logging.debug(f"Skipping {person.name} - checked {time_since_last_check.days} days ago")
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
        self.config_manager.update_person_last_checked(person.id, datetime.now())
        
        # Mark movies as notified in configuration
        for notification in notifications:
            for movie in notification["movies"]:
                self.config_manager.add_notified_movie(notification["person_id"], movie["id"])
        
        return notifications
    
    def run_check(self) -> bool:
        """
        Run a complete check for all tracked people
        
        Returns:
            True if successful, False otherwise
        """
        logging.info("Starting movie notification check")
        logging.info(f"Tracking {len(self.config_manager.persons)} people")
        
        all_notifications = []
        
        # Process each person
        for person in self.config_manager.persons:
            try:
                notifications = self.process_person(person)
                all_notifications.extend(notifications)
                
                if notifications:
                    logging.info(f"Found {sum(len(n['movies']) for n in notifications)} "
                                f"new movies for {person.name}")
                
            except Exception as e:
                logging.error(f"Error processing {person.name}: {e}")
        
        # Send notifications
        if all_notifications:
            logging.info(f"Sending {len(all_notifications)} notifications")
            results = self.email_notifier.send_batch_notifications(all_notifications)
            
            # Log results
            success_count = sum(1 for success in results.values() if success)
            logging.info(f"Notifications sent: {success_count}/{len(results)} successful")
        else:
            logging.info("No new movies found for notification")
        
        # Save configuration with updated timestamps
        self.config_manager.save_config()
        
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
    
    def run_scheduled(self, interval_hours: int = 24):
        """
        Run the notifier on a schedule
        
        Args:
            interval_hours: Hours between checks
        """
        if not self.initialize_components():
            logging.error("Failed to initialize components. Exiting.")
            return
        
        logging.info(f"Starting scheduled movie notifier (checking every {interval_hours} hours)")
        
        try:
            while True:
                # Run check
                self.run_check()
                
                # Wait for next check
                logging.info(f"Next check in {interval_hours} hours...")
                time.sleep(interval_hours * 3600)
                
        except KeyboardInterrupt:
            logging.info("Movie notifier stopped by user")
        except Exception as e:
            logging.error(f"Error in scheduled run: {e}")
    
    def test_connection(self) -> bool:
        """
        Test connections to TMDB and email server
        
        Returns:
            True if all connections successful, False otherwise
        """
        logging.info("Testing connections...")
        
        if not self.initialize_components():
            return False
        
        # Test TMDB connection
        try:
            test_result = self.tmdb_client.get_now_playing_movies(page=1)
            if test_result:
                logging.info("✓ TMDB API connection successful")
            else:
                logging.error("✗ TMDB API connection failed")
                return False
        except Exception as e:
            logging.error(f"✗ TMDB API connection error: {e}")
            return False
        
        # Test email connection
        try:
            test_subject = "Movie Notifier - Connection Test"
            test_body = "<p>This is a test email from Movie Notifier.</p>"
            success = self.email_notifier.send_notification(test_subject, test_body, "Test email")
            
            if success:
                logging.info("✓ Email connection successful")
            else:
                logging.error("✗ Email connection failed")
                return False
        except Exception as e:
            logging.error(f"✗ Email connection error: {e}")
            return False
        
        logging.info("✓ All connections tested successfully")
        return True

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Movie Notifier - Get email notifications for new movie releases")
    parser.add_argument("--config", "-c", default="config/config.yaml", 
                       help="Path to configuration file")
    parser.add_argument("--once", "-o", action="store_true", 
                       help="Run once and exit")
    parser.add_argument("--schedule", "-s", action="store_true", 
                       help="Run on a schedule (default: every 24 hours)")
    parser.add_argument("--interval", "-i", type=int, default=24,
                       help="Hours between checks when running on schedule")
    parser.add_argument("--test", "-t", action="store_true",
                       help="Test connections only")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Create notifier
    notifier = MovieNotifier(args.config)
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run based on arguments
    if args.test:
        notifier.test_connection()
    elif args.once:
        notifier.run_once()
    elif args.schedule:
        notifier.run_scheduled(args.interval)
    else:
        # Default: run once
        notifier.run_once()

if __name__ == "__main__":
    main()