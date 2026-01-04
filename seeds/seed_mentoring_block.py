import random

from db.connection import get_connection
from config import settings

SCHEMA = settings.SCHEMA


def seed_mentoring_block():
    print("=== Seeding MENTORING BLOCK ===")

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {SCHEMA}, public;")

        # mentors / students берём из users.is_mentor (НЕ случайно)
        cur.execute("SELECT uuid FROM users WHERE is_mentor = true;")
        mentors = [row[0] for row in cur.fetchall()]

        cur.execute("SELECT uuid FROM users WHERE is_mentor = false;")
        students = [row[0] for row in cur.fetchall()]

        if not mentors:
            print("  [!] ERROR: no mentors found (users.is_mentor=true).")
            return
        if not students:
            print("  [!] ERROR: no students found (users.is_mentor=false).")
            return

        print(f"  Mentors: {len(mentors)}, students: {len(students)}")

        # all ways
        cur.execute("SELECT uuid FROM ways;")
        way_ids = [row[0] for row in cur.fetchall()]
        if not way_ids:
            print("  [!] ERROR: no ways found")
            return

        mentor_links = 0
        former_links = 0
        from_requests = 0
        to_requests = 0

        # mentor_users_ways and former_mentors_ways
        for way_uuid in way_ids:
            # 1–3 текущих ментора на путь, но не больше чем mentors
            k_current = random.randint(1, min(3, len(mentors)))
            current_mentors = random.sample(mentors, k_current)

            for mentor_uuid in current_mentors:
                cur.execute(
                    f"""
                    INSERT INTO {SCHEMA}.mentor_users_ways (user_uuid, way_uuid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                    """,
                    (mentor_uuid, way_uuid),
                )
                # считаем попытку вставки, но можно считать только успешные — по rowcount
                mentor_links += 1

            # 0–2 бывших ментора на путь (из оставшихся)
            possible_former = [m for m in mentors if m not in current_mentors]
            if possible_former:
                k_former = random.randint(0, min(2, len(possible_former)))
                if k_former > 0:
                    former_for_way = random.sample(possible_former, k_former)
                    for former_uuid in former_for_way:
                        cur.execute(
                            f"""
                            INSERT INTO {SCHEMA}.former_mentors_ways (former_mentor_uuid, way_uuid)
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING;
                            """,
                            (former_uuid, way_uuid),
                        )
                        former_links += 1

        # from_user_mentoring_requests (запросы от студентов)
                # В БД стоит триггер: лимит запросов на один way_uuid.
                # Поэтому вставляем ТОЛЬКО если:
                #  - пары (student_uuid, way_uuid) ещё нет
                #  - по этому way_uuid сейчас < лимита
        MAX_FROM_REQ_PER_WAY = 5  # <-- если лимит 10, поставь 10

        # текущие количества запросов по way_uuid
        cur.execute(
            f"""
            SELECT way_uuid, COUNT(*)::int AS cnt
            FROM {SCHEMA}.from_user_mentoring_requests
            GROUP BY way_uuid;
            """
        )
        from_way_count = {row[0]: row[1] for row in cur.fetchall()}

        available_ways_for_from = [w for w in way_ids if from_way_count.get(w, 0) < MAX_FROM_REQ_PER_WAY]

        for student_uuid in students:
            if not available_ways_for_from:
                break  # все пути достигли лимита

            k_req = random.randint(0, 3)
            if k_req == 0:
                continue

            k_req = min(k_req, len(available_ways_for_from))
            chosen_ways = random.sample(available_ways_for_from, k_req)

            for way_uuid in chosen_ways:
                if from_way_count.get(way_uuid, 0) >= MAX_FROM_REQ_PER_WAY:
                    if way_uuid in available_ways_for_from:
                        available_ways_for_from.remove(way_uuid)
                    continue

                cur.execute(
                    f"""
                    INSERT INTO {SCHEMA}.from_user_mentoring_requests (user_uuid, way_uuid)
                    SELECT %s, %s
                    WHERE
                    NOT EXISTS (
                        SELECT 1
                        FROM {SCHEMA}.from_user_mentoring_requests r
                        WHERE r.user_uuid = %s AND r.way_uuid = %s
                    )
                    AND (
                        SELECT COUNT(*)
                        FROM {SCHEMA}.from_user_mentoring_requests r2
                        WHERE r2.way_uuid = %s
                    ) < %s;
                    """,
                    (student_uuid, way_uuid, student_uuid, way_uuid, way_uuid, MAX_FROM_REQ_PER_WAY),
                )

                if cur.rowcount == 1:
                    from_requests += 1
                    from_way_count[way_uuid] = from_way_count.get(way_uuid, 0) + 1

                if from_way_count.get(way_uuid, 0) >= MAX_FROM_REQ_PER_WAY:
                    if way_uuid in available_ways_for_from:
                        available_ways_for_from.remove(way_uuid)

        
        # to_user_mentoring_requests (запросы к менторам)
        # В БД стоит триггер: max 5 requests на один way_uuid.
        # Поэтому вставляем ТОЛЬКО если:
        #  - пары (mentor_uuid, way_uuid) ещё нет
        #  - по этому way_uuid сейчас < 5 записей
        # Делается через INSERT ... SELECT ... WHERE ..., чтобы не
        # было "опасных" попыток вставки, которые триггер может остановить.
        MAX_REQ_PER_WAY = 5

        # текущие количества по way_uuid (для ускорения выбора доступных)
        cur.execute(
            f"""
            SELECT way_uuid, COUNT(*)::int AS cnt
            FROM {SCHEMA}.to_user_mentoring_requests
            GROUP BY way_uuid;
            """
        )
        way_req_count = {row[0]: row[1] for row in cur.fetchall()}

        available_ways = [w for w in way_ids if way_req_count.get(w, 0) < MAX_REQ_PER_WAY]

        for mentor_uuid in mentors:
            if not available_ways:
                break  # все пути достигли лимита

            k_req = random.randint(0, 3)
            if k_req == 0:
                continue

            k_req = min(k_req, len(available_ways))
            chosen_ways = random.sample(available_ways, k_req)

            for way_uuid in chosen_ways:
                
                if way_req_count.get(way_uuid, 0) >= MAX_REQ_PER_WAY:
                    if way_uuid in available_ways:
                        available_ways.remove(way_uuid)
                    continue

                # безопасная вставка (не триггерит лишние попытки)
                cur.execute(
                    f"""
                    INSERT INTO {SCHEMA}.to_user_mentoring_requests (user_uuid, way_uuid)
                    SELECT %s, %s
                    WHERE
                      NOT EXISTS (
                        SELECT 1
                        FROM {SCHEMA}.to_user_mentoring_requests r
                        WHERE r.user_uuid = %s AND r.way_uuid = %s
                      )
                      AND (
                        SELECT COUNT(*)
                        FROM {SCHEMA}.to_user_mentoring_requests r2
                        WHERE r2.way_uuid = %s
                      ) < %s;
                    """,
                    (mentor_uuid, way_uuid, mentor_uuid, way_uuid, way_uuid, MAX_REQ_PER_WAY),
                )

                # rowcount = 1 если реально вставили
                if cur.rowcount == 1:
                    to_requests += 1
                    way_req_count[way_uuid] = way_req_count.get(way_uuid, 0) + 1

                # обновляем available_ways
                if way_req_count.get(way_uuid, 0) >= MAX_REQ_PER_WAY:
                    if way_uuid in available_ways:
                        available_ways.remove(way_uuid)

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
