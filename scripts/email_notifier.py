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
        
    def send_notification(self, subject: str, body_html: str, body_text: str = None) -> bool:
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
                body_text = re.sub(r'
\s*
', '

', body_text)
            
            # Attach both HTML and plain text versions
            part1 = MIMEText(body_text, 'plain')
            part2 = MIMEText(body_html, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
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
            overview = html.escape(movie.get('overview', 'No overview available.'))
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
        text_body = f"Movie Notification for {person_name}
"
        text_body += "=" * 50 + "

"
        
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
            
            text_body += f"{i}. {title}
"
            text_body += f"   Release Date: {release_date}
"
            text_body += f"   Rating: {vote_average}/10
"
            if credit_info:
                text_body += f"   {credit_info}
"
            text_body += f"   Overview: {overview[:100]}...

"
        
        text_body += f"
Sent by Movie Notifier on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        text_body += "
Powered by The Movie Database (TMDB) API"
        
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
                logger.info(f"Notification sent for {person_name}: {len(movies)} movies")
            else:
                logger.error(f"Failed to send notification for {person_name}")
        
        return results