-- Fine Calculation System Reference (SQLite compatible)
-- Borrowing period: 14 days
-- Fine rule: Rs. 5 per late day after due_date

BEGIN TRANSACTION;

CREATE INDEX IF NOT EXISTS idx_issue_fines
ON issue_record(fine_paid, fine_amount);

CREATE INDEX IF NOT EXISTS idx_issue_overdue
ON issue_record(returned, due_date);

DROP VIEW IF EXISTS vw_fine_details;
CREATE VIEW vw_fine_details AS
SELECT
    i.id AS issue_id,
    b.title AS book_title,
    i.borrower_name,
    i.issue_date,
    i.due_date,
    i.return_date,
    i.late_days,
    i.fine_amount,
    i.fine_paid,
    CASE
        WHEN i.returned = 0 AND i.due_date < CURRENT_TIMESTAMP THEN 'Overdue'
        WHEN i.returned = 0 THEN 'Borrowed'
        WHEN i.fine_amount > 0 AND i.fine_paid = 0 THEN 'Unpaid Fine'
        WHEN i.fine_amount > 0 AND i.fine_paid = 1 THEN 'Paid Fine'
        ELSE 'Complete'
    END AS status
FROM issue_record i
JOIN book b ON i.book_id = b.id;

COMMIT;
