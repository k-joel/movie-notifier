#!/usr/bin/env python3
"""
Email Notifier for Movie Notifier
Handles sending email notifications for new movie releases
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime
import html

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Handles sending email notifications"""

    def __init__(self, config):
        """
        Initialize email notifier

        Args:
            config: EmailConfig object
        """
        self.config = config

    def send_notification(self, subject: str, body_html: str, body_text: Optional[str] = None) -> bool:
        """
        Send an email notification

        Args:
            subject: Email subject
            body_html: HTML email body
            body_text: Plain text email body (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config.from_email
            msg['To'] = self.config.to_email

            # Create plain text version if not provided
            if body_text is None:
                # Simple HTML to text conversion
                import re
                body_text = re.sub(r'<[^>]+>', '', body_html)
                body_text = re.sub(r'\s*', '', body_text)

            # Attach both HTML and plain text versions
            part1 = MIMEText(body_text, 'plain')
            part2 = MIMEText(body_html, 'html')

            msg.attach(part1)
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username,
                             self.config.smtp_password)
                server.send_message(msg)

            logger.info(f"Email notification sent successfully: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False

    def create_movie_notification_email(self, person_name: str, movies: List[Dict],
                                        notification_type: str = "new_release") -> tuple:
        """
        Create email content for movie notifications

        Args:
            person_name: Name of the actor/director
            movies: List of movie dictionaries
            notification_type: Type of notification ("new_release", "upcoming", "now_playing")

        Returns:
            Tuple of (subject, html_body, text_body)
        """
        # Determine subject based on notification type
        if notification_type == "new_release":
            subject = f"🎬 New Movie Release: {person_name}"
        elif notification_type == "upcoming":
            subject = f"📅 Upcoming Movie: {person_name}"
        elif notification_type == "now_playing":
            subject = f"🎥 Now Playing: {person_name}"
        else:
            subject = f"Movie Update: {person_name}"

        # Create HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .movie-card {{ border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 15px; background-color: #fff; }}
                .movie-title {{ font-size: 18px; font-weight: bold; color: #007bff; margin-bottom: 10px; }}
                .movie-info {{ margin-bottom: 8px; }}
                .movie-overview {{ margin-top: 10px; color: #666; }}
                .rating {{ color: #ffc107; font-weight: bold; }}
                .release-date {{ color: #28a745; font-weight: bold; }}
                .notification-type {{ background-color: #e9ecef; padding: 5px 10px; border-radius: 3px; font-size: 12px; display: inline-block; margin-bottom: 10px; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎬 Movie Notification</h1>
                <p>You're receiving this notification because you're tracking <strong>{html.escape(person_name)}</strong></p>
            </div>
            
            <div class="notification-type">
                {notification_type.replace('_', ' ').title()} • {len(movies)} movie{'s' if len(movies) != 1 else ''}
            </div>
        """

        # Add each movie
        for movie in movies:
            title = html.escape(movie.get('title', 'Unknown Title'))
            release_date = movie.get('release_date', 'TBA')
            overview = html.escape(
                movie.get('overview', 'No overview available.'))
            vote_average = movie.get('vote_average', 'N/A')
            poster_path = movie.get('poster_path')

            # Determine credit type
            credit_type = movie.get('credit_type', '')
            credit_info = ""
            if credit_type == 'cast':
                character = movie.get('character', '')
                if character:
                    credit_info = f"as <em>{html.escape(character)}</em>"
            elif credit_type == 'crew':
                job = movie.get('job', '')
                if job:
                    credit_info = f"as <em>{html.escape(job)}</em>"

            # Create poster URL if available
            poster_html = ""
            if poster_path:
                poster_url = f"https://image.tmdb.org/t/p/w200{poster_path}"
                poster_html = f'<img src="{poster_url}" alt="{title}" style="max-width: 100px; float: right; margin-left: 15px; border-radius: 3px;">'

            html_body += f"""
            <div class="movie-card">
                {poster_html}
                <div class="movie-title">{title}</div>
                <div class="movie-info">
                    <span class="release-date">📅 Release Date: {release_date}</span>
                </div>
                <div class="movie-info">
                    <span class="rating">⭐ Rating: {vote_average}/10</span>
                </div>
                {f'<div class="movie-info">🎭 {credit_info}</div>' if credit_info else ''}
                <div class="movie-overview">
                    {overview[:200]}{'...' if len(overview) > 200 else ''}
                </div>
            </div>
            """

        # Add footer
        html_body += f"""
            <div class="footer">
                <p>This notification was sent by Movie Notifier on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>To manage your notifications, update your configuration file.</p>
                <p>Powered by The Movie Database (TMDB) API</p>
            </div>
        </body>
        </html>
        """

        # Create plain text version
        text_body = f"Movie Notification for {person_name}"
        text_body += "=" * 50 + ""

        for i, movie in enumerate(movies, 1):
            title = movie.get('title', 'Unknown Title')
            release_date = movie.get('release_date', 'TBA')
            overview = movie.get('overview', 'No overview available.')
            vote_average = movie.get('vote_average', 'N/A')

            credit_type = movie.get('credit_type', '')
            credit_info = ""
            if credit_type == 'cast':
                character = movie.get('character', '')
                if character:
                    credit_info = f"as {character}"
            elif credit_type == 'crew':
                job = movie.get('job', '')
                if job:
                    credit_info = f"as {job}"

            text_body += f"{i}. {title}"
            text_body += f"   Release Date: {release_date}"
            text_body += f"   Rating: {vote_average}/10"
            if credit_info:
                text_body += f"   {credit_info}"
            text_body += f"   Overview: {overview[:100]}..."

        text_body += f"Sent by Movie Notifier on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        text_body += "Powered by The Movie Database (TMDB) API"

        return subject, html_body, text_body

    def send_batch_notifications(self, notifications: List[Dict]) -> Dict[str, bool]:
        """
        Send multiple notifications in batch

        Args:
            notifications: List of notification dictionaries with keys:
                          - person_name: Name of actor/director
                          - movies: List of movies
                          - notification_type: Type of notification

        Returns:
            Dictionary mapping person names to success status
        """
        results = {}

        for notification in notifications:
            person_name = notification['person_name']
            movies = notification['movies']
            notification_type = notification['notification_type']

            if not movies:
                logger.info(f"No movies to notify for {person_name}")
                results[person_name] = True
                continue

            subject, html_body, text_body = self.create_movie_notification_email(
                person_name, movies, notification_type
            )

            success = self.send_notification(subject, html_body, text_body)
            results[person_name] = success

            if success:
                logger.info(
                    f"Notification sent for {person_name}: {len(movies)} movies")
            else:
                logger.error(f"Failed to send notification for {person_name}")

        return results


def send_test_email(config_path="config/config.yaml"):
    """
    Send a test email to verify email configuration

    Args:
        config_path: Path to configuration file
    """
    import sys
    import os
    # Add scripts directory to path for imports
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config_manager import ConfigManager

    print("Movie Notifier - Email Configuration Test")
    print("=========================================")
    print(f"Using configuration from: {config_path}")
    print()

    # Load configuration
    config_manager = ConfigManager(config_path)
    if not config_manager.load_config():
        print(f"ERROR: Failed to load configuration from {config_path}")
        print("Please ensure the configuration file exists and is valid.")
        sys.exit(1)

    email_config = config_manager.get_email_config()
    if not email_config:
        print("ERROR: No email configuration found in config file.")
        sys.exit(1)

    print("Email Configuration:")
    print(
        f"  SMTP Server: {email_config.smtp_server}:{email_config.smtp_port}")
    print(f"  From: {email_config.from_email}")
    print(f"  To: {email_config.to_email}")
    print()

    # Create notifier
    notifier = EmailNotifier(email_config)

    # Create test email content
    test_subject = "🎬 Movie Notifier - Test Email"

    # Escape CSS curly braces by doubling them
    test_html_body = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; text-align: center; }}
            .success {{ color: #28a745; font-weight: bold; }}
            .info {{ background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #6c757d; font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎬 Movie Notifier</h1>
            <p>Email Configuration Test</p>
        </div>
        
        <div class="info">
            <h2 class="success">✓ Test Successful!</h2>
            <p>This is a test email to verify that your email configuration is working correctly.</p>
            <p>If you're receiving this email, your Movie Notifier email settings are properly configured.</p>
        </div>
        
        <div class="info">
            <h3>Configuration Details:</h3>
            <ul>
                <li><strong>SMTP Server:</strong> {smtp_server}:{smtp_port}</li>
                <li><strong>From Email:</strong> {from_email}</li>
                <li><strong>To Email:</strong> {to_email}</li>
                <li><strong>Test Time:</strong> {test_time}</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>This test email was sent by Movie Notifier on {test_time}</p>
            <p>You can now receive movie notifications for your tracked actors and directors.</p>
        </div>
    </body>
    </html>
    """.format(
        smtp_server=email_config.smtp_server,
        smtp_port=email_config.smtp_port,
        from_email=email_config.from_email,
        to_email=email_config.to_email,
        test_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    test_text_body = """
    Movie Notifier - Email Configuration Test
    =========================================
    
    ✓ Test Successful!
    
    This is a test email to verify that your email configuration is working correctly.
    If you're receiving this email, your Movie Notifier email settings are properly configured.
    
    Configuration Details:
    - SMTP Server: {smtp_server}:{smtp_port}
    - From Email: {from_email}
    - To Email: {to_email}
    - Test Time: {test_time}
    
    This test email was sent by Movie Notifier on {test_time}
    You can now receive movie notifications for your tracked actors and directors.
    """.format(
        smtp_server=email_config.smtp_server,
        smtp_port=email_config.smtp_port,
        from_email=email_config.from_email,
        to_email=email_config.to_email,
        test_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    print("Sending test email...")
    try:
        success = notifier.send_notification(
            test_subject, test_html_body, test_text_body)

        if success:
            print("[SUCCESS] Test email sent successfully!")
            print(
                f"Check your inbox at {email_config.to_email} for the test email.")
            return True
        else:
            print("[ERROR] Failed to send test email.")
            print("Please check your email configuration and SMTP server settings.")
            return False

    except Exception as e:
        print(f"[ERROR] Error sending test email: {e}")
        print("Please check your email configuration and network connection.")
        return False


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Test email configuration for Movie Notifier")
    parser.add_argument(
        "--config",
        "-c",
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    import logging
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(
            level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Send test email
    success = send_test_email(args.config)
    sys.exit(0 if success else 1)
