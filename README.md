# MastersWay – учебный проект с PostgreSQL

Проект моделирует систему путей обучения, активности студентов и менторства.  

Стек: PostgreSQL + Docker + Python (seeds), плюс Grafana и pgAdmin для работы с данными.


## 1. Предварительные требования

- Python 3.12.3
- Docker 29.0.1
- Docker compose v2.40.3-desktop.1

## 2. Инструкция Linux/WSL система

1. Создать схему используя 000001_init_schema.up.sql в PostgreSQL (я использую в проекте название SCHEMA = "o_test"), если используете другое наазвание замените его в config/settings.py 

2. Перейти в папку с скаченым проектом
    - cd /mnt/c/"Users"/"USERNAME"/MastersWay
    - или cd MastersWay

3. Установка пакета для виртуальных окружений (Один раз на системе (если ещё не делали))
    - sudo apt update
    - sudo apt install python3-venv

3. Создание и активация виртуального окружения
    - python3 -m venv venv
    - source venv/bin/activate
    - pip install --upgrade pip
    
4. Убедитесь, что окружение активно — в терминале перед строкой должно отображаться:
    - (venv)

5. Установка библиотек для проекта (из корня проекта)
    - pip install -r requirements.txt

6. Запуск Docker-сервисов (из корня проекта)
    - docker compose up -d

7. Проверить, что контейнеры запущены
    - docker ps

    - Вы увидите сервисы:
        - postgres
        - pgadmin
        - grafana

- База данных будет доступна по:
 - PostgreSQL
        - host: localhost
        - port: 5433
        - database: mydb
        - user: postgres
        - password: postgres
        
8. До запуска reset_and_seed.py убедиться что создана схема("o_test")

8. Применение сидов
    - python3 reset_and_seed.py

После выполнения — данные должны появиться в таблице и базе
