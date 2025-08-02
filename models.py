import sqlite3


def create_db(db):
    sqlite3.connect(db).close()


def ensure_table(file):
    db = sqlite3.connect(file)
    """Initialize database tables and indexes if they don't exist."""
    # Create users table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            hash TEXT NOT NULL,
            cash NUMERIC NOT NULL DEFAULT 10000.00
        )
    """
    )

    # Create holdings table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS holdings (
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            shares INTEGER NOT NULL,
            avg_price NUMERIC NOT NULL,
            cur_price NUMERIC NOT NULL,
            cost_basis NUMERIC NOT NULL,
            present_value NUMERIC,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """
    )

    # Create operations table for transaction history
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS operations (user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            shares INTEGER NOT NULL,
            price NUMERIC NOT NULL,
            total NUMERIC NOT NULL,
            timestamp DATETIME NOT NULL,
            type TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """
    )

    index = db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='username';"
    ).fetchone()

    if not index:
        db.execute("CREATE UNIQUE INDEX username ON users (username)")
