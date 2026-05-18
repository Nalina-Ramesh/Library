-- Library Management System SQL Schema (SQLite compatible)

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
    returned BOOLEAN DEFAULT 0,
    return_date DATETIME,
    FOREIGN KEY(book_id) REFERENCES book(id)
);

-- Sample data
INSERT INTO book (title, author, category, quantity, available_quantity)
VALUES
('Clean Code', 'Robert C. Martin', 'Programming', 5, 5),
('Introduction to Algorithms', 'Cormen', 'Computer Science', 3, 3),
('Python Crash Course', 'Eric Matthes', 'Programming', 4, 4);
