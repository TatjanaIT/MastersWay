import random
from datetime import datetime, timedelta
from faker import Faker
import unidecode

from db.connection import get_connection
from config import settings, seed_config

fake = Faker("ru_RU")

SCHEMA = settings.SCHEMA
PRICING_PLANS = seed_config.PRICING_PLANS
USER_TAG_NAMES = seed_config.USER_TAG_NAMES 
MENTORS = seed_config.MENTORS
STUDENTS = seed_config.STUDENTS

# Helper functions
def random_date_within_period():
    now = datetime.now()
    days_back = max(1, seed_config.SEED_DAYS_BACK) # период в днях
    delta_days = random.randint(1, days_back)  
    return now - timedelta(days=delta_days)

def random_updated_from_created(created_at):
    """
    updated_at:
    - иногда = created_at (не обновляли), иначе случайно между created_at и сейчас
    """
    now = datetime.now()

    # 30% случаев: не обновляли запись
    if random.random() < 0.30:
        return created_at

    if created_at >= now:
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
def seed_users_block(mentors_amount: int = MENTORS,
                     students_amount: int = STUDENTS):
    
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"SET search_path TO {SCHEMA}, public;")

    print("= Seeding USERS BLOCK =")

    # 1. USERS 
    user_ids = []

    def create_user(is_mentor: bool):
        first = fake.first_name()
        last = fake.last_name()
        email = make_email(cur, first, last)
        created_at = random_date_within_period()

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
    for uid in user_ids:
        plan = random.choice(PRICING_PLANS)

        now = datetime.now()

        if plan == "free":
            coins = random.randint(0, 150)
            expiration = None
        elif plan == "ai-starter":
            coins = random.randint(800, 1500)
            expiration = now + timedelta(days=random.randint(30, 90))
        elif plan == "starter":
            coins = random.randint(1500, 2500)
            expiration = now + timedelta(days=random.randint(60, 180))
        else:  # pro/b2b и т.д.
            coins = random.randint(3000, 5000)
            expiration = now + timedelta(days=random.randint(90, 365))

        created_at = random_date_within_period()

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