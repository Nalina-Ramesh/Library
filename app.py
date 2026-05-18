from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///library.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Display timezone for UI (IST)
# Fallback avoids crash on systems missing IANA tz database.
if ZoneInfo is not None:
    try:
        APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
    except Exception:
        APP_TIMEZONE = timezone(timedelta(hours=5, minutes=30))
else:
    APP_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


class Book(db.Model):
    """Book master table for library inventory."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    available_quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class IssueRecord(db.Model):
    """Tracks issued books and return state."""

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    borrower_name = db.Column(db.String(120), nullable=False)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    returned = db.Column(db.Boolean, default=False)
    return_date = db.Column(db.DateTime, nullable=True)

    book = db.relationship("Book", backref=db.backref("issues", lazy=True))


@app.template_filter("format_datetime")
def format_datetime(value, fmt="%d-%m-%Y %I:%M %p"):
    """Convert stored UTC datetime to IST for UI display."""
    if not value:
        return "-"

    # SQLAlchemy/SQLite commonly returns naive datetime values.
    # Treat naive values as UTC and convert to IST for consistent display.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    local_dt = value.astimezone(APP_TIMEZONE)
    return local_dt.strftime(fmt)


def is_logged_in() -> bool:
    return bool(session.get("admin_logged_in"))


@app.route("/")
def home():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Simple admin login for demo.
    Default credentials:
    username: admin
    password: admin123
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == "admin" and password == "admin123":
            session["admin_logged_in"] = True
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))

    total_books = db.session.query(db.func.sum(Book.quantity)).scalar() or 0
    available_books = db.session.query(db.func.sum(Book.available_quantity)).scalar() or 0
    issued_books = total_books - available_books
    total_titles = Book.query.count()

    recent_issues = (
        IssueRecord.query.order_by(IssueRecord.issue_date.desc()).limit(5).all()
    )

    return render_template(
        "dashboard.html",
        total_books=total_books,
        issued_books=issued_books,
        available_books=available_books,
        total_titles=total_titles,
        recent_issues=recent_issues,
    )


@app.route("/books")
def view_books():
    if not is_logged_in():
        return redirect(url_for("login"))

    q = request.args.get("q", "").strip()
    books_query = Book.query

    if q:
        pattern = f"%{q}%"
        books_query = books_query.filter(
            db.or_(
                Book.title.like(pattern),
                Book.author.like(pattern),
                Book.category.like(pattern),
            )
        )

    books = books_query.order_by(Book.id.desc()).all()
    return render_template("books.html", books=books, q=q)


@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    if not is_logged_in():
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "").strip()
        quantity = request.form.get("quantity", "1").strip()

        if not title or not author or not category:
            flash("Please fill all required fields.", "warning")
            return redirect(url_for("add_book"))

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity must be a positive integer.", "danger")
            return redirect(url_for("add_book"))

        book = Book(
            title=title,
            author=author,
            category=category,
            quantity=quantity,
            available_quantity=quantity,
        )
        db.session.add(book)
        db.session.commit()
        flash("Book added successfully.", "success")
        return redirect(url_for("view_books"))

    return render_template("add_book.html")


@app.route("/books/edit/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    if not is_logged_in():
        return redirect(url_for("login"))

    book = Book.query.get_or_404(book_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "").strip()
        quantity_raw = request.form.get("quantity", "1").strip()

        if not title or not author or not category:
            flash("Please fill all required fields.", "warning")
            return redirect(url_for("edit_book", book_id=book.id))

        try:
            new_quantity = int(quantity_raw)
            if new_quantity <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity must be a positive integer.", "danger")
            return redirect(url_for("edit_book", book_id=book.id))

        issued_count = book.quantity - book.available_quantity
        if new_quantity < issued_count:
            flash(
                f"Quantity cannot be less than currently issued copies ({issued_count}).",
                "danger",
            )
            return redirect(url_for("edit_book", book_id=book.id))

        book.title = title
        book.author = author
        book.category = category
        book.quantity = new_quantity
        book.available_quantity = new_quantity - issued_count

        db.session.commit()
        flash("Book updated successfully.", "success")
        return redirect(url_for("view_books"))

    return render_template("edit_book.html", book=book)


@app.route("/books/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    if not is_logged_in():
        return redirect(url_for("login"))

    book = Book.query.get_or_404(book_id)
    issued_count = book.quantity - book.available_quantity

    if issued_count > 0:
        flash("Cannot delete a book that is currently issued.", "danger")
        return redirect(url_for("view_books"))

    db.session.delete(book)
    db.session.commit()
    flash("Book deleted successfully.", "success")
    return redirect(url_for("view_books"))


@app.route("/issue", methods=["GET", "POST"])
def issue_book():
    if not is_logged_in():
        return redirect(url_for("login"))

    books = Book.query.order_by(Book.title.asc()).all()

    if request.method == "POST":
        borrower_name = request.form.get("borrower_name", "").strip()
        book_id = request.form.get("book_id", "").strip()

        if not borrower_name or not book_id:
            flash("Borrower name and book are required.", "warning")
            return redirect(url_for("issue_book"))

        book = Book.query.get(book_id)
        if not book:
            flash("Selected book not found.", "danger")
            return redirect(url_for("issue_book"))

        if book.available_quantity <= 0:
            flash("No available copies for this book.", "danger")
            return redirect(url_for("issue_book"))

        issue = IssueRecord(book_id=book.id, borrower_name=borrower_name)
        book.available_quantity -= 1
        db.session.add(issue)
        db.session.commit()

        flash("Book issued successfully.", "success")
        return redirect(url_for("issued_books"))

    return render_template("issue_book.html", books=books)


@app.route("/issued")
def issued_books():
    if not is_logged_in():
        return redirect(url_for("login"))

    records = IssueRecord.query.order_by(IssueRecord.issue_date.desc()).all()
    return render_template("issued_books.html", records=records)


@app.route("/return/<int:issue_id>", methods=["POST"])
def return_book(issue_id):
    if not is_logged_in():
        return redirect(url_for("login"))

    issue = IssueRecord.query.get_or_404(issue_id)

    if issue.returned:
        flash("Book already returned.", "info")
        return redirect(url_for("issued_books"))

    issue.returned = True
    issue.return_date = datetime.utcnow()
    issue.book.available_quantity += 1
    db.session.commit()

    flash("Book returned successfully.", "success")
    return redirect(url_for("issued_books"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
