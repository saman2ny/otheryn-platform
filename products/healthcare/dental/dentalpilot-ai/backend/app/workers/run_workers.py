"""Run the durable background workers in one deployable process.

Deploy this module as a separate worker service. The HTTP service must remain
independent so webhook receipt stays fast and health checks are not blocked by
provider calls or SMTP delivery.
"""

import logging
import threading

from app.workers.communication_outbox import run_worker as run_communication_outbox_worker
from app.workers.email_outbox import run_worker as run_email_outbox_worker
from app.workers.subscription_billing import run_worker as run_subscription_billing_worker


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    workers = (
        threading.Thread(
            target=run_email_outbox_worker,
            name="email-outbox-worker",
            daemon=False,
        ),
        threading.Thread(
            target=run_communication_outbox_worker,
            name="communication-outbox-worker",
            daemon=False,
        ),
        threading.Thread(
            target=run_subscription_billing_worker,
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
