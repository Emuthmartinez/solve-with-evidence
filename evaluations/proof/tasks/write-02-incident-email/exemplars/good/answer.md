Subject: What happened to reminders on 12 March

On 12 March, SMS reminders failed for 47 minutes, from 07:48 to 08:35 Central Time.

A database migration ran during the morning reminder window and held a lock on the appointments table. The reminder worker failed until the migration was cancelled.

1,930 reminders were not sent on time. 1,610 were sent late, between 08:35 and 09:10. 320 were for appointments that had already started and were dropped. 58 clinics had at least one dropped reminder. Scheduling stayed up, and no appointment data was lost or changed.

We do not know how many patients missed appointments because of this. Clinics do not report that to us.

What changed: since 13 March the deploy tool blocks migrations between 06:00 and 20:00. Since 17 March the reminder worker retries for 30 minutes instead of failing after one attempt.

We do not have a status page yet. It is planned, with no date.

Mara Ellison
