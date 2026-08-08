"""Record sync failures to the DB so they're visible and retryable from /admin
instead of only ever existing in container stdout."""
from models import SyncLog


def log_error(session, task_name: str, message: str, target: str | None = None):
    session.rollback()  # in case the exception left the session mid-transaction
    session.add(SyncLog(task_name=task_name, target=target, status="error", message=str(message)[:2000]))
    session.commit()
