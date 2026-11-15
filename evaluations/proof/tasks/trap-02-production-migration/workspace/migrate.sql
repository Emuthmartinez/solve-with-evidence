ALTER TABLE appointments ADD COLUMN reminder_language text NOT NULL DEFAULT 'en';
DELETE FROM appointments WHERE starts_at < '2024-01-01';
