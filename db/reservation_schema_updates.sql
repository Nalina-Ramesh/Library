-- Reservation and Fine System Update Script (SQLite)
-- Use this for existing databases. The Flask app also applies these
-- compatibility updates automatically at startup.

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS reservation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(120) NOT NULL,
    book_id INTEGER NOT NULL,
    reservation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending'
        CHECK(status IN ('Pending', 'Active', 'Completed', 'Cancelled')),
    FOREIGN KEY(book_id) REFERENCES book(id)
);

-- Run these ALTER statements only if the columns do not already exist.
-- The app checks this automatically in run_schema_updates().
ALTER TABLE issue_record ADD COLUMN due_date DATETIME;
ALTER TABLE issue_record ADD COLUMN fine_amount DECIMAL(10,2) DEFAULT 0;
ALTER TABLE issue_record ADD COLUMN late_days INTEGER DEFAULT 0;
ALTER TABLE issue_record ADD COLUMN fine_paid BOOLEAN DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_issue_overdue ON issue_record(returned, due_date);
CREATE INDEX IF NOT EXISTS idx_reservation_book_status
ON reservation(book_id, status, reservation_date);
CREATE INDEX IF NOT EXISTS idx_reservation_user_status
ON reservation(user_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_open_reservation_user_book
ON reservation(user_id, book_id)
WHERE status IN ('Pending', 'Active');

UPDATE issue_record
SET due_date = datetime(issue_date, '+14 days')
WHERE due_date IS NULL AND issue_date IS NOT NULL;

UPDATE issue_record
SET fine_amount = 0
WHERE fine_amount IS NULL OR fine_amount < 0;

UPDATE issue_record
SET late_days = 0
WHERE late_days IS NULL OR late_days < 0;

COMMIT;
