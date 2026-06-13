-- Library Management System SQL Schema (SQLite compatible)

DROP TABLE IF EXISTS reservation;
DROP TABLE IF EXISTS issue_record;
DROP TABLE IF EXISTS book;

CREATE TABLE book (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    author VARCHAR(120) NOT NULL,
    category VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    available_quantity INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE issue_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    borrower_name VARCHAR(120) NOT NULL,
    issue_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    due_date DATETIME,
    returned BOOLEAN DEFAULT 0,
    return_date DATETIME,
    late_days INTEGER DEFAULT 0,
    fine_amount DECIMAL(10,2) DEFAULT 0,
    fine_paid BOOLEAN DEFAULT 0,
    FOREIGN KEY(book_id) REFERENCES book(id)
);

CREATE TABLE reservation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(120) NOT NULL,
    book_id INTEGER NOT NULL,
    reservation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending'
        CHECK(status IN ('Pending', 'Active', 'Completed', 'Cancelled')),
    FOREIGN KEY(book_id) REFERENCES book(id)
);

CREATE INDEX idx_issue_overdue ON issue_record(returned, due_date);
CREATE INDEX idx_reservation_book_status ON reservation(book_id, status, reservation_date);
CREATE INDEX idx_reservation_user_status ON reservation(user_id, status);
CREATE UNIQUE INDEX uq_open_reservation_user_book
ON reservation(user_id, book_id)
WHERE status IN ('Pending', 'Active');

-- Sample data
INSERT INTO book (title, author, category, quantity, available_quantity)
VALUES
('Clean Code', 'Robert C. Martin', 'Programming', 5, 5),
('Introduction to Algorithms', 'Cormen', 'Computer Science', 3, 3),
('Python Crash Course', 'Eric Matthes', 'Programming', 4, 4);
