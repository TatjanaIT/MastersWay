# MastersWay – учебный проект с PostgreSQL

Проект моделирует систему путей обучения, активности студентов и менторства.  

Стек: PostgreSQL + Docker + Python (seeds), плюс Grafana и pgAdmin для работы с данными.


## 1. Предварительные требования

- Python 3.12.3
- Docker 29.0.1
- Docker compose v2.40.3-desktop.1
- Python3-venv
    - sudo apt install python3-venv (выполнить один раз, если venv ещё не установлен)

## 2. Инструкция Linux/WSL Ubuntu система

2. Создание  и активация виртуального окружения (из корня проекта)
    - python3 -m venv venv (создаёт виртуальное окружение)
    - source venv/bin/activate (активация venv)
    
        - Проверка: 
            - в терминале перед строкой должно отображаться: (venv)

3. Установка библиотек для проекта (из корня проекта)
    - pip install -r requirements.txt

4. Запуск Docker-сервисов (из корня проекта)
    - docker compose up -d

        - Проверка запуска контейнеров
            - docker ps

                - Вы увидите сервисы:
                    - postgres
                    - pgadmin
                    - grafana

    - База данных будет доступна:
        - pgAdmin (web) http://localhost:5050
            - PostgreSQL
                - host: localhost
                - port: 5433
                - database: mydb
                - user: postgres
                - password: postgres

6. Создание схемы и таблиц 
    - python3 create_shema_and_tables.py

7. Применение сидов
    - python3 reset_and_seed.py

После выполнения — данные должны появиться в таблице и базе
