import os
import time

import dotenv
import schedule

from update import run_update

if not os.environ.get("IS_DOCKER", False):
    dotenv.load_dotenv()


def run_scheduled():
    schedule.every(1).week.do(
        run_update, days_to_fetch=int(os.environ.get("WEEKLY_PULL_PAST_DAYS"))
    )
    schedule.every(1).day.do(
        run_update, days_to_fetch=int(os.environ.get("DAILY_PULL_PAST_DAYS"))
    )
    schedule.every(1).hour.do(
        run_update, days_to_fetch=int(os.environ.get("HOURLY_PULL_PAST_DAYS"))
    )

    print("Entering scheduled update loop.")
    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    run_scheduled()
