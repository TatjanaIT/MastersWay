import random

from db.connection import get_connection
from config import settings

SCHEMA = settings.SCHEMA

# MAIN FUNCTION 
def seed_mentoring_block():
    print("=== Seeding MENTORING BLOCK ===")

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {SCHEMA}, public;")

        # all users
        cur.execute("SELECT uuid FROM users;")
        user_ids = [row[0] for row in cur.fetchall()]
        if len(user_ids) < 2:
            print("  [!] ERROR: need at least 2 users")
            return

        # all ways
        cur.execute("SELECT uuid FROM ways;")
        way_ids = [row[0] for row in cur.fetchall()]
        if not way_ids:
            print("  [!] ERROR: no ways found")
            return

        # делим пользователей на менторов и студентов (30% менторов)
        num_mentors = max(1, int(len(user_ids) * 0.3))
        mentors = set(random.sample(user_ids, num_mentors))
        students = [u for u in user_ids if u not in mentors]

        print(f"  Mentors: {len(mentors)}, students: {len(students)}")

        mentor_links = 0
        former_links = 0
        from_requests = 0
        to_requests = 0

        # mentor_users_ways and former_mentors_ways 
        for way_uuid in way_ids:
            # 1–3 текущих ментора на путь
            k_current = min(random.randint(1, 3), len(mentors))
            current_mentors = random.sample(list(mentors), k_current)

            for mentor_uuid in current_mentors:
                cur.execute(
                    f"""
                    INSERT INTO {SCHEMA}.mentor_users_ways
                        (user_uuid, way_uuid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (mentor_uuid, way_uuid),
                )
                mentor_links += 1

            # 0–2 бывших ментора на путь (из тех же менторов)
            possible_former = [m for m in mentors if m not in current_mentors]
            if possible_former:
                k_former = random.randint(0, min(2, len(possible_former)))
                former_for_way = random.sample(possible_former, k_former)
                for former_uuid in former_for_way:
                    cur.execute(
                        f"""
                        INSERT INTO {SCHEMA}.former_mentors_ways
                            (former_mentor_uuid, way_uuid)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING;
                        """,
                        (former_uuid, way_uuid),
                    )
                    former_links += 1

        # from_user_mentoring_requests (запросы от студентов "хочу ментора по этому пути")
        for student_uuid in students:
            k_req = random.randint(0, min(3, len(way_ids)))
            if k_req == 0:
                continue
            chosen_ways = random.sample(way_ids, k_req)

            for way_uuid in chosen_ways:
                cur.execute(
                    f"""
                    INSERT INTO {SCHEMA}.from_user_mentoring_requests
                        (user_uuid, way_uuid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (student_uuid, way_uuid),
                )
                from_requests += 1

        # to_user_mentoring_requests (запросы к менторам "возьми студента по этому пути")
        for mentor_uuid in mentors:
            k_req = random.randint(0, min(3, len(way_ids)))
            if k_req == 0:
                continue
            chosen_ways = random.sample(way_ids, k_req)

            for way_uuid in chosen_ways:
                cur.execute(
                    f"""
                    INSERT INTO {SCHEMA}.to_user_mentoring_requests
                        (user_uuid, way_uuid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (mentor_uuid, way_uuid),
                )
                to_requests += 1

        conn.commit()
        print("=== MENTORING BLOCK COMPLETED ===")
        print(f"  mentor_users_ways:            {mentor_links}")
        print(f"  former_mentors_ways:          {former_links}")
        print(f"  from_user_mentoring_requests: {from_requests}")
        print(f"  to_user_mentoring_requests:   {to_requests}")

    except Exception as e:
        if conn:
            conn.rollback()
        print("Error in mentoring block:", e)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    seed_mentoring_block()