## MastersWay – Learning Project with PostgreSQL

This project is a learning project that simulates:
- learning paths, student activity, mentoring.

Tech stack: PostgreSQL, Docker, and Python (seed scripts).

Grafana and pgAdmin are used to view and work with the data.

## 1. Prerequisites (Linux / WSL Ubuntu)

Before starting, make sure you have:

- Python 3.12.3
- Docker 29.0.1
- Docker compose v2.40.3-desktop.1
- Python3-venv
   - sudo apt install python3-venv (run once if it is not installed)

## 2. Instructions (from the project root)

1. Virtual environment
    - python3 -m venv venv (Create a virtual environment) 
    - source venv/bin/activate (Activate the virtual environment)
        -You should see (venv) at the beginning of the terminal line
    - pip install --upgrade pip (Update pip inside venv (optional but recommended))

2. Install project dependencies
    - pip install -r requirements.txt

3. Start Docker services
    - docker compose up -d
        - docker ps (check that containers are running)
            
            You should see
            - postgres
            - pgadmin
            - grafana

4. Database access (pgAdmin)
    - (http://localhost:5050) (Open pgAdmin in the browser)

        - PPostgreSQL connection settings
            - host: localhost
            - port: 5433
            - database: mydb
            - user: postgres
            - password: postgres

5. Create database schema and tables
    - python3 create_shema_and_tables.py

6. Run seed scripts
    - python3 reset_and_seed.py

After this step, the tables should contain data.

7. Remove the database schema (all tables and data)
    - python3 drop_db.py
