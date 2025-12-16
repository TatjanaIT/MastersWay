import random
from datetime import datetime, timedelta
from faker import Faker

from db.connection import get_connection
from config import settings, seed_config

fake = Faker("ru_RU")

SCHEMA = settings.SCHEMA
WAY_TAGS = seed_config.WAY_TAGS

project_titles = seed_config.PROJECTS_TITLES
projects_count = seed_config.PROJECTS_COUNT
way_names = seed_config.WAY_NAMES
titles = seed_config.TITLES
types = seed_config.TYPES

# Helper functions
def random_date_within_6_months():
    today = datetime.now()
    delta_days = random.randint(0, 180)
    return today - timedelta(days=delta_days)

def random_created_updated_last_6_months():
    now = datetime.now()

    # created_at: от 0 до 180 дней назад
    created_at = now - timedelta(days=random.randint(0, 180))

    # сколько времени между created_at и сейчас
    diff = now - created_at
    total_seconds = int(diff.total_seconds())
    if total_seconds <= 0:
        return created_at, now

    # выбираем случайный сдвиг в секундах
    shift_seconds = random.randint(0, total_seconds)
    updated_at = created_at + timedelta(seconds=shift_seconds)

    return created_at, updated_at


# 1. PROJECTS + WAYS
def seed_projects_and_ways(cur):
    cur.execute("SELECT uuid FROM users WHERE is_mentor = TRUE;")
    mentors = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT uuid FROM users WHERE is_mentor = FALSE;")
    students = [row[0] for row in cur.fetchall()]

    if not mentors or not students:
        print("  [!] Нет менторов или студентов — сначала seed_users_block")
        return

    # projects
    project_uuids = []

    for _ in range(projects_count):
        title = random.choice(project_titles)
        owner_uuid = random.choice(students)
        is_private = random.choice([True, False])
        is_deleted = False

        cur.execute(
            """
            INSERT INTO projects (uuid, name, owner_uuid, is_private, is_deleted)
            VALUES (gen_random_uuid(), %s, %s, %s, %s)
            RETURNING uuid;
            """,
            (title, owner_uuid, is_private, is_deleted),
        )

        project_uuids.append(cur.fetchone()[0])

    print(f" Projects created: {len(project_uuids)}")

    # ways
    ways_created = 0

    for name in way_names:
        goal_description = f"Обучающий путь: {name}."

        created_at, updated_at = random_created_updated_last_6_months()

        estimation_time = random.randint(10, 80)
        owner_uuid = random.choice(mentors)
        is_completed = random.choice([True, False])
        is_private = random.choice([True, False])

        project_uuid = (
            random.choice(project_uuids) if project_uuids and random.random() < 0.7 else None
        )

        cur.execute(
            """
            INSERT INTO ways
                (uuid, name, goal_description, updated_at, created_at, estimation_time, owner_uuid,
                 copied_from_way_uuid, is_completed, is_private, project_uuid)
            VALUES
                (gen_random_uuid(), %s, %s, %s, %s, %s, %s,
                 NULL, %s, %s,%s);
            """,
            (
                name, goal_description, updated_at, created_at, estimation_time, owner_uuid,
                is_completed, is_private, project_uuid,
            ),
        )

        ways_created += 1

    print(f"  Ways created: {ways_created}")


# 2. WAY_TAGS
def seed_way_tags(cur):
    print("  Seeding way_tags...")

    cur.execute("SELECT name FROM way_tags;")
    existing = {row[0] for row in cur.fetchall()}

    inserted = 0
    for name in WAY_TAGS:
        if name in existing:
            continue

        cur.execute(
            "INSERT INTO way_tags (uuid, name) VALUES (gen_random_uuid(), %s);",
            (name,),
        )
        inserted += 1

    print(f"  way_tags: +{inserted}, всего {len(WAY_TAGS)}")


# 3. WAY_COLLECTIONS
def seed_way_collections(cur):
    print("  Seeding way_collections...")

    cur.execute("SELECT COUNT(*) FROM way_collections;")
    if cur.fetchone()[0] > 0:
        print("  way_collections уже существуют — пропускаю")
        return

    cur.execute("SELECT uuid FROM users;")
    users = [row[0] for row in cur.fetchall()]
    if not users:
        print("  [!] Нет пользователей для коллекций")
        return

    inserted = 0
    for _ in range(10):
        owner_uuid = random.choice(users)
        name = random.choice(titles) + " " + fake.word()
        type_ = random.choice(types)

        created_at, updated_at = random_created_updated_last_6_months()

        cur.execute(
            """
            INSERT INTO way_collections
                (uuid, owner_uuid, created_at, updated_at, name, type)
            VALUES
                (gen_random_uuid(), %s, %s, %s, %s, %s);
            """,
            (owner_uuid, created_at, updated_at, name, type_),
        )

        inserted += 1

    print(f"  way_collections inserted: {inserted}")


#4. WAYS_WAY_TAGS
def seed_ways_way_tags(cur):
    print("  Seeding ways_way_tags...")

    cur.execute("SELECT uuid FROM ways;")
    ways = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT uuid FROM way_tags;")
    tags = [row[0] for row in cur.fetchall()]

    if not ways or not tags:
        print("  [!] ways или way_tags пусты")
        return

    for way_uuid in ways:
        for tag_uuid in random.sample(tags, min(random.randint(1, 3), len(tags))):
            cur.execute(
                """
                INSERT INTO ways_way_tags (way_uuid, way_tag_uuid)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (way_uuid, tag_uuid),
            )

    print("  ways_way_tags done")

# 5. COLLECTIONS + COMPOSITES 
def seed_collections_and_composites(cur):
    print("  Seeding way_collections_ways & composite_ways...")

    cur.execute("SELECT uuid FROM way_collections;")
    collections = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT uuid FROM ways;")
    ways = [row[0] for row in cur.fetchall()]

    if not collections or not ways:
        print("  [!] Нет коллекций или путей")
        return

    wcw_inserted = 0
    for way_uuid in ways:
        for coll_uuid in random.sample(collections, min(3, len(collections))):
            cur.execute(
                """
                INSERT INTO way_collections_ways (way_collection_uuid, way_uuid)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (coll_uuid, way_uuid),
            )
            wcw_inserted += 1

    print(f"  way_collections_ways inserted: {wcw_inserted}")

    # composite_ways
    comp_inserted = 0
    for parent_uuid in ways:
        children = random.sample(
            [w for w in ways if w != parent_uuid],
            random.randint(0, 2),
        )
        for child_uuid in children:
            cur.execute(
                """
                INSERT INTO composite_ways (child_uuid, parent_uuid)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (child_uuid, parent_uuid),
            )
            comp_inserted += 1

    print(f"  composite_ways inserted: {comp_inserted}")

# 6. USERS_PROJECTS 
def seed_users_projects(cur):
    print("  -> Seeding users_projects...")

    # Students
    cur.execute(f"SELECT uuid FROM {SCHEMA}.users WHERE is_mentor = FALSE;")
    user_ids = [row[0] for row in cur.fetchall()]

    # Projects
    cur.execute(f"SELECT uuid FROM {SCHEMA}.projects;")
    project_ids = [row[0] for row in cur.fetchall()]

    if not (user_ids and project_ids):
        print("  [!] Skipping users_projects — no users or no projects found.")
        return

    inserted = 0

    for uid in user_ids:
        for _ in range(random.randint(1, 3)):
            created_at = random_date_within_6_months()

            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.users_projects
                    (user_uuid, project_uuid, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (uid, random.choice(project_ids), created_at),
            )
            inserted += 1

    print(f"  <- users_projects done (inserted {inserted})")

# MAIN FUNCTION 
def seed_ways_block():
    print("=== Seeding WAYS BLOCK ===")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {SCHEMA}, public;")

        seed_projects_and_ways(cur)
        seed_way_tags(cur)
        seed_way_collections(cur)
        seed_ways_way_tags(cur)
        seed_collections_and_composites(cur)
        seed_users_projects(cur)

        conn.commit()
        print("=== WAYS BLOCK COMPLETED ===")
    except Exception as e:
        conn.rollback()
        print("Error in ways block:", e)
    finally:
        conn.close()


if __name__ == "__main__":
    seed_ways_block()