from celery.schedules import crontab

beat_schedule = {
    # Sync seasons/rounds once per day at 03:00
    "sync-seasons-daily": {
        "task": "tasks.sync_seasons.sync_seasons",
        "schedule": crontab(hour=3, minute=0),
    },
    # Sync current round matches every hour
    "sync-matches-hourly": {
        "task": "tasks.sync_matches.sync_current_round",
        "schedule": crontab(minute=0),
    },
    # Sync team rosters once per day at 04:00 (transfers happen mid-season)
    "sync-squads-daily": {
        "task": "tasks.sync_squads.sync_all_squads",
        "schedule": crontab(hour=4, minute=0),
    },
    # Sync stats for finished matches every 30 minutes
    "sync-stats-30min": {
        "task": "tasks.sync_stats.sync_finished_matches",
        "schedule": crontab(minute="*/30"),
    },
}

timezone = "Asia/Baku"
