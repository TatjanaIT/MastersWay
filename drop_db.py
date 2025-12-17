from db.connection import get_connection
from config import settings


def ask_confirmation():
    print("⚠️ ВНИМАНИЕ!")
    print(f"Эта операция ПОЛНОСТЬЮ УДАЛИТ схему '{settings.SCHEMA}' со всеми таблицами и данными.")
    print("Отменить операцию будет невозможно.")
    print()

    answer = input("Продолжить удаление? (yes/no): ").strip().lower()
    return answer in ("y", "yes")

def drop_schema():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{settings.SCHEMA}" CASCADE;')
        conn.commit()
        print(f"✅ Schema '{settings.SCHEMA}' successfully dropped")
    finally:
        conn.close()


if __name__ == "__main__":
    if ask_confirmation():
        drop_schema()
    else:
        print("❌ Операция отменена.")

