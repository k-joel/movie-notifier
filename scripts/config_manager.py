#!/usr/bin/env python3
"""
Configuration Manager for Movie Notifier
Handles loading and managing configuration files
"""

import yaml
import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class PersonConfig:
    """Configuration for a tracked person (actor/director)"""
    id: int
    name: str
    type: str  # "actor" or "director"
    notify_for: List[str]  # ["acting"], ["directing"], or both
    last_checked: Optional[datetime] = None
    last_notified_movies: List[int] = field(default_factory=list)
    
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
    api_key: str
    base_url: str
    
@dataclass
class NotificationConfig:
    """Notification settings"""
    check_interval_days: int
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

class ConfigManager:
    """Manages configuration loading and saving"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config_data: Optional[Dict] = None
        self.persons: List[PersonConfig] = []
        self.email_config: Optional[EmailConfig] = None
        self.tmdb_config: Optional[TMDBConfig] = None
        self.notification_config: Optional[NotificationConfig] = None
        self.logging_config: Optional[LoggingConfig] = None
        
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
                api_key=tmdb_data.get('api_key', ''),
                base_url=tmdb_data.get('base_url', 'https://api.themoviedb.org/3')
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
                check_interval_days=notification_data.get('check_interval_days', 1),
                look_ahead_days=notification_data.get('look_ahead_days', 30),
                include_upcoming=notification_data.get('include_upcoming', True),
                include_now_playing=notification_data.get('include_now_playing', True)
            )
            
            # Load tracked persons
            persons_data = self.config_data.get('tracked_people', [])
            self.persons = []
            for person_data in persons_data:
                person = PersonConfig(
                    id=person_data.get('id'),
                    name=person_data.get('name', ''),
                    type=person_data.get('type', 'actor'),
                    notify_for=person_data.get('notify_for', ['acting'])
                )
                self.persons.append(person)
            
            # Load logging configuration
            logging_data = self.config_data.get('logging', {})
            self.logging_config = LoggingConfig(
                level=logging_data.get('level', 'INFO'),
                file=logging_data.get('file', 'logs/movie_notifier.log'),
                max_size_mb=logging_data.get('max_size_mb', 10),
                backup_count=logging_data.get('backup_count', 5)
            )
            
            logger.info(f"Configuration loaded successfully from {self.config_path}")
            logger.info(f"Loaded {len(self.persons)} tracked persons")
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
            # Update tracked persons with their current state
            persons_data = []
            for person in self.persons:
                person_data = {
                    'id': person.id,
                    'name': person.name,
                    'type': person.type,
                    'notify_for': person.notify_for
                }
                if person.last_checked:
                    person_data['last_checked'] = person.last_checked.isoformat()
                if person.last_notified_movies:
                    person_data['last_notified_movies'] = person.last_notified_movies
                persons_data.append(person_data)
            
            # Update configuration data
            if self.config_data:
                self.config_data['tracked_people'] = persons_data
            
            # Save to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Configuration saved successfully to {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def get_person_by_id(self, person_id: int) -> Optional[PersonConfig]:
        """
        Get person configuration by ID
        
        Args:
            person_id: TMDB person ID
            
        Returns:
            PersonConfig or None if not found
        """
        for person in self.persons:
            if person.id == person_id:
                return person
        return None
    
    def add_person(self, person_id: int, name: str, person_type: str = "actor", 
                   notify_for: List[str] = None) -> bool:
        """
        Add a new person to track
        
        Args:
            person_id: TMDB person ID
            name: Person's name
            person_type: "actor" or "director"
            notify_for: What to notify for (acting, directing, or both)
            
        Returns:
            True if added successfully, False otherwise
        """
        if notify_for is None:
            notify_for = ["acting"] if person_type == "actor" else ["directing"]
        
        # Check if person already exists
        if self.get_person_by_id(person_id):
            logger.warning(f"Person with ID {person_id} already exists")
            return False
        
        person = PersonConfig(
            id=person_id,
            name=name,
            type=person_type,
            notify_for=notify_for
        )
        self.persons.append(person)
        logger.info(f"Added person: {name} (ID: {person_id})")
        return True
    
    def remove_person(self, person_id: int) -> bool:
        """
        Remove a person from tracking
        
        Args:
            person_id: TMDB person ID
            
        Returns:
            True if removed successfully, False otherwise
        """
        person = self.get_person_by_id(person_id)
        if person:
            self.persons.remove(person)
            logger.info(f"Removed person: {person.name} (ID: {person_id})")
            return True
        return False
    
    def update_person_last_checked(self, person_id: int, timestamp: datetime) -> bool:
        """
        Update the last checked timestamp for a person
        
        Args:
            person_id: TMDB person ID
            timestamp: Last checked timestamp
            
        Returns:
            True if updated successfully, False otherwise
        """
        person = self.get_person_by_id(person_id)
        if person:
            person.last_checked = timestamp
            return True
        return False
    
    def add_notified_movie(self, person_id: int, movie_id: int) -> bool:
        """
        Add a movie to the list of notified movies for a person
        
        Args:
            person_id: TMDB person ID
            movie_id: TMDB movie ID
            
        Returns:
            True if added successfully, False otherwise
        """
        person = self.get_person_by_id(person_id)
        if person:
            if movie_id not in person.last_notified_movies:
                person.last_notified_movies.append(movie_id)
                # Keep only the last 100 movies to prevent list from growing too large
                if len(person.last_notified_movies) > 100:
                    person.last_notified_movies = person.last_notified_movies[-100:]
            return True
        return False
    
    def is_movie_notified(self, person_id: int, movie_id: int) -> bool:
        """
        Check if a movie has already been notified for a person
        
        Args:
            person_id: TMDB person ID
            movie_id: TMDB movie ID
            
        Returns:
            True if movie has been notified, False otherwise
        """
        person = self.get_person_by_id(person_id)
        if person:
            return movie_id in person.last_notified_movies
        return False