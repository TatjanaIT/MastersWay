import random
from datetime import datetime, timedelta
from faker import Faker
import unidecode

from db.connection import get_connection
from config import settings

fake = Faker("ru_RU")
SCHEMA = settings.SCHEMA

PRICING_PLANS = ["free", "ai-starter", "starter", "pro"]
USER_TAG_NAMES = ["Python", "SQL", "PostgreSQL", "Power BI", "Tableau",
                  "Data Analyst", "Product Analyst", "Marketing",
                  "Junior", "Middle", "Senior", "Mentor"]

DEFAULT_MENTORS = 7
DEFAULT_STUDENTS = 23

# Helper functions

def random_date_within_6_months():
    today = datetime.now()
    delta_days = random.randint(0, 180)
    return today - timedelta(days=delta_days)

def random_updated_from_created(created_at): # Делает updated_at случайным моментом между created_at и сейчас, но никогда не в будущем.
    now = datetime.now()

    if created_at >= now: # если вдруг created_at уже в будущем (на всякий случай)
        return now

    diff = now - created_at
    total_seconds = int(diff.total_seconds())
    if total_seconds <= 0:
        return now

    shift_seconds = random.randint(0, total_seconds)
    return created_at + timedelta(seconds=shift_seconds)

def make_email(cur, first, last):
    base = f"{unidecode.unidecode(last).lower()}.{unidecode.unidecode(first[0]).lower()}"
    email = f"{base}@example.com"

    cur.execute(f"SELECT 1 FROM users WHERE email = %s", (email,))
    if cur.fetchone() is None:
        return email

    # если занято — добавляем число
    counter = 2
    while True:
        new_email = f"{base}{counter}@example.com"
        cur.execute(f"SELECT 1 FROM users WHERE email = %s", (new_email,))
        if cur.fetchone() is None:
            return new_email
        counter += 1

def generate_contact():
    type_ = random.choice(["email", "telegram", "phone"])

    if type_ == "email":
        return fake.email(), "Email"
    elif type_ == "telegram":
        return f"https://t.me/{fake.user_name()}", "Telegram"
    else:
        return fake.phone_number(), "Телефон"


# MAIN FUNCTION
def seed_users_block(mentors_amount: int = DEFAULT_MENTORS,
                     students_amount: int = DEFAULT_STUDENTS):
    
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"SET search_path TO {settings.SCHEMA}, public;")

    print("=== Seeding USERS BLOCK ===")


    # 1. USERS 
    user_ids = []

    def create_user(is_mentor: bool):
        first = fake.first_name()
        last = fake.last_name()
        email = make_email(cur, first, last)
        created_at = random_date_within_6_months()

        cur.execute(
            """
            INSERT INTO users
                (uuid, name, email, description, created_at, image_url, is_mentor)
            VALUES
                (gen_random_uuid(), %s, %s, %s, %s, %s, %s)
            RETURNING uuid;
            """,
            (
                f"{first} {last}",
                email,
                "Mentor" if is_mentor else "Student",
                created_at,
                "",
                is_mentor,
            ),
        )
        return cur.fetchone()[0]

    for _ in range(mentors_amount):
        user_ids.append(create_user(is_mentor=True))

    for _ in range(students_amount):
        user_ids.append(create_user(is_mentor=False))

    print(f"Inserted {len(user_ids)} users")

    # 2. PROFILE SETTINGS
    now = datetime.now()

    for uid in user_ids:

        plan = random.choice(PRICING_PLANS)

        if plan == "free":
            coins = random.randint(0, 150)
            expiration = None
        elif plan == "ai-starter":
            coins = random.randint(800, 1500)
            expiration = now + timedelta(days=random.randint(30, 90))
        elif plan == "starter":
            coins = random.randint(1500, 2500)
            expiration = now + timedelta(days=random.randint(60, 180))
        else:  # pro
            coins = random.randint(3000, 5000)
            expiration = now + timedelta(days=random.randint(90, 365))

        # created_at: какой-то момент за последние 6 месяцев (можно поменять 180 на 50, если надо)
        created_at = now - timedelta(days=random.randint(0, 180))

        # updated_at: рандомно между created_at и сейчас
        updated_at = random_updated_from_created(created_at)

        cur.execute(
            """
            INSERT INTO profile_settings
                (uuid, pricing_plan, coins, expiration_date,
                 created_at, updated_at, owner_uuid)
            VALUES
                (gen_random_uuid(), %s, %s, %s, %s, %s, %s);
            """,
            (plan, coins, expiration, created_at, updated_at, uid),
        )

    print("Inserted profile_settings")

    # 3. USER_TAGS
    cur.execute("SELECT name, uuid FROM user_tags;")
    existing = {row[0]: row[1] for row in cur.fetchall()}

    tag_uuid_by_name = existing.copy()

    for tag in USER_TAG_NAMES:
        if tag not in existing:
            cur.execute(
                """
                INSERT INTO user_tags (uuid, name)
                VALUES (gen_random_uuid(), %s)
                RETURNING uuid;
                """,
                (tag,),
            )
            tag_uuid_by_name[tag] = cur.fetchone()[0]

    all_tag_uuids = list(tag_uuid_by_name.values())
    print(f"user_tags total: {len(all_tag_uuids)}")

    # 4. USER_CONTACTS
    contacts_inserted = 0

    for uid in user_ids:
        for _ in range(random.randint(1, 3)):
            link, desc = generate_contact()
            cur.execute(
                """
                INSERT INTO user_contacts (uuid, user_uuid, contact_link, description)
                VALUES (gen_random_uuid(), %s, %s, %s);
                """,
                (uid, link, desc),
            )
            contacts_inserted += 1

    print(f"Inserted {contacts_inserted} user_contacts")

    #5. USERS_USER_TAGS
    tag_links_inserted = 0

    for uid in user_ids:
        chosen = random.sample(all_tag_uuids, random.randint(2, 5))

        for tag_uuid in chosen:
            cur.execute(
                """
                INSERT INTO users_user_tags (user_uuid, user_tag_uuid)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (uid, tag_uuid),
            )
            tag_links_inserted += 1

    print(f"Inserted {tag_links_inserted} users_user_tags")

    conn.commit()
    conn.close()

    print("=== USERS BLOCK COMPLETED ===")


if __name__ == "__main__":
    seed_users_block()