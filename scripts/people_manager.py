#!/usr/bin/env python3
"""
People Manager for Movie Notifier
Handles loading, saving, and managing tracked people configuration
"""

import yaml
import os
import logging
import typing
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from utils import get_project_root

logger = logging.getLogger(__name__)

# Forward references for type hints
if typing.TYPE_CHECKING:
    from tmdb_client import TMDBClient
    from config_manager import ConfigManager


@dataclass
class PersonConfig:
    """Configuration for a tracked person (actor/director)"""
    id: int
    name: str
    notify_for: List[str]  # ["acting"], ["directing"], or both
    last_checked: Optional[datetime] = None
    last_notified_movies: List[int] = field(default_factory=list)

    @property
    def is_actor(self) -> bool:
        """Check if person is an actor (based on notify_for)"""
        return "acting" in self.notify_for

    @property
    def is_director(self) -> bool:
        """Check if person is a director (based on notify_for)"""
        return "directing" in self.notify_for


class PeopleManager:
    """Manages people configuration loading and saving"""

    def __init__(self, people_path: str = "config/people.yaml"):
        """
        Initialize people manager

        Args:
            people_path: Path to people configuration file
        """
        if not os.path.isabs(people_path):
            people_path = os.path.join(get_project_root(), people_path)

        self.people_path = people_path
        self.people_data: Optional[Dict] = None
        self.persons: List[PersonConfig] = []

    def load_people(self) -> bool:
        """
        Load people configuration from YAML file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.people_path, 'r', encoding='utf-8') as f:
                self.people_data = yaml.safe_load(f)

            if not self.people_data:
                logger.error("People configuration file is empty")
                return False

            # Load tracked persons
            persons_data = self.people_data.get('tracked_people', [])
            self.persons = []
            for person_data in persons_data:
                person = PersonConfig(
                    id=person_data.get('id'),
                    name=person_data.get('name', ''),
                    notify_for=person_data.get('notify_for', ['acting'])
                )
                self.persons.append(person)

            logger.info(
                f"People configuration loaded successfully from {self.people_path}")
            logger.info(f"Loaded {len(self.persons)} tracked persons")
            return True

        except FileNotFoundError:
            logger.error(
                f"People configuration file not found: {self.people_path}")
            return False
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML people configuration: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading people configuration: {e}")
            return False

    def save_people(self) -> bool:
        """
        Save people configuration to YAML file

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
                    'notify_for': person.notify_for
                }
                if person.last_checked:
                    person_data['last_checked'] = person.last_checked.isoformat()
                if person.last_notified_movies:
                    person_data['last_notified_movies'] = person.last_notified_movies
                persons_data.append(person_data)

            # Update people data
            if self.people_data:
                self.people_data['tracked_people'] = persons_data

            # Save to file
            with open(self.people_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.people_data, f,
                          default_flow_style=False, allow_unicode=True)

            logger.info(
                f"People configuration saved successfully to {self.people_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving people configuration: {e}")
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

    def add_person(self, person_id: int, name: str, notify_for: Optional[List[str]] = None) -> bool:
        """
        Add a new person to track

        Args:
            person_id: TMDB person ID
            name: Person's name
            notify_for: What to notify for (acting, directing, or both)

        Returns:
            True if added successfully, False otherwise
        """
        if notify_for is None:
            notify_for = ["acting"]  # Default to actor

        # Check if person already exists
        if self.get_person_by_id(person_id):
            logger.warning(f"Person with ID {person_id} already exists")
            return False

        person = PersonConfig(
            id=person_id,
            name=name,
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

    def get_all_persons(self) -> List[PersonConfig]:
        """
        Get all tracked persons

        Returns:
            List of PersonConfig objects
        """
        return self.persons

    def get_actors(self) -> List[PersonConfig]:
        """
        Get all persons who are actors (based on notify_for)

        Returns:
            List of PersonConfig objects for actors
        """
        return [person for person in self.persons if person.is_actor]

    def get_directors(self) -> List[PersonConfig]:
        """
        Get all persons who are directors (based on notify_for)

        Returns:
            List of PersonConfig objects for directors
        """
        return [person for person in self.persons if person.is_director]


def interactive_setup():
    """
    Interactive setup for managing tracked people.
    Runs when the script is executed directly.
    """
    import sys
    import os

    # Add scripts directory to path for imports
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    from tmdb_client import TMDBClient
    from config_manager import ConfigManager

    print("\n" + "="*60)
    print("MOVIE NOTIFIER - PEOPLE MANAGER")
    print("="*60)

    # Load configuration
    config_manager = ConfigManager()
    if not config_manager.load_config():
        print("Error: Could not load configuration. Please run setup.py first.")
        sys.exit(1)

    # Get TMDB configuration
    tmdb_config = config_manager.get_tmdb_config()
    if not tmdb_config or not tmdb_config.read_access_token:
        print("Error: TMDB configuration not found or read access token is missing.")
        print("Please run setup.py to configure your TMDB read access token.")
        sys.exit(1)

    # Initialize TMDB client
    tmdb_client = TMDBClient(
        read_access_token=tmdb_config.read_access_token,
        base_url=tmdb_config.base_url
    )

    # Initialize people manager
    people_manager = PeopleManager()
    if not people_manager.load_people():
        print("Warning: Could not load people configuration. Starting with empty list.")

    while True:
        print("\n" + "-"*60)
        print("CURRENTLY TRACKED PEOPLE:")
        print("-"*60)

        persons = people_manager.get_all_persons()
        if not persons:
            print("No people are currently being tracked.")
        else:
            for i, person in enumerate(persons, 1):
                notify_str = ", ".join(
                    person.notify_for) if person.notify_for else "none"
                print(f"{i}. {person.name} ({notify_str})")

        print("\nOPTIONS:")
        print("1. Add a person")
        print("2. Delete a person")
        print("3. Edit a person's notification roles")
        print("4. Save and quit")
        print("5. Quit without saving")

        try:
            choice = input("\nEnter your choice (1-5): ").strip()

            if choice == "1":
                add_person_interactive(people_manager, tmdb_client)
            elif choice == "2":
                delete_person_interactive(people_manager)
            elif choice == "3":
                edit_person_interactive(people_manager)
            elif choice == "4":
                if people_manager.save_people():
                    print("Configuration saved successfully.")
                else:
                    print("Error: Could not save configuration.")
                print("Goodbye!")
                break
            elif choice == "5":
                print("Exiting without saving changes.")
                break
            else:
                print("Invalid choice. Please enter a number between 1 and 5.")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            save_choice = input(
                "Save changes before quitting? (y/n): ").strip().lower()
            if save_choice == 'y':
                if people_manager.save_people():
                    print("Configuration saved successfully.")
                else:
                    print("Error: Could not save configuration.")
            print("Goodbye!")
            break
        except EOFError:
            print("\n\nEnd of input reached. Exiting without saving.")
            break
        except Exception as e:
            print(f"Error: {e}")
            print("Please try again.")


def add_person_interactive(people_manager: 'PeopleManager', tmdb_client: 'TMDBClient'):
    """Interactive flow for adding a new person."""
    print("\n" + "-"*60)
    print("ADD NEW PERSON")
    print("-"*60)

    # Get search query
    search_query = input("Enter person name to search: ").strip()
    if not search_query:
        print("No name entered. Cancelling.")
        return

    print(f"\nSearching for '{search_query}' on TMDB...")
    search_results = tmdb_client.search_person(search_query)

    if not search_results or 'results' not in search_results or not search_results['results']:
        print("No results found. Please try a different name.")
        return

    results = search_results['results'][:10]  # Top 10 results

    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results, 1):
        known_for = []
        if 'known_for' in result and result['known_for']:
            for item in result['known_for'][:3]:  # Show up to 3 known works
                title = item.get('title') or item.get('name') or 'Unknown'
                media_type = item.get('media_type', 'movie')
                known_for.append(f"{title} ({media_type})")

        known_for_str = ", ".join(known_for) if known_for else "No known works"
        print(f"{i}. {result.get('name', 'Unknown')} (ID: {result.get('id', 'N/A')})")
        print(f"   Known for: {known_for_str}")
        print()

    try:
        selection = input(
            f"Select person (1-{len(results)}), or 0 to cancel: ").strip()
        if selection == "0":
            print("Cancelled.")
            return

        index = int(selection) - 1
        if index < 0 or index >= len(results):
            print("Invalid selection.")
            return

        selected_person = results[index]
        person_id = selected_person['id']
        person_name = selected_person['name']

        # Check if person already exists
        if people_manager.get_person_by_id(person_id):
            print(
                f"Person '{person_name}' (ID: {person_id}) is already being tracked.")
            return

        # Get person details to determine roles
        print(f"\nGetting details for {person_name}...")
        person_details = tmdb_client.get_person_details(person_id)

        if not person_details:
            print("Could not retrieve person details. Using default roles.")
            known_for_department = "Acting"  # Default
        else:
            known_for_department = person_details.get(
                'known_for_department', 'Acting')

        # Determine available roles
        available_roles = []
        if known_for_department.lower() in ['acting', 'actor', 'actress']:
            available_roles.append('acting')
        if known_for_department.lower() in ['directing', 'director']:
            available_roles.append('directing')

        # Also check for writing, producing, etc.
        if 'writing' in known_for_department.lower():
            available_roles.append('writing')
        if 'production' in known_for_department.lower():
            available_roles.append('producing')

        # If no specific department found, offer common options
        if not available_roles:
            available_roles = ['acting', 'directing', 'writing', 'producing']

        print(f"\n{person_name} is known for: {known_for_department}")
        print("Available notification roles:")
        for i, role in enumerate(available_roles, 1):
            print(f"  {i}. {role}")

        # Get role selections
        selected_roles = []
        while True:
            role_input = input(
                "\nSelect roles (comma-separated numbers, e.g., '1,3' or 'all' for all): ").strip().lower()

            if role_input == 'all':
                selected_roles = available_roles.copy()
                break
            elif role_input == '':
                print("No roles selected. Using default (acting).")
                selected_roles = ['acting']
                break
            else:
                try:
                    role_indices = [
                        int(x.strip()) - 1 for x in role_input.split(',')]
                    valid = True
                    for idx in role_indices:
                        if idx < 0 or idx >= len(available_roles):
                            print(
                                f"Invalid selection: {idx + 1}. Please try again.")
                            valid = False
                            break

                    if valid:
                        selected_roles = [available_roles[idx]
                                          for idx in role_indices]
                        break
                except ValueError:
                    print("Invalid input. Please enter numbers separated by commas.")

        # Add the person
        if people_manager.add_person(person_id, person_name, selected_roles):
            print(f"\nSuccessfully added {person_name} (ID: {person_id})")
            print(f"Notification roles: {', '.join(selected_roles)}")
        else:
            print(
                f"\nFailed to add {person_name}. They may already be tracked.")

    except ValueError:
        print("Invalid input. Please enter a number.")
    except Exception as e:
        print(f"Error: {e}")


def delete_person_interactive(people_manager: PeopleManager):
    """Interactive flow for deleting a person."""
    print("\n" + "-"*60)
    print("DELETE PERSON")
    print("-"*60)

    persons = people_manager.get_all_persons()
    if not persons:
        print("No people to delete.")
        return

    for i, person in enumerate(persons, 1):
        notify_str = ", ".join(
            person.notify_for) if person.notify_for else "none"
        print(f"{i}. {person.name} ({notify_str})")

    try:
        selection = input(
            f"\nSelect person to delete (1-{len(persons)}), or 0 to cancel: ").strip()
        if selection == "0":
            print("Cancelled.")
            return

        index = int(selection) - 1
        if index < 0 or index >= len(persons):
            print("Invalid selection.")
            return

        person_to_delete = persons[index]
        confirm = input(
            f"Are you sure you want to delete {person_to_delete.name}? (y/n): ").strip().lower()

        if confirm == 'y':
            if people_manager.remove_person(person_to_delete.id):
                print(f"Successfully deleted {person_to_delete.name}.")
            else:
                print(f"Failed to delete {person_to_delete.name}.")
        else:
            print("Deletion cancelled.")

    except ValueError:
        print("Invalid input. Please enter a number.")


def edit_person_interactive(people_manager: PeopleManager):
    """Interactive flow for editing a person's notification roles."""
    print("\n" + "-"*60)
    print("EDIT PERSON'S NOTIFICATION ROLES")
    print("-"*60)

    persons = people_manager.get_all_persons()
    if not persons:
        print("No people to edit.")
        return

    for i, person in enumerate(persons, 1):
        notify_str = ", ".join(
            person.notify_for) if person.notify_for else "none"
        print(f"{i}. {person.name} ({notify_str})")

    try:
        selection = input(
            f"\nSelect person to edit (1-{len(persons)}), or 0 to cancel: ").strip()
        if selection == "0":
            print("Cancelled.")
            return

        index = int(selection) - 1
        if index < 0 or index >= len(persons):
            print("Invalid selection.")
            return

        person_to_edit = persons[index]
        print(f"\nEditing {person_to_edit.name}")
        print(
            f"Current notification roles: {', '.join(person_to_edit.notify_for) if person_to_edit.notify_for else 'none'}")

        # Available roles
        available_roles = ['acting', 'directing', 'writing', 'producing']
        print("\nAvailable notification roles:")
        for i, role in enumerate(available_roles, 1):
            print(f"  {i}. {role}")

        # Get new role selections
        selected_roles = []
        while True:
            role_input = input(
                "\nSelect new roles (comma-separated numbers, e.g., '1,3' or 'all' for all): ").strip().lower()

            if role_input == 'all':
                selected_roles = available_roles.copy()
                break
            elif role_input == '':
                print("No roles selected. Keeping current roles.")
                return
            else:
                try:
                    role_indices = [
                        int(x.strip()) - 1 for x in role_input.split(',')]
                    valid = True
                    for idx in role_indices:
                        if idx < 0 or idx >= len(available_roles):
                            print(
                                f"Invalid selection: {idx + 1}. Please try again.")
                            valid = False
                            break

                    if valid:
                        selected_roles = [available_roles[idx]
                                          for idx in role_indices]
                        break
                except ValueError:
                    print("Invalid input. Please enter numbers separated by commas.")

        # Update the person
        person_to_edit.notify_for = selected_roles
        print(f"\nUpdated {person_to_edit.name}")
        print(f"New notification roles: {', '.join(selected_roles)}")

    except ValueError:
        print("Invalid input. Please enter a number.")


if __name__ == "__main__":
    interactive_setup()
