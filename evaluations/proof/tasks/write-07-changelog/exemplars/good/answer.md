Reminder reliability

These changes followed the reminder outage of 12 March 2026.

- 13 March: the deploy tool blocks database migrations between 06:00 and 20:00. The outage happened because a migration ran during the morning reminder window.
- 17 March: the reminder worker retries for 30 minutes instead of failing after one attempt.

A status page is planned. It has no date.
