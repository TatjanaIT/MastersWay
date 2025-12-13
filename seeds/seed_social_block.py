import random
from datetime import datetime, timedelta
from faker import Faker

from db.connection import get_connection
from config import settings

fake = Faker("ru_RU")
SCHEMA = settings.SCHEMA


COMMENT_TEMPLATES = [
    "Сегодня было немного сложно, но в целом материал по теме понятен.",
    "Застрял(а) на паре задач, нужно ещё раз пересмотреть теорию.",
    "Чувствую прогресс, задачи даются легче, чем раньше.",
    "Отличный день, получилось закрыть запланированный объём.",
    "Не успел(а) всё, что хотел(а), но основные цели выполнены.",
    "Есть вопросы по теме, планирую задать ментору на созвоне.",
]

def random_updated_from_created(created_at, max_shift_hours=24):
   
    now = datetime.now()
    if created_at >= now:
        return now

    diff = now - created_at
    max_seconds_allowed = min(int(diff.total_seconds()), max_shift_hours * 3600)

    if max_seconds_allowed <= 0:
        return now

    shift_seconds = random.randint(60, max_seconds_allowed)  # минимум +1 минута
    return created_at + timedelta(seconds=shift_seconds)

def generate_comment_text() -> str:
    base = random.choice(COMMENT_TEMPLATES)
    extra = fake.sentence(nb_words=8)
    text = f"{base} {extra}"
    return text[:2950]

# 1. COMMENTS
def seed_comments(cur):
    print("  -> Seeding comments...")

    # all users
    cur.execute(f"SELECT uuid FROM {SCHEMA}.users;")
    user_ids = [row[0] for row in cur.fetchall()]
    if not user_ids:
        print("  [!] ERROR: no users found")
        return

    # all day_reports
    cur.execute(f"SELECT uuid, created_at FROM {SCHEMA}.day_reports;")
    report_rows = cur.fetchall()
    if not report_rows:
        print("  [!] ERROR: no day_reports found")
        return

    total_inserted = 0

    for day_report_uuid, dr_created_at in report_rows:
        comments_count = random.randint(0, 5)  # не на каждый день комментарии

        for _ in range(comments_count):
            owner_uuid = random.choice(user_ids)
            created_at = dr_created_at + timedelta(
                minutes=random.randint(5, 240)
            )
            updated_at = random_updated_from_created(created_at, max_shift_hours=6)
            description = generate_comment_text()

            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.comments
                    (uuid, created_at, updated_at,
                     description, owner_uuid, day_report_uuid)
                VALUES
                    (gen_random_uuid(), %s, %s,
                     %s, %s, %s);
                """,
                (
                    created_at,
                    updated_at,
                    description,
                    owner_uuid,
                    day_report_uuid,
                ),
            )
            total_inserted += 1

    print(f"  <- comments done (inserted {total_inserted})")


# 2. FAVORITE_USERS
def seed_favorite_users(cur):
    print("  -> Seeding favorite_users...")

    cur.execute(f"SELECT uuid FROM {SCHEMA}.users;")
    user_ids = [row[0] for row in cur.fetchall()]
    if not user_ids:
        print("  [!] ERROR: no users found")
        return

    total_inserted = 0

    for donor_uuid in user_ids:
        possible_acceptors = [u for u in user_ids if u != donor_uuid]
        if not possible_acceptors:
            continue

        # каждый пользователь добавит 1–5 избранных
        k = min(random.randint(1, 5), len(possible_acceptors))
        chosen = random.sample(possible_acceptors, k)

        for acceptor_uuid in chosen:
            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.favorite_users
                    (donor_user_uuid, acceptor_user_uuid)
                VALUES (%s, %s);
                """,
                (donor_uuid, acceptor_uuid),
            )
            total_inserted += 1

    print(f"  <- favorite_users done (inserted {total_inserted})")


# 3. FAVORITE_USERS_WAYS
def seed_favorite_users_ways(cur):
    print("  -> Seeding favorite_users_ways...")

    cur.execute(f"SELECT uuid FROM {SCHEMA}.users;")
    user_ids = [row[0] for row in cur.fetchall()]
    if not user_ids:
        print("  [!] ERROR: no users found")
        return

    cur.execute(f"SELECT uuid FROM {SCHEMA}.ways;")
    way_ids = [row[0] for row in cur.fetchall()]
    if not way_ids:
        print("  [!] ERROR: no ways found")
        return

    total_inserted = 0

    for user_uuid in user_ids:
        k = min(random.randint(1, 4), len(way_ids))
        chosen_ways = random.sample(way_ids, k)

        for way_uuid in chosen_ways:
            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.favorite_users_ways
                    (user_uuid, way_uuid)
                VALUES (%s, %s);
                """,
                (user_uuid, way_uuid),
            )
            total_inserted += 1

    print(f"  <- favorite_users_ways done (inserted {total_inserted})")


# MAIN FUNCTION
def seed_social_block():
    print("=== Seeding SOCIAL BLOCK ===")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {SCHEMA}, public;")

        seed_comments(cur)
        seed_favorite_users(cur)
        seed_favorite_users_ways(cur)

        conn.commit()
        print("=== SOCIAL BLOCK COMPLETED ===")
    except Exception as e:
        conn.rollback()
        print("Error in social block:", e)
    finally:
        conn.close()
        

if __name__ == "__main__":
    seed_social_block()
