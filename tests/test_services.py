from datetime import date, datetime, timezone

import pytest

from app import create_app
from extensions import db
from models import Book, ReadingEvent, User
from services.reading_service import get_reading_history
from services.stats_service import calculate_streak


@pytest.fixture
def app_context():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def _create_user(username="reader"):
    user = User(username=username, email=f"{username}@bookclub.test")
    db.session.add(user)
    db.session.flush()
    return user


def _create_book(title, user):
    book = Book(
        title=title,
        author="Test Author",
        pages=100,
        genre="test",
        added_by=user.id,
    )
    db.session.add(book)
    db.session.flush()
    return book


def test_calculate_streak_counts_three_consecutive_user_local_days(app_context):
    user = _create_user()
    books = [_create_book(f"Book {i}", user) for i in range(3)]

    finished_times = [
        datetime(2026, 6, 29, 4, 10, tzinfo=timezone.utc),
        datetime(2026, 6, 29, 3, 58, tzinfo=timezone.utc),
        datetime(2026, 6, 28, 3, 58, tzinfo=timezone.utc),
    ]

    for book, finished_at in zip(books, finished_times):
        db.session.add(
            ReadingEvent(
                user_id=user.id,
                book_id=book.id,
                started_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
                finished_at=finished_at,
            )
        )
    db.session.commit()

    streak = calculate_streak(
        user.id,
        user_timezone="America/New_York",
        today=date(2026, 6, 29),
    )

    assert streak == 3


def test_get_reading_history_orders_most_recently_finished_first(app_context):
    user = _create_user()
    older_started_newer_finished = _create_book("Finished Most Recently", user)
    newer_started_older_finished = _create_book("Finished Earlier", user)

    db.session.add_all(
        [
            ReadingEvent(
                user_id=user.id,
                book_id=older_started_newer_finished.id,
                started_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
                finished_at=datetime(2026, 6, 20, tzinfo=timezone.utc),
            ),
            ReadingEvent(
                user_id=user.id,
                book_id=newer_started_older_finished.id,
                started_at=datetime(2026, 6, 10, tzinfo=timezone.utc),
                finished_at=datetime(2026, 6, 15, tzinfo=timezone.utc),
            ),
        ]
    )
    db.session.commit()

    history = get_reading_history(user.id)

    assert [event.book.title for event in history] == [
        "Finished Most Recently",
        "Finished Earlier",
    ]
