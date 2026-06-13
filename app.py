from datetime import datetime, timedelta, timezone
from decimal import Decimal

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

BORROWING_PERIOD_DAYS = 14
FINE_PER_DAY = Decimal("5.00")
SCHEMA_READY = False

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

    @property
    def has_pending_reservations(self):
        """Returns True if book has pending reservations."""
        return db.session.query(
            Reservation.query.filter_by(
                book_id=self.id,
                status="Pending",
            ).exists()
        ).scalar()


class IssueRecord(db.Model):
    """Tracks issued books, return state and fines."""

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    borrower_name = db.Column(db.String(120), nullable=False)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    returned = db.Column(db.Boolean, default=False)
    return_date = db.Column(db.DateTime, nullable=True)
    late_days = db.Column(db.Integer, default=0)
    fine_amount = db.Column(db.Numeric(10, 2), default=0)
    fine_paid = db.Column(db.Boolean, default=False)

    book = db.relationship("Book", backref=db.backref("issues", lazy=True))


class Reservation(db.Model):
    """Tracks book reservations."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(120), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    reservation_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default="Pending")

    book = db.relationship("Book", backref=db.backref("reservations", lazy=True))

    @classmethod
    def get_pending_for_book(cls, book_id):
        """Returns pending reservations for a book."""
        return cls.query.filter_by(
            book_id=book_id,
            status="Pending",
        ).order_by(cls.reservation_date.asc()).all()


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


def calculate_fine(due_date, return_date):
    """Return late days and fine amount using date-only comparison."""
    if not due_date or not return_date:
        return 0, Decimal("0.00")

    late_days = max(0, (return_date.date() - due_date.date()).days)
    return late_days, FINE_PER_DAY * late_days


def activate_next_reservation(book_id):
    """Activate the oldest pending reservation when a copy is available."""
    book = Book.query.get(book_id)
    if not book or book.available_quantity <= 0:
        return None

    active_reservation = Reservation.query.filter_by(
        book_id=book_id,
        status="Active",
    ).first()
    if active_reservation:
        return None

    pending_reservation = Reservation.query.filter_by(
        book_id=book_id,
        status="Pending",
    ).order_by(Reservation.reservation_date.asc()).first()

    if pending_reservation:
        pending_reservation.status = "Active"

    return pending_reservation


def run_schema_updates():
    """Apply backward-compatible SQLite updates for existing databases."""
    with db.engine.begin() as connection:
        issue_columns = {
            row[1] for row in connection.exec_driver_sql("PRAGMA table_info(issue_record)")
        }
        if "due_date" not in issue_columns:
            connection.exec_driver_sql("ALTER TABLE issue_record ADD COLUMN due_date DATETIME")
        if "fine_amount" not in issue_columns:
            connection.exec_driver_sql(
                "ALTER TABLE issue_record ADD COLUMN fine_amount DECIMAL(10,2) DEFAULT 0"
            )
        if "late_days" not in issue_columns:
            connection.exec_driver_sql(
                "ALTER TABLE issue_record ADD COLUMN late_days INTEGER DEFAULT 0"
            )
        if "fine_paid" not in issue_columns:
            connection.exec_driver_sql(
                "ALTER TABLE issue_record ADD COLUMN fine_paid BOOLEAN DEFAULT 0"
            )

        connection.exec_driver_sql(
            """
            CREATE INDEX IF NOT EXISTS idx_issue_overdue
            ON issue_record(returned, due_date)
            """
        )
        connection.exec_driver_sql(
            """
            CREATE INDEX IF NOT EXISTS idx_reservation_book_status
            ON reservation(book_id, status, reservation_date)
            """
        )
        connection.exec_driver_sql(
            """
            CREATE INDEX IF NOT EXISTS idx_reservation_user_status
            ON reservation(user_id, status)
            """
        )
        connection.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_open_reservation_user_book
            ON reservation(user_id, book_id)
            WHERE status IN ('Pending', 'Active')
            """
        )
        connection.exec_driver_sql(
            """
            UPDATE issue_record
            SET due_date = datetime(issue_date, '+14 days')
            WHERE due_date IS NULL AND issue_date IS NOT NULL
            """
        )
        connection.exec_driver_sql(
            """
            UPDATE issue_record
            SET fine_amount = 0
            WHERE fine_amount IS NULL OR fine_amount < 0
            """
        )
        connection.exec_driver_sql(
            """
            UPDATE issue_record
            SET late_days = 0
            WHERE late_days IS NULL OR late_days < 0
            """
        )


@app.route("/")
def home():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.before_request
def prepare_database():
    global SCHEMA_READY
    if not SCHEMA_READY:
        db.create_all()
        run_schema_updates()
        SCHEMA_READY = True


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
    total_reservations = Reservation.query.count()
    pending_reservations = Reservation.query.filter_by(status="Pending").count()
    active_reservations = Reservation.query.filter_by(status="Active").count()
    total_fine_collected = (
        db.session.query(db.func.coalesce(db.func.sum(IssueRecord.fine_amount), 0))
        .filter(IssueRecord.fine_paid.is_(True))
        .scalar()
    )
    pending_fine_amount = (
        db.session.query(db.func.coalesce(db.func.sum(IssueRecord.fine_amount), 0))
        .filter(IssueRecord.fine_paid.is_(False), IssueRecord.fine_amount > 0)
        .scalar()
    )
    overdue_books = IssueRecord.query.filter(
        IssueRecord.returned.is_(False),
        IssueRecord.due_date < datetime.utcnow(),
    ).count()

    recent_issues = (
        IssueRecord.query.order_by(IssueRecord.issue_date.desc()).limit(5).all()
    )

    return render_template(
        "dashboard.html",
        total_books=total_books,
        issued_books=issued_books,
        available_books=available_books,
        total_titles=total_titles,
        total_reservations=total_reservations,
        pending_reservations=pending_reservations,
        active_reservations=active_reservations,
        total_fine_collected=total_fine_collected,
        pending_fine_amount=pending_fine_amount,
        overdue_books=overdue_books,
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

    open_reservation = Reservation.query.filter(
        Reservation.book_id == book.id,
        Reservation.status.in_(["Pending", "Active"]),
    ).first()
    if open_reservation:
        flash("Cannot delete a book with pending or active reservations.", "danger")
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

        issue_date = datetime.utcnow()
        issue = IssueRecord(
            book_id=book.id,
            borrower_name=borrower_name,
            issue_date=issue_date,
            due_date=issue_date + timedelta(days=BORROWING_PERIOD_DAYS),
        )
        book.available_quantity -= 1

        active_reservation = Reservation.query.filter_by(
            book_id=book.id,
            user_id=borrower_name,
            status="Active",
        ).first()
        if active_reservation:
            active_reservation.status = "Completed"

        db.session.add(issue)
        db.session.commit()

        flash("Book issued successfully.", "success")
        return redirect(url_for("issued_books"))

    return render_template("issue_book.html", books=books)


@app.route("/issued")
def issued_books():
    if not is_logged_in():
        return redirect(url_for("login"))

    q = request.args.get("q", "").strip()
    records_query = IssueRecord.query
    if q:
        records_query = records_query.filter(IssueRecord.borrower_name.like(f"%{q}%"))

    records = records_query.order_by(IssueRecord.issue_date.desc()).all()
    return render_template("issued_books.html", records=records, q=q)


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
    issue.late_days, issue.fine_amount = calculate_fine(issue.due_date, issue.return_date)

    issue.book.available_quantity += 1
    activated_reservation = activate_next_reservation(issue.book_id)

    if activated_reservation:
        flash(
            f"Book returned successfully. Reservation activated for {activated_reservation.user_id}.",
            "success",
        )
    else:
        flash("Book returned successfully.", "success")

    db.session.commit()
    return redirect(url_for("issued_books"))


@app.route("/books/<int:book_id>/reserve", methods=["POST"])
def reserve_book(book_id):
    if not is_logged_in():
        return redirect(url_for("login"))

    book = Book.query.get_or_404(book_id)
    user_id = request.form.get("user_id", "").strip()

    if not user_id:
        flash("Borrower name is required to reserve a book.", "warning")
        return redirect(url_for("view_books"))

    if book.available_quantity > 0:
        flash("This book is currently available. Please issue it instead of reserving.", "info")
        return redirect(url_for("view_books"))

    duplicate = Reservation.query.filter(
        Reservation.book_id == book.id,
        Reservation.user_id == user_id,
        Reservation.status.in_(["Pending", "Active"]),
    ).first()
    if duplicate:
        flash("This user already has an open reservation for this book.", "warning")
        return redirect(url_for("view_books"))

    reservation = Reservation(
        user_id=user_id,
        book_id=book.id,
        reservation_date=datetime.utcnow(),
        status="Pending",
    )
    db.session.add(reservation)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Could not create reservation. Please check for duplicate reservations.", "danger")
        return redirect(url_for("view_books"))

    flash("Book reserved successfully. Status: Pending.", "success")
    return redirect(url_for("view_books"))


@app.route("/reservations")
def reservations():
    if not is_logged_in():
        return redirect(url_for("login"))

    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    reservations_query = Reservation.query.join(Book)

    if q:
        pattern = f"%{q}%"
        reservations_query = reservations_query.filter(
            db.or_(
                Reservation.user_id.like(pattern),
                Book.title.like(pattern),
                Book.author.like(pattern),
            )
        )

    if status in ["Pending", "Active", "Completed", "Cancelled"]:
        reservations_query = reservations_query.filter(Reservation.status == status)

    reservation_records = reservations_query.order_by(
        Reservation.reservation_date.desc()
    ).all()
    return render_template(
        "reservations.html",
        reservations=reservation_records,
        q=q,
        status=status,
    )


@app.route("/my-reservations", methods=["GET", "POST"])
def my_reservations():
    if not is_logged_in():
        return redirect(url_for("login"))

    user_id = request.values.get("user_id", "").strip()
    reservation_records = []
    if user_id:
        reservation_records = Reservation.query.filter_by(user_id=user_id).order_by(
            Reservation.reservation_date.desc()
        ).all()

    return render_template(
        "my_reservations.html",
        reservations=reservation_records,
        user_id=user_id,
    )


@app.route("/reservations/<int:reservation_id>/cancel", methods=["POST"])
def cancel_reservation(reservation_id):
    if not is_logged_in():
        return redirect(url_for("login"))

    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.status not in ["Pending", "Active"]:
        flash("Only pending or active reservations can be cancelled.", "warning")
    else:
        reservation.status = "Cancelled"
        activate_next_reservation(reservation.book_id)
        db.session.commit()
        flash("Reservation cancelled successfully.", "success")

    next_url = request.form.get("next") or url_for("reservations")
    return redirect(next_url)


@app.route("/fines")
def fines():
    if not is_logged_in():
        return redirect(url_for("login"))

    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    fines_query = IssueRecord.query.join(Book).filter(IssueRecord.fine_amount > 0)

    if q:
        pattern = f"%{q}%"
        fines_query = fines_query.filter(
            db.or_(IssueRecord.borrower_name.like(pattern), Book.title.like(pattern))
        )

    if status == "paid":
        fines_query = fines_query.filter(IssueRecord.fine_paid.is_(True))
    elif status == "unpaid":
        fines_query = fines_query.filter(IssueRecord.fine_paid.is_(False))

    fine_records = fines_query.order_by(IssueRecord.return_date.desc()).all()
    return render_template("fines.html", records=fine_records, q=q, status=status)


@app.route("/fines/<int:issue_id>/toggle-paid", methods=["POST"])
def toggle_fine_paid(issue_id):
    if not is_logged_in():
        return redirect(url_for("login"))

    issue = IssueRecord.query.get_or_404(issue_id)
    if issue.fine_amount < 0:
        issue.fine_amount = 0
    issue.fine_paid = not bool(issue.fine_paid)
    db.session.commit()
    flash("Fine payment status updated.", "success")
    return redirect(
        url_for(
            "fines",
            q=request.form.get("q", ""),
            status=request.form.get("status", ""),
        )
    )


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        run_schema_updates()
    app.run(host="0.0.0.0", port=5000, debug=True)
