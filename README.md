# 🎬 Movie Notifier

Get email notifications whenever your favorite actors or directors release new movies!

## ✨ Features

- **Automated Notifications**: Get email alerts for new movie releases
- **Track Multiple People**: Monitor actors and directors simultaneously
- **Smart Filtering**: Only get notified about movies you haven't seen yet
- **Flexible Scheduling**: Configure how often to check for updates
- **Beautiful Emails**: Receive nicely formatted HTML emails with movie details
- **TMDB Integration**: Powered by The Movie Database (TMDB) API

## 📋 Prerequisites

- Python 3.7 or higher
- TMDB API key (free)
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

### 3. Get TMDB API Key
1. Visit [https://www.themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
2. Create an account if needed
3. Request an API key (v3 auth)

### 4. Configure Email
**For Gmail users:**
1. Go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Generate an "App Password" (not your regular password)
3. Use this password in the config file

### 5. Edit Configuration
Open `config/config.yaml` and update:
- `tmdb.api_key`: Your TMDB API key
- `email.smtp_username`: Your email address
- `email.smtp_password`: Your app password
- `email.from_email` and `email.to_email`: Notification email addresses
- `tracked_people`: Add/remove actors/directors as needed

### 6. Test the Setup
```bash
python scripts/movie_notifier.py --test
```

### 7. Run Once
```bash
python scripts/movie_notifier.py --once
```

## ⚙️ Configuration Details

### TMDB Person IDs
To find TMDB person IDs:
1. Visit [https://www.themoviedb.org/person](https://www.themoviedb.org/person)
2. Search for the actor/director
3. The ID is in the URL (e.g., `/person/287` for Brad Pitt)

### Example Configuration
```yaml
tracked_people:
  - id: 287        # Brad Pitt
    name: "Brad Pitt"
    type: "actor"
    notify_for: ["acting"]
    
  - id: 525        # Christopher Nolan
    name: "Christopher Nolan"
    type: "director"
    notify_for: ["directing"]
```

### Notification Settings
- `check_interval_days`: How often to check (default: 1 day)
- `look_ahead_days`: How far ahead to check for upcoming movies (default: 30 days)
- `include_upcoming`: Notify about upcoming movies (default: true)
- `include_now_playing`: Notify about currently playing movies (default: true)

## 🔧 Usage

### Command Line Options
```bash
# Show help
python scripts/movie_notifier.py --help

# Test connections only
python scripts/movie_notifier.py --test

# Run once and exit
python scripts/movie_notifier.py --once

# Run on schedule (every 24 hours)
python scripts/movie_notifier.py --schedule

# Run with custom interval (every 12 hours)
python scripts/movie_notifier.py --schedule --interval 12

# Verbose logging
python scripts/movie_notifier.py --once --verbose

# Custom config file
python scripts/movie_notifier.py --once --config /path/to/config.yaml
```

### Windows Batch File
```bash
run_movie_notifier.bat --once
```

### Unix/Linux/Mac
```bash
./run_movie_notifier.sh --once
```

## 📅 Scheduling with AionUI Cron

A cron job has been set up to run daily at 9:00 AM. The cron job will:
- Execute the movie notifier
- Send notifications for new releases
- Log results to the conversation

**Cron Job Details:**
- **Name**: Movie Release Notifier
- **Schedule**: Every day at 9:00 AM
- **ID**: `cron_aedd0c33`

To modify or check the cron job, use the AionUI cron skill commands.

## 🐛 Troubleshooting

### Common Issues

**TMDB API Errors:**
- Ensure your API key is correct
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
│   └── config.yaml          # Configuration file
├── scripts/
│   ├── tmdb_client.py       # TMDB API client
│   ├── config_manager.py    # Configuration manager
│   ├── email_notifier.py    # Email notification system
│   └── movie_notifier.py    # Main orchestrator
├── data/                    # Data storage (future use)
├── logs/                    # Log files
├── requirements.txt         # Python dependencies
├── setup.py                # Setup script
├── run_movie_notifier.bat  # Windows batch file
├── run_movie_notifier.sh   # Unix shell script
└── README.md               # This file
```

## 🔄 Integration with n8n

If you have n8n installed locally, you can integrate it with Movie Notifier:

### Option 1: Use n8n as Email Sender
Configure n8n to send emails instead of using SMTP directly.

### Option 2: Trigger n8n Workflows
Modify the notifier to trigger n8n webhooks when new movies are found.

### Option 3: Use n8n for Scheduling
Use n8n's scheduling features instead of the built-in cron.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is provided as-is for personal use. TMDB API usage is subject to TMDB's terms of service.

## 🙏 Acknowledgments

- [The Movie Database (TMDB)](https://www.themoviedb.org/) for their excellent API
- Python community for the amazing libraries
- AionUI for the cron scheduling capability

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs in `logs/movie_notifier.log`
3. Ensure your configuration is correct

---

**Enjoy staying updated with your favorite movies! 🎥🍿**