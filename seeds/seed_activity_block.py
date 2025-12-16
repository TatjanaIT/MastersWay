import random
from datetime import datetime, timedelta

from db.connection import get_connection
from config import settings, seed_config

SCHEMA = settings.SCHEMA
JOB_TAG_NAMES = seed_config.JOB_TAG_NAMES
TAG_COLORS = seed_config.TAG_COLORS
PLAN_TEMPLATES = seed_config.PLAN_TEMPLATES
PLAN_TOPICS = seed_config.PLAN_TOPICS
PROBLEM_TEMPLATES = seed_config.PROBLEM_TEMPLATES
PROBLEM_TOPICS = seed_config.PROBLEM_TOPICS
JOB_DONE_TEMPLATES = seed_config.JOB_DONE_TEMPLATES
JOB_DONE_TOPICS = seed_config.JOB_DONE_TOPICS

# helpers 
def random_past_date(days_back=90): #Случайная дата в прошлом (от 1 до days_back дней назад)
    today = datetime.now()
    delta = timedelta(days=random.randint(1, days_back)) 
    return today - delta

def random_updated_from_created(created_at, max_shift_hours=72):
    """
    Делает updated_at случайным моментом между created_at и сейчас,
    но не позже now. max_shift_hours ограничивает максимальный сдвиг.
    """
    now = datetime.now()

    if created_at >= now: # если вдруг created_at в будущем (на всякий случай)
        return now

    diff = now - created_at
    max_seconds = min(int(diff.total_seconds()), max_shift_hours * 3600)

    if max_seconds <= 0:
        return now

    shift_seconds = random.randint(0, max_seconds)
    return created_at + timedelta(seconds=shift_seconds)

def get_unique_date_for_way(cur, way_uuid, days_back=90, max_tries=50):
    """
    Подбирает дату, для которой ещё НЕТ отчёта для данного way_uuid.
    Проверяет day_reports по дате (created_at::date).
    """
    for _ in range(max_tries):
        dt = random_past_date(days_back)
        dt_date = dt.date()

        cur.execute(
            f"""
            SELECT 1
            FROM {SCHEMA}.day_reports
            WHERE way_uuid = %s
              AND created_at::date = %s
            """,
            (way_uuid, dt_date),
        )
        if not cur.fetchone():
            return dt

    return random_past_date(days_back)


def generate_metric_description(is_done: bool, estimation: int) -> str:
    """Описание метрики под учебную платформу."""
    tasks = [
        "урок по основам Python",
        "модуль по SQL и запросам",
        "практика по PostgreSQL",
        "домашнее задание по аналитике данных",
        "разбор задач по дашбордам",
        "проектное задание по продуктовой аналитике",
        "повторение пройденного материала",
        "созвон с ментором и разбор вопросов",
    ]

    outcomes_done = [
        "Задача выполнена, материал усвоен на хорошем уровне.",
        "Завершил(а) работу и закрепил(а) ключевые концепции.",
        "Задание закрыл(а), появилось больше уверенности в теме.",
        "Задача успешно выполнена, можно двигаться дальше.",
    ]

    outcomes_in_progress = [
        "Задача в процессе, нужно доделать оставшуюся часть.",
        "Успел(а) сделать только часть задания, планирую завершить позже.",
        "Нужно вернуться к этой задаче и довести до конца.",
        "Часть материала пока остаётся непроработанной.",
    ]

    task = random.choice(tasks)

    if is_done:
        outcome = random.choice(outcomes_done)
        status_text = "завершена"
    else:
        outcome = random.choice(outcomes_in_progress)
        status_text = "в процессе"

    description = (
        f"Учебная задача ({status_text}): {task}. "
        f"Оценка сложности по ощущениям — {estimation}/10. {outcome}"
    )
    return description[:295]


# A. day_reports + metrics 
def seed_day_reports_and_metrics(cur):
    print("  -> Seeding day_reports & metrics...")

    cur.execute(f"SELECT uuid FROM {SCHEMA}.ways;")
    way_ids = [row[0] for row in cur.fetchall()]

    if not way_ids:
        print("  [!] No ways found. Seed ways first.")
        return

    for way_uuid in way_ids:
        reports_count = random.randint(3, 8)

        for _ in range(reports_count):
            created_at = get_unique_date_for_way(cur, way_uuid, days_back=90)
            updated_at = random_updated_from_created(created_at, max_shift_hours=24)

            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.day_reports
                    (uuid, way_uuid, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), %s, %s, %s)
                RETURNING uuid;
                """,
                (way_uuid, created_at, updated_at),
            )
            
            day_report_id = cur.fetchone()[0]

            metrics_count = random.randint(2, 5)
            for _m in range(metrics_count):
                metric_created = created_at + timedelta(
                    minutes=random.randint(0, 600)
                )
                
                metric_updated = random_updated_from_created(metric_created, max_shift_hours=48)


                is_done = random.choice([True, False])
                done_date = (
                    metric_created + timedelta(hours=random.randint(1, 48))
                    if is_done
                    else None
                )

                estimation = random.randint(1, 10)
                description = generate_metric_description(is_done, estimation)

                cur.execute(
                    f"""
                    INSERT INTO {SCHEMA}.metrics
                        (uuid, created_at, updated_at, description, is_done, 
                        done_date, metric_estimation, way_uuid, parent_uuid)
                    VALUES
                        (gen_random_uuid(), %s, %s,
                        %s, %s, %s,
                        %s, %s, NULL);
                    """,
                    (
                        metric_created, metric_updated, description, is_done,
                        done_date, estimation, way_uuid,
                    ),
                )

    print("  <- day_reports & metrics done")


# B. job_tags 
def seed_job_tags(cur):
    print("  -> Seeding job_tags...")

    # получаем все пути
    cur.execute(f"SELECT uuid FROM {SCHEMA}.ways;")
    way_ids = [row[0] for row in cur.fetchall()]
    if not way_ids:
        print("  [!] No ways found. Seed ways first.")
        return

    inserted = 0

    for way_uuid in way_ids:

        # 3–6 тегов на путь
        tags_count = random.randint(3, 6)
        chosen_names = random.sample(JOB_TAG_NAMES, tags_count)

        for name in chosen_names:
            description = f"Тег для задач: {name.lower()}."
            color = random.choice(TAG_COLORS)

            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.job_tags
                    (uuid, name, description, color, way_uuid)
                VALUES
                    (gen_random_uuid(), %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (name, description, color, way_uuid),
            )

            inserted += 1

    print(f"  <- job_tags done (inserted {inserted})")


# C. plans 
def generate_plan_description():
    topic = random.choice(PLAN_TOPICS)
    template = random.choice(PLAN_TEMPLATES)
    return template.format(topic=topic)

def seed_plans(cur):
    print("  -> Seeding plans...")

    cur.execute(f"SELECT uuid FROM {SCHEMA}.users;")
    user_ids = [row[0] for row in cur.fetchall()]
    if not user_ids:
        print("  [!] No users found. Seed users first.")
        return

    cur.execute(f"SELECT uuid, created_at FROM {SCHEMA}.day_reports;")
    reports = cur.fetchall()
    if not reports:
        print("  [!] No day_reports found.")
        return

    for day_report_uuid, created_at in reports:
        plans_count = random.randint(2, 5)
        owner_uuid = random.choice(user_ids)

        for _ in range(plans_count):
            description = generate_plan_description()
            time_spent = random.randint(10, 120)
            is_done = random.choice([True, False])
            updated_at = random_updated_from_created(created_at, max_shift_hours=72)

            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.plans
                    (uuid, created_at, updated_at, description, time, 
                    owner_uuid, is_done, day_report_uuid)
                VALUES
                    (gen_random_uuid(), %s, %s, %s,
                     %s, %s, %s, %s);
                """,
                (
                    created_at, updated_at, description, time_spent,
                    owner_uuid, is_done, day_report_uuid,
                ),
            )

    print("  <- plans done")


# D. plans_job_tags 
def seed_plans_job_tags(cur):
    print("  -> Seeding plans_job_tags...")

    cur.execute(f"SELECT uuid, way_uuid FROM {SCHEMA}.job_tags;")
    rows = cur.fetchall()
    if not rows:
        print("  [!] No job_tags found. Seed job_tags first.")
        return

    job_tags_by_way = {}
    for job_tag_uuid, way_uuid in rows:
        job_tags_by_way.setdefault(way_uuid, []).append(job_tag_uuid)

    cur.execute(
        f"""
        SELECT p.uuid AS plan_uuid,
               dr.way_uuid AS way_uuid
        FROM {SCHEMA}.plans p
        JOIN {SCHEMA}.day_reports dr
          ON p.day_report_uuid = dr.uuid;
        """
    )
    plan_rows = cur.fetchall()
    if not plan_rows:
        print("  [!] No plans found.")
        return

    inserted = 0
    for plan_uuid, way_uuid in plan_rows:
        tags_for_way = job_tags_by_way.get(way_uuid)
        if not tags_for_way:
            continue

        k = min(random.randint(1, 3), len(tags_for_way))
        chosen_tags = random.sample(tags_for_way, k)

        for job_tag_uuid in chosen_tags:
            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.plans_job_tags
                    (plan_uuid, job_tag_uuid)
                VALUES
                    (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (plan_uuid, job_tag_uuid),
            )
            inserted += 1

    print(f"  <- plans_job_tags done (inserted {inserted})")


# E. problems 
def generate_problem_description():
    topic = random.choice(PROBLEM_TOPICS)
    n = random.randint(3, 10)
    template = random.choice(PROBLEM_TEMPLATES)
    text = template.format(topic=topic, n=n)
    return text if len(text) <= 2950 else text[:2950]

def seed_problems(cur):
    print("  -> Seeding problems...")

    cur.execute(f"SELECT uuid FROM {SCHEMA}.users;")
    user_ids = [row[0] for row in cur.fetchall()]
    if not user_ids:
        print("  [!] No users found.")
        return

    cur.execute(f"SELECT uuid, created_at FROM {SCHEMA}.day_reports;")
    report_rows = cur.fetchall()
    if not report_rows:
        print("  [!] No day_reports found.")
        return

    for day_report_uuid, created_at in report_rows:
        owner_uuid = random.choice(user_ids)
        problems_count = random.randint(2, 6)

        for _ in range(problems_count):
            description = generate_problem_description()
            is_done = random.choice([True, False])
            updated_at = random_updated_from_created(created_at, max_shift_hours=72)

            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.problems
                    (uuid, created_at, updated_at,
                     description, is_done, owner_uuid, day_report_uuid)
                VALUES
                    (gen_random_uuid(), %s, %s,
                     %s, %s, %s, %s);
                """,
                (
                    created_at, updated_at, description, is_done,
                    owner_uuid, day_report_uuid,
                ),
            )

    print("  <- problems done")


# F. job_dones
def generate_job_done_description():
    topic = random.choice(JOB_DONE_TOPICS)
    template = random.choice(JOB_DONE_TEMPLATES)
    return template.format(topic=topic)[:2900]


def seed_job_dones(cur):
    print("  -> Seeding job_dones...")

    cur.execute(f"SELECT uuid FROM {SCHEMA}.users;")
    users = [row[0] for row in cur.fetchall()]
    if not users:
        print("  [!] No users found.")
        return

    cur.execute(f"SELECT uuid, created_at FROM {SCHEMA}.day_reports;")
    reports = cur.fetchall()
    if not reports:
        print("  [!] No day_reports found.")
        return

    for day_report_uuid, created_at in reports:
        owner_uuid = random.choice(users)
        count = random.randint(3, 7)

        for _ in range(count):
            description = generate_job_done_description()
            minutes_spent = random.randint(5, 120)
            updated_at = random_updated_from_created(created_at, max_shift_hours=72)

            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.job_dones
                    (uuid, created_at, updated_at, description,  
                    time, owner_uuid, day_report_uuid)
                VALUES
                    (gen_random_uuid(), %s, %s,
                     %s, %s, %s, %s);
                """,
                (
                    created_at, updated_at, description, minutes_spent,
                    owner_uuid, day_report_uuid,
                ),
            )

    print("  <- job_dones done")


# G. job_dones_job_tags 
def seed_job_dones_job_tags(cur):
    print("  -> Seeding job_dones_job_tags...")

    # 1. job_tags по way_uuid
    cur.execute(f"SELECT uuid, way_uuid FROM {SCHEMA}.job_tags;")
    rows = cur.fetchall()
    if not rows:
        print("  [!] No job_tags found.")
        return

    tags_by_way = {}
    for tag_uuid, way_uuid in rows:
        tags_by_way.setdefault(way_uuid, []).append(tag_uuid)

    # 2. job_dones + way_uuid
    cur.execute(
        f"""
        SELECT jd.uuid AS job_done_uuid,
               dr.way_uuid AS way_uuid
        FROM {SCHEMA}.job_dones jd
        JOIN {SCHEMA}.day_reports dr
             ON jd.day_report_uuid = dr.uuid;
        """
    )
    job_done_rows = cur.fetchall()
    if not job_done_rows:
        print("  [!] No job_dones found.")
        return

    inserted = 0
    for job_done_uuid, way_uuid in job_done_rows:
        tags = tags_by_way.get(way_uuid)
        if not tags:
            continue

        k = min(random.randint(1, 3), len(tags))
        chosen = random.sample(tags, k)

        for tag_uuid in chosen:
            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.job_dones_job_tags
                    (job_done_uuid, job_tag_uuid)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (job_done_uuid, tag_uuid),
            )
            inserted += 1

    print(f"  <- job_dones_job_tags done (inserted {inserted})")

# MAIN BLOCK 
def seed_activity_block():
    print("=== Seeding ACTIVITY BLOCK ===")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {SCHEMA}, public;")

        seed_day_reports_and_metrics(cur)
        seed_job_tags(cur)
        seed_plans(cur)
        seed_plans_job_tags(cur)
        seed_problems(cur)
        seed_job_dones(cur)
        seed_job_dones_job_tags(cur)

        conn.commit()
        print("=== ACTIVITY BLOCK COMPLETED ===")
   
    except Exception as e:
        conn.rollback()
        print("Error in activity block:", e)
    
    finally:
        conn.close()


if __name__ == "__main__":
    seed_activity_block()
