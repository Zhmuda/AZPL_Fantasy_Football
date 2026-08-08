import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

app = Celery(
    "collector",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.sync_seasons",
        "tasks.sync_matches",
        "tasks.sync_squads",
        "tasks.sync_stats",
        "tasks.calc_points",
        "tasks.set_prices",
    ],
)

app.config_from_object("beat_schedule")
app.conf.task_default_queue = "default"
