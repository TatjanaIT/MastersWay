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


# Helpers

def random_date_within_6_months():
    now = datetime.now()
    return now - timedelta(days=random.randint(0, 180))


def random_created_updated_last_6_months():
    now = datetime.now()
    created_at = now - timedelta(days=random.randint(0, 180))

    diff = now - created_at
    total_seconds = int(diff.total_seconds())
    shift_seconds = random.randint(0, total_seconds) if total_seconds > 0 else 0
    updated_at = created_at + timedelta(seconds=shift_seconds)
    return created_at, updated_at


# 1) PROJECTS

def seed_projects(cur):
    cur.execute("SELECT uuid FROM users WHERE is_mentor = FALSE;")
    students = [row[0] for row in cur.fetchall()]
    if not students:
        print("  [!] Нет студентов — сначала seed_users_block")
        return []

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
    return project_uuids


# 2) USERS_PROJECTS (assignments)

def seed_users_projects(cur):
    print("  -> Seeding users_projects...")

    cur.execute("SELECT uuid FROM users WHERE is_mentor = FALSE;")
    user_ids = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT uuid FROM projects WHERE is_deleted = FALSE;")
    project_ids = [row[0] for row in cur.fetchall()]

    if not (user_ids and project_ids):
        print("  [!] Skipping users_projects — no users or no projects found.")
        return 0

    inserted_attempts = 0
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
            inserted_attempts += 1

    print(f"  <- users_projects done (attempted {inserted_attempts})")
    return inserted_attempts


# 3) WAYS for users_projects (core)

def seed_ways_for_users_projects(cur):
    """
    Создаём ways (задачи) для каждой пары user×project из users_projects.
    Важно:
      - ways.owner_uuid = user_uuid (студент)
      - ways.project_uuid = project_uuid
      - прогресс распределяем реалистично
    """
    print("  -> Seeding ways for users_projects...")

    cur.execute(f"SELECT user_uuid, project_uuid FROM {SCHEMA}.users_projects;")
    pairs = cur.fetchall()
    if not pairs:
        print("  [!] users_projects пустая — сначала seed_users_projects")
        return 0

    ways_created = 0

    # Распределение прогресса (можешь подкрутить веса)
    progress_values = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    progress_weights = [25, 20, 18, 15, 12, 10]

    for user_uuid, project_uuid in pairs:
        total_tasks = random.randint(5, 20)

        progress_ratio = random.choices(progress_values, weights=progress_weights, k=1)[0]
        completed_tasks = int(round(total_tasks * progress_ratio))

        for i in range(total_tasks):
            created_at, updated_at = random_created_updated_last_6_months()
            name = random.choice(way_names)
            goal_description = f"Task in project: {name}"

            estimation_time = random.randint(10, 80)
            is_completed = i < completed_tasks
            is_private = False

            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.ways
                    (uuid, name, goal_description, updated_at, created_at,
                     estimation_time, owner_uuid, copied_from_way_uuid,
                     is_completed, is_private, project_uuid)
                VALUES
                    (gen_random_uuid(), %s, %s, %s, %s,
                     %s, %s, NULL,
                     %s, %s, %s);
                """,
                (
                    name,
                    goal_description,
                    updated_at,
                    created_at,
                    estimation_time,
                    user_uuid,          # <-- студент
                    is_completed,
                    is_private,
                    project_uuid,
                ),
            )
            ways_created += 1

    print(f"  <- ways created: {ways_created}")
    return ways_created


# 4) WAY_TAGS

def seed_way_tags(cur):
    print("  Seeding way_tags...")

    cur.execute("SELECT name FROM way_tags;")
    existing = {row[0] for row in cur.fetchall()}

    inserted = 0
    for name in WAY_TAGS:
        if name in existing:
            continue

        cur.execute(
            f"INSERT INTO {SCHEMA}.way_tags (uuid, name) VALUES (gen_random_uuid(), %s);",
            (name,),
        )
        inserted += 1

    print(f"  way_tags: +{inserted}, всего {len(WAY_TAGS)}")


# 5) WAY_COLLECTIONS

def seed_way_collections(cur):
    print("  Seeding way_collections...")

    cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.way_collections;")
    if cur.fetchone()[0] > 0:
        print("  way_collections уже существуют — пропускаю")
        return

    cur.execute(f"SELECT uuid FROM {SCHEMA}.users;")
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
            f"""
            INSERT INTO {SCHEMA}.way_collections
                (uuid, owner_uuid, created_at, updated_at, name, type)
            VALUES
                (gen_random_uuid(), %s, %s, %s, %s, %s);
            """,
            (owner_uuid, created_at, updated_at, name, type_),
        )
        inserted += 1

    print(f"  way_collections inserted: {inserted}")


# 6) WAYS_WAY_TAGS

def seed_ways_way_tags(cur):
    print("  Seeding ways_way_tags...")

    cur.execute(f"SELECT uuid FROM {SCHEMA}.ways;")
    ways = [row[0] for row in cur.fetchall()]

    cur.execute(f"SELECT uuid FROM {SCHEMA}.way_tags;")
    tags = [row[0] for row in cur.fetchall()]

    if not ways or not tags:
        print("  [!] ways или way_tags пусты")
        return

    for way_uuid in ways:
        for tag_uuid in random.sample(tags, min(random.randint(1, 3), len(tags))):
            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.ways_way_tags (way_uuid, way_tag_uuid)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (way_uuid, tag_uuid),
            )

    print("  ways_way_tags done")


# 7) COLLECTIONS + COMPOSITES (FIX: limit 100 ways/collection)

def seed_collections_and_composites(cur):
    print("  Seeding way_collections_ways & composite_ways...")

    MAX_WAYS_PER_COLLECTION = 100

    cur.execute(f"SELECT uuid FROM {SCHEMA}.way_collections;")
    collections = [row[0] for row in cur.fetchall()]

    cur.execute(f"SELECT uuid FROM {SCHEMA}.ways;")
    ways = [row[0] for row in cur.fetchall()]

    if not collections or not ways:
        print("  [!] Нет коллекций или путей")
        return

    # текущие количества ways в коллекциях
    cur.execute(f"""
        SELECT way_collection_uuid, COUNT(*)::int
        FROM {SCHEMA}.way_collections_ways
        GROUP BY way_collection_uuid;
    """)
    coll_cnt = {row[0]: row[1] for row in cur.fetchall()}

    wcw_inserted = 0
    random.shuffle(ways)

    for way_uuid in ways:
        available = [c for c in collections if coll_cnt.get(c, 0) < MAX_WAYS_PER_COLLECTION]
        if not available:
            break

        k = random.randint(1, 3)
        k = min(k, len(available))
        chosen = random.sample(available, k)

        for coll_uuid in chosen:
            if coll_cnt.get(coll_uuid, 0) >= MAX_WAYS_PER_COLLECTION:
                continue

            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.way_collections_ways (way_collection_uuid, way_uuid)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (coll_uuid, way_uuid),
            )

            if cur.rowcount == 1:
                coll_cnt[coll_uuid] = coll_cnt.get(coll_uuid, 0) + 1
                wcw_inserted += 1

    print(f"  way_collections_ways inserted: {wcw_inserted}")

    # composite_ways
    comp_inserted = 0
    for parent_uuid in ways:
        pool = [w for w in ways if w != parent_uuid]
        if not pool:
            continue
        children = random.sample(pool, random.randint(0, min(2, len(pool))))
        for child_uuid in children:
            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.composite_ways (child_uuid, parent_uuid)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (child_uuid, parent_uuid),
            )
            comp_inserted += 1

    print(f"  composite_ways inserted: {comp_inserted}")


# MAIN (FIX: commit after core)

def seed_ways_block():
    print("=== Seeding WAYS BLOCK ===")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {SCHEMA}, public;")

        # 1) CORE (commit even if later steps fail)
        seed_projects(cur)
        seed_users_projects(cur)
        seed_ways_for_users_projects(cur)

        conn.commit()
        print("  [OK] Core (projects/users_projects/ways) committed")

        # 2) WRAPPERS
        seed_way_tags(cur)
        seed_way_collections(cur)
        seed_ways_way_tags(cur)
        seed_collections_and_composites(cur)

        conn.commit()
        print("=== WAYS BLOCK COMPLETED ===")

    except Exception as e:
        conn.rollback()
        print("Error in ways block:", e)
    finally:
        conn.close()


if __name__ == "__main__":
    seed_ways_block()
