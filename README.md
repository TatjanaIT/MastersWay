# MastersWay – учебный проект с PostgreSQL

Проект моделирует систему путей обучения, активности студентов и менторства.  

Стек: PostgreSQL + Docker + Python (seeds), плюс Grafana и pgAdmin для работы с данными.


## 1. Предварительные требования

- Python 3.12.3
- Docker 29.0.1
- Docker compose v2.40.3-desktop.1
- Git 2.43.0 

## 2. Инструкция(по шагам) Linux/WSL система

1. Установка пакета для виртуальных окружений
    sudo apt update
    sudo apt install python3-venv

2. Создание и активация виртуального окружения
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    
3. Убедитесь, что окружение активно — в терминале перед строкой должно отображаться:
    (venv)

4. Установка библиотек для проекта
    pip install -r requirements.txt

5. Запуск Docker-сервисов
    docker compose up -d

6. Проверить, что контейнеры запущены
    docker ps

    Вы увидите сервисы:
        postgres (порт 5433 → 5432)
        pgadmin
        grafana

7. Применение миграций и сидов
    python3 reset_and_seed.py

После выполнения — данные должны появиться в таблице и базе