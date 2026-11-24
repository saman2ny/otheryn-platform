"""Run the durable background workers in one deployable process.

Deploy this module as a separate worker service. The HTTP service must remain
independent so webhook receipt stays fast and health checks are not blocked by
provider calls or SMTP delivery.

Each worker runs under a supervisor: if a worker thread raises (for example a
transient database error), the exception is logged and the worker is restarted
after a short delay instead of silently dying.
"""

import logging
import threading
import time
from typing import Callable

from app.workers.communication_outbox import run_worker as run_communication_outbox_worker
from app.workers.email_outbox import run_worker as run_email_outbox_worker
from app.workers.subscription_billing import run_worker as run_subscription_billing_worker

logger = logging.getLogger(__name__)


def _run_once(name: str, target: Callable[[], None]) -> bool:
    try:
        target()
        return True
    except Exception:
        logger.exception("Worker %s crashed", name)
        return False


def _run_supervised(name: str, target: Callable[[], None], sleep_seconds: float = 5.0) -> None:
    while True:
        if _run_once(name, target):
            return
        time.sleep(sleep_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    workers = (
        threading.Thread(
            target=_run_supervised,
            args=("email-outbox-worker", run_email_outbox_worker),
            name="email-outbox-worker",
            daemon=False,
        ),
        threading.Thread(
            target=_run_supervised,
            args=("communication-outbox-worker", run_communication_outbox_worker),
            name="communication-outbox-worker",
            daemon=False,
        ),
        threading.Thread(
            target=_run_supervised,
            args=("subscription-billing-worker", run_subscription_billing_worker),
            name="subscription-billing-worker",
            daemon=False,
        ),
    )
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()


if __name__ == "__main__":
    main()