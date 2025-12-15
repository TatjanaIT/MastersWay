from db.connection import get_connection
from config.settings import SCHEMA
from seeds.seed_all import main as global_seed_main

def ask_confirmation():
    print(f"\n⚠️ ВНИМАНИЕ: Эта операция УДАЛИТ ВСЕ ДАННЫЕ в таблицах схемы '{SCHEMA}'!")
    print("Структура таблиц сохранится.")
    print("Продолжить? (yes/no): ", end="")

    answer = input().strip().lower()
    if answer in ("y", "yes"):
        return True

    print("Операция отменена пользователем.")
    return False

def truncate_all_tables():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        print(f"\nПолучаем список всех таблиц в схеме '{SCHEMA}' ")

        cur.execute(
            f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE';
            """,
            (SCHEMA,),
        )
        tables = [row[0] for row in cur.fetchall()]

        if not tables:
            print("Таблиц не найдено — схема пустая.")
            return

        print(f"Найдено таблиц: {len(tables)}")

        print("\nОчищаем все таблицы...")
        for table in tables:
            print(f"   - TRUNCATE {table}")
            cur.execute(f'TRUNCATE TABLE {SCHEMA}."{table}" RESTART IDENTITY CASCADE;')

        conn.commit()
        print("\nВсе данные успешно удалены.\n")

    finally:
        if conn:
            conn.close()

def main():
    print("\n= RESET DATA + SEED =\n")

    if not ask_confirmation():
        return

    truncate_all_tables()

    print("Запускаем глобальный сидер seed_all...\n")
    global_seed_main()

    print("\nГотово: данные пересозданы, структура таблиц сохранена.\n")


if __name__ == "__main__":
    main()
