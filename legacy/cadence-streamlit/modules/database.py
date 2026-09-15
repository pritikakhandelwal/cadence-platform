import sqlite3
import os


DB_PATH = "database/cadence.db"


# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def get_connection():
    """
    Create a hardened connection to the SQLite database.

    Pragmas applied on every connection:
    - WAL journal mode  : better read/write concurrency, crash-safe
    - foreign_keys ON   : enforce referential integrity
    - busy_timeout      : wait up to 5 s instead of failing immediately on lock
    """

    os.makedirs("database", exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


# ==========================================================
# CREATE TABLES
# ==========================================================

def create_tables():
    """
    Create all required database tables.
    """

    conn = get_connection()

    cursor = conn.cursor()

    # ==========================================================
    # USERS TABLE
    # ==========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            joined_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS login_security(

            email TEXT PRIMARY KEY,

            failed_attempts INTEGER NOT NULL DEFAULT 0,

            locked_until TEXT,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    # ==========================================================
    # ANALYSIS TABLE
    # ==========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            similarity REAL NOT NULL,

            dtw_distance REAL NOT NULL,

            feedback TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(user_id)
            REFERENCES users(id)

        )
        """
    )

    conn.commit()

    conn.close()


# ==========================================================
# SAVE ANALYSIS
# ==========================================================

def save_analysis(
    user_id,
    similarity,
    dtw_distance,
    feedback
):
    """
    Save one completed dance analysis with sanitized metrics.
    """

    try:
        clean_user_id = int(user_id)
        clean_similarity = max(0.0, min(100.0, float(similarity)))
        clean_distance = max(0.0, float(dtw_distance))
        clean_feedback = str(feedback)[:2000] if feedback is not None else ""
    except (TypeError, ValueError) as err:
        raise ValueError(f"Invalid analysis parameters: {err}") from err

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO analysis(

            user_id,

            similarity,

            dtw_distance,

            feedback

        )

        VALUES(?,?,?,?)

        """,
        (
            clean_user_id,
            clean_similarity,
            clean_distance,
            clean_feedback
        )
    )

    conn.commit()

    conn.close()


# ==========================================================
# GET ALL ANALYSES OF A USER
# ==========================================================

def get_user_analyses(user_id):
    """
    Return all analyses belonging to a user.
    """

    clean_user_id = int(user_id)

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT

            similarity,

            dtw_distance,

            feedback,

            created_at

        FROM analysis

        WHERE user_id=?

        ORDER BY created_at DESC

        """,
        (clean_user_id,)
    )

    analyses = cursor.fetchall()

    conn.close()

    return analyses


# ==========================================================
# GET USER STATISTICS
# ==========================================================

def get_user_statistics(user_id):
    """
    Returns:
    Total analyses,
    Best similarity,
    Average similarity,
    Latest similarity
    """

    clean_user_id = int(user_id)

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT

            COUNT(*),

            MAX(similarity),

            AVG(similarity)

        FROM analysis

        WHERE user_id=?

        """,
        (clean_user_id,)
    )

    total, best, average = cursor.fetchone()

    cursor.execute(
        """
        SELECT similarity

        FROM analysis

        WHERE user_id=?

        ORDER BY created_at DESC

        LIMIT 1

        """,
        (clean_user_id,)
    )

    latest = cursor.fetchone()

    conn.close()

    return (
        total or 0,
        best or 0,
        average or 0,
        latest[0] if latest else 0
    )


# ==========================================================
# GET SIMILARITY HISTORY
# ==========================================================

def get_similarity_history(user_id):
    """
    Returns similarity history ordered by date.
    """

    clean_user_id = int(user_id)

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT

            created_at,

            similarity

        FROM analysis

        WHERE user_id=?

        ORDER BY created_at ASC

        """,
        (clean_user_id,)
    )

    history = cursor.fetchall()

    conn.close()

    return history


# ==========================================================
# GET ACHIEVEMENT DATA
# ==========================================================

def get_achievement_data(user_id):
    """
    Returns:
    Total analyses,
    Best similarity,
    Average similarity
    """

    clean_user_id = int(user_id)

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT

            COUNT(*),

            MAX(similarity),

            AVG(similarity)

        FROM analysis

        WHERE user_id=?

        """,
        (clean_user_id,)
    )

    total, best, average = cursor.fetchone()

    conn.close()

    return (

        total or 0,

        best or 0,

        average or 0

    )
