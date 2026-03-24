# 🎬 Movie & TV Show Notifier

Get email notifications whenever your favorite actors or directors release new movies!

## ✨ Features

- **Automated Notifications**: Get email alerts for new movie releases
- **Track Multiple People**: Monitor actors, directors, writers, and producers simultaneously
- **Smart Filtering**: Only get notified about movies you haven't seen yet
- **Flexible Scheduling**: Configure how often to check for updates (built-in or OS-native)
- **Beautiful Emails**: Receive nicely formatted HTML emails with movie details, posters, and ratings
- **TMDB Integration**: Powered by The Movie Database (TMDB) API
- **Interactive Setup**: Easy-to-use interactive commands to manage tracked people

## 📋 Prerequisites

- Python 3.7 or higher
- TMDB API Read Access Token (free)
- Email account (Gmail recommended for simplicity)

## 🚀 Quick Start

### 1. Clone/Download

```bash
# Navigate to the movie-notifier directory
cd movie-notifier
```

### 2. Run Setup Script

```bash
python setup.py
```

This will:

- Check Python version
- Install dependencies
- Create configuration template
- Set up directories

### 3. Get TMDB API Read Access Token

1. Visit [https://www.themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
2. Create an account if needed
3. Request an API key (v3 auth)
4. Under your API settings, generate a **Read Access Token** (Bearer token)

### 4. Configure Email

**For Gmail users:**

1. Go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Generate an "App Password" (not your regular password)
3. Use this password in the config file

### 5. Configure Settings

The application uses two YAML configuration files. You can set them up manually or use the interactive tools.

#### Configuration Files

**`config/config.yaml`** - Main application settings:

```yaml
tmdb:
  read_access_token: "YOUR_TMDB_READ_ACCESS_TOKEN"
  base_url: "https://api.themoviedb.org/3"

email:
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  smtp_username: "your_email@gmail.com"
  smtp_password: "your_app_password"
  from_email: "your_email@gmail.com"
  to_email: "your_email@gmail.com"

notifications:
  check_interval_days: 1
  look_ahead_days: 30
  include_upcoming: true
  include_now_playing: true

logging:
  level: "INFO"
  file: "logs/movie_notifier.log"
  max_size_mb: 10
  backup_count: 5
```

**`config/people.yaml`** - Tracked people:

```yaml
tracked_people:
  - id: 287
    name: "Brad Pitt"
    notify_for: ["acting"]
    
  - id: 525
    name: "Christopher Nolan"
    notify_for: ["directing", "writing", "producing"]
```

#### Interactive Configuration Tools

**Config Manager** - Set up configuration files:

```bash
python scripts/config_manager.py
```

**People Manager** - Manage tracked people:

```bash
python scripts/people_manager.py
```

This interactive tool provides a menu to:

- **Add new people**: Search TMDB for actors/directors and add them to your tracking list
- **Edit existing entries**: Modify notification roles (acting, directing, writing, producing) for tracked people
- **Remove people**: Delete tracked people from your list
- **View current list**: See all people currently being tracked
- **Test configuration**: Verify your setup is working correctly

**Test TMDB Connection** - Verify API credentials:

```bash
python scripts/tmdb_client.py
```

This interactive tool allows you to configure your TMDB API credentials, email settings, and notification preferences.

#### Notification Roles

You can track people for different roles:

- `acting` - Notifications for movies they act in
- `directing` - Notifications for movies they direct
- `writing` - Notifications for movies they write
- `producing` - Notifications for movies they produce

#### TMDB Person IDs

To find TMDB person IDs:

1. Visit [https://www.themoviedb.org/person](https://www.themoviedb.org/person)
2. Search for the actor/director
3. The ID is in the URL (e.g., `/person/287` for Brad Pitt)

#### Notification Settings

- `check_interval_days`: How often to check (default: 1 day)
- `look_ahead_days`: How far ahead to check for upcoming movies (default: 30 days)
- `include_upcoming`: Notify about upcoming movies (default: true)
- `include_now_playing`: Notify about currently playing movies (default: true)

### 6. Test Email Configuration

```bash
python scripts/email_notifier.py
```

## ⚙️ Configuration Details

For detailed configuration instructions, see **Step 5: Configure Settings** in the Quick Start section above. That section includes:

- Configuration file templates and examples
- Interactive configuration tools (config_manager.py, people_manager.py)
- How to test your TMDB connection
- Notification roles and settings

## 🔧 Usage

### Command Line Options

```bash
# Show help
python scripts/movie_notifier.py --help

# Run once and exit
python scripts/movie_notifier.py --once

# Run on schedule (built-in loop, every 24 hours)
python scripts/movie_notifier.py --schedule

# Run with custom interval (every 12 hours)
python scripts/movie_notifier.py --schedule --interval 12

# Use OS-native scheduler (cron on Linux, Task Scheduler on Windows)
python scripts/movie_notifier.py --schedule --native

# Verbose logging
python scripts/movie_notifier.py --once --verbose

# Output to console instead of sending emails
python scripts/movie_notifier.py --once --console

# Custom config file
python scripts/movie_notifier.py --once --config /path/to/config.yaml
```

## 🐛 Troubleshooting

### Common Issues

**TMDB API Errors:**

- Ensure your read access token is correct
- Check if you've exceeded API rate limits (free tier: 50 requests per 10 seconds)
- Verify internet connection

**Email Sending Errors:**

- For Gmail: Use app-specific password, not your regular password
- Check SMTP server/port settings
- Verify email credentials
- Check if your email provider allows SMTP access

**Python Errors:**

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version`
- Verify file permissions

### Logs

Check the log file for detailed information:

- Location: `logs/movie_notifier.log`
- Configurable in `config/config.yaml`

## 📁 Project Structure

```
movie-notifier/
├── config/
│   ├── config.yaml          # Main configuration file
│   └── people.yaml          # Tracked people configuration
├── scripts/
│   ├── movie_notifier.py    # Main orchestrator
│   ├── tmdb_client.py       # TMDB API client
│   ├── config_manager.py   # Configuration manager
│   ├── email_notifier.py   # Email notification system
│   ├── people_manager.py   # Tracked people manager
│   ├── scheduler.py        # OS-native task scheduler
│   └── utils.py            # Utility functions
├── logs/                    # Log files
├── requirements.txt         # Python dependencies
├── setup.py                # Setup script
└── README.md               # This file
```

## 🔄 Integration with n8n

If you have n8n installed locally, you can integrate it with Movie Notifier:

### Option 1: Use n8n as Email Sender

Configure n8n to send emails instead of using SMTP directly.

### Option 2: Trigger n8n Workflows

Modify the notifier to trigger n8n webhooks when new movies are found.

### Option 3: Use n8n for Scheduling

Use n8n's scheduling features instead of the built-in scheduler.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is provided as-is for personal use. TMDB API usage is subject to TMDB's terms of service.

## 📞 Support

For issues or questions:

1. Check the troubleshooting section
2. Review the logs in `logs/movie_notifier.log`
3. Ensure your configuration is correct

---

**Enjoy staying updated with your favorite movies! 🎥🍿**