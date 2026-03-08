"""
Creates 4 sandboxed SQLite databases with realistic sample data:
  - ecommerce: customers, orders, products, order_items, categories
  - hr: employees, departments, salaries, projects, project_assignments
  - movies: movies, actors, directors, genres, movie_cast, ratings
  - sports: teams, players, games, game_stats, standings
"""
import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_DIR = "./sample_dbs"

DATABASES = {
    "ecommerce": "E-Commerce Store",
    "hr": "HR & Employees",
    "movies": "Movies & Actors",
    "sports": "Sports League",
}


def seed_ecommerce(path: str):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY, name TEXT, description TEXT
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY, name TEXT, category_id INTEGER, price REAL,
        stock INTEGER, rating REAL, created_at TEXT,
        FOREIGN KEY(category_id) REFERENCES categories(id)
    );
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY, name TEXT, email TEXT, city TEXT,
        country TEXT, joined_at TEXT, total_spent REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY, customer_id INTEGER, status TEXT,
        total REAL, created_at TEXT, shipped_at TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    );
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER,
        quantity INTEGER, unit_price REAL,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );
    """)

    categories = [
        (1,'Electronics','Gadgets and devices'),
        (2,'Clothing','Apparel and accessories'),
        (3,'Books','Fiction and non-fiction'),
        (4,'Home & Garden','Furniture and decor'),
        (5,'Sports','Equipment and gear'),
    ]
    c.executemany("INSERT OR IGNORE INTO categories VALUES (?,?,?)", categories)

    products_data = [
        ('Wireless Headphones',1,79.99,150,4.5),('Laptop Stand',1,45.00,80,4.2),
        ('USB-C Hub',1,35.50,200,4.3),('Mechanical Keyboard',1,129.00,60,4.7),
        ('Webcam HD',1,89.00,40,4.1),('Running Shoes',2,95.00,120,4.4),
        ('Yoga Pants',2,45.00,200,4.6),('Winter Jacket',2,149.00,55,4.3),
        ('Casual Sneakers',2,65.00,180,4.2),('Sunglasses',2,55.00,90,4.0),
        ('Clean Code',3,35.00,300,4.8),('The Pragmatic Programmer',3,42.00,250,4.9),
        ('Designing Data-Intensive Apps',3,55.00,180,4.9),('Atomic Habits',3,18.00,500,4.7),
        ('Deep Work',3,16.00,400,4.6),('Standing Desk',4,399.00,25,4.5),
        ('Office Chair',4,299.00,30,4.4),('Desk Lamp',4,49.00,120,4.3),
        ('Bookshelf',4,189.00,20,4.1),('Plant Pot Set',4,29.00,200,4.2),
        ('Tennis Racket',5,89.00,45,4.4),('Basketball',5,35.00,80,4.5),
        ('Yoga Mat',5,28.00,150,4.6),('Dumbbells Set',5,75.00,40,4.7),
        ('Cycling Helmet',5,55.00,60,4.3),
    ]
    for i,(name,cat,price,stock,rating) in enumerate(products_data,1):
        d = (datetime.now()-timedelta(days=random.randint(30,365))).strftime('%Y-%m-%d')
        c.execute("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?,?)",
                  (i,name,cat,price,stock,rating,d))

    cities = [('New York','US'),('London','UK'),('Berlin','DE'),('Tokyo','JP'),
              ('Sydney','AU'),('Paris','FR'),('Toronto','CA'),('Dubai','AE')]
    first = ['Alice','Bob','Carol','David','Emma','Frank','Grace','Henry','Iris','James',
             'Kate','Leo','Mia','Noah','Olivia','Paul','Quinn','Rachel','Sam','Tina']
    last = ['Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Wilson','Moore']

    for i in range(1,101):
        name = f"{random.choice(first)} {random.choice(last)}"
        city,country = random.choice(cities)
        joined = (datetime.now()-timedelta(days=random.randint(30,730))).strftime('%Y-%m-%d')
        c.execute("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?,?)",
                  (i,name,f"user{i}@email.com",city,country,joined,0))

    statuses = ['delivered','shipped','processing','cancelled']
    for i in range(1,301):
        cid = random.randint(1,100)
        status = random.choices(statuses,[0.6,0.2,0.15,0.05])[0]
        created = (datetime.now()-timedelta(days=random.randint(1,180))).strftime('%Y-%m-%d')
        shipped = (datetime.now()-timedelta(days=random.randint(0,10))).strftime('%Y-%m-%d') if status in ('shipped','delivered') else None
        total = 0
        c.execute("INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?)",(i,cid,status,total,created,shipped))
        n_items = random.randint(1,4)
        for _ in range(n_items):
            pid = random.randint(1,25)
            qty = random.randint(1,3)
            price = products_data[pid-1][2]
            total += qty*price
            c.execute("INSERT OR IGNORE INTO order_items VALUES (?,?,?,?,?)",(None,i,pid,qty,price))
        c.execute("UPDATE orders SET total=? WHERE id=?",(round(total,2),i))

    conn.commit(); conn.close()


def seed_hr(path: str):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY, name TEXT, budget REAL, location TEXT, head_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY, name TEXT, email TEXT, department_id INTEGER,
        role TEXT, level TEXT, hire_date TEXT, manager_id INTEGER,
        FOREIGN KEY(department_id) REFERENCES departments(id)
    );
    CREATE TABLE IF NOT EXISTS salaries (
        id INTEGER PRIMARY KEY, employee_id INTEGER, amount REAL, currency TEXT,
        effective_date TEXT, FOREIGN KEY(employee_id) REFERENCES employees(id)
    );
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY, name TEXT, status TEXT, budget REAL,
        start_date TEXT, end_date TEXT, department_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS project_assignments (
        id INTEGER PRIMARY KEY, project_id INTEGER, employee_id INTEGER,
        role TEXT, hours_per_week INTEGER
    );
    """)

    depts = [(1,'Engineering',2000000,'San Francisco',None),(2,'Product',800000,'New York',None),
             (3,'Design',600000,'Remote',None),(4,'Marketing',700000,'London',None),
             (5,'Sales',1200000,'Chicago',None),(6,'HR',400000,'Austin',None)]
    c.executemany("INSERT OR IGNORE INTO departments VALUES (?,?,?,?,?)", depts)

    roles = {'Engineering':['Software Engineer','Senior Engineer','Staff Engineer','Engineering Manager'],
             'Product':['Product Manager','Senior PM','Director of Product'],
             'Design':['UI Designer','UX Researcher','Design Lead'],
             'Marketing':['Marketing Manager','Content Writer','SEO Specialist'],
             'Sales':['Sales Rep','Account Executive','Sales Manager'],
             'HR':['HR Generalist','Recruiter','HR Manager']}
    levels = ['L3','L4','L5','L6']
    dept_names = {1:'Engineering',2:'Product',3:'Design',4:'Marketing',5:'Sales',6:'HR'}
    names = ['Alex Chen','Jordan Lee','Sam Park','Morgan Davis','Casey Kim',
             'Riley Brown','Avery Johnson','Quinn Wilson','Jamie Garcia','Drew Martinez',
             'Blake Thompson','Sage Anderson','River Taylor','Skylar Moore','Dakota Harris',
             'Finley Clark','Peyton Lewis','Reese Walker','Cameron Hall','Ari Young']

    for i,name in enumerate(names,1):
        dept_id = random.randint(1,6)
        dept = dept_names[dept_id]
        role = random.choice(roles[dept])
        level = random.choice(levels)
        hire = (datetime.now()-timedelta(days=random.randint(30,1825))).strftime('%Y-%m-%d')
        mgr = random.randint(1,i-1) if i > 3 else None
        c.execute("INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?,?,?,?)",
                  (i,name,f"{name.lower().replace(' ','.')}@company.com",dept_id,role,level,hire,mgr))
        base = {'L3':80000,'L4':110000,'L5':150000,'L6':200000}[level]
        salary = base + random.randint(-10000,20000)
        c.execute("INSERT OR IGNORE INTO salaries VALUES (?,?,?,?,?)",
                  (i,i,salary,'USD',(datetime.now()-timedelta(days=random.randint(0,365))).strftime('%Y-%m-%d')))

    projects = [
        (1,'Platform Rewrite','active',500000,'2024-01-01','2024-12-31',1),
        (2,'Mobile App v2','active',300000,'2024-03-01','2024-09-30',1),
        (3,'Brand Refresh','completed',150000,'2023-06-01','2024-01-01',3),
        (4,'Q4 Campaign','active',200000,'2024-10-01','2024-12-31',4),
        (5,'CRM Migration','planning',400000,'2025-01-01','2025-06-30',5),
    ]
    c.executemany("INSERT OR IGNORE INTO projects VALUES (?,?,?,?,?,?,?)", projects)

    for proj_id in range(1,6):
        for _ in range(random.randint(2,5)):
            emp = random.randint(1,20)
            role = random.choice(['Developer','Designer','Lead','Reviewer'])
            hrs = random.choice([10,20,30,40])
            c.execute("INSERT OR IGNORE INTO project_assignments VALUES (?,?,?,?,?)",(None,proj_id,emp,role,hrs))

    conn.commit(); conn.close()


def seed_movies(path: str):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS directors (id INTEGER PRIMARY KEY, name TEXT, nationality TEXT, birth_year INTEGER);
    CREATE TABLE IF NOT EXISTS genres (id INTEGER PRIMARY KEY, name TEXT);
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY, title TEXT, year INTEGER, director_id INTEGER,
        genre_id INTEGER, runtime_min INTEGER, budget_m REAL, box_office_m REAL,
        imdb_rating REAL, FOREIGN KEY(director_id) REFERENCES directors(id)
    );
    CREATE TABLE IF NOT EXISTS actors (id INTEGER PRIMARY KEY, name TEXT, nationality TEXT, birth_year INTEGER);
    CREATE TABLE IF NOT EXISTS movie_cast (
        id INTEGER PRIMARY KEY, movie_id INTEGER, actor_id INTEGER, character_name TEXT, billing_order INTEGER
    );
    CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY, movie_id INTEGER, source TEXT, score REAL, max_score REAL
    );
    """)

    directors = [(1,'Christopher Nolan','British',1970),(2,'Greta Gerwig','American',1983),
                 (3,'Denis Villeneuve','Canadian',1967),(4,'Jordan Peele','American',1979),
                 (5,'Bong Joon-ho','South Korean',1969),(6,'Ridley Scott','British',1937),
                 (7,'Steven Spielberg','American',1946),(8,'Ava DuVernay','American',1972)]
    c.executemany("INSERT OR IGNORE INTO directors VALUES (?,?,?,?)", directors)

    genres = [(1,'Sci-Fi'),(2,'Drama'),(3,'Comedy'),(4,'Horror'),(5,'Thriller'),(6,'Action'),(7,'Animation')]
    c.executemany("INSERT OR IGNORE INTO genres VALUES (?,?)", genres)

    movies = [
        (1,'Oppenheimer',2023,1,2,180,100.0,952.0,8.3),
        (2,'Barbie',2023,2,3,114,145.0,1441.0,6.9),
        (3,'Dune Part Two',2024,3,1,166,190.0,711.0,8.5),
        (4,'Get Out',2017,4,4,104,4.5,255.0,7.7),
        (5,'Parasite',2019,5,2,132,11.4,258.0,8.5),
        (6,'The Martian',2015,6,1,144,108.0,630.0,8.0),
        (7,'Interstellar',2014,1,1,169,165.0,773.0,8.7),
        (8,'Lady Bird',2017,2,2,94,10.0,79.0,7.4),
        (9,'Arrival',2016,3,1,116,47.0,203.0,7.9),
        (10,'Nope',2022,4,1,130,68.0,171.0,6.8),
        (11,'Memories of Murder',2003,5,5,132,2.8,3.0,8.1),
        (12,'Gladiator',2000,6,6,155,103.0,460.0,8.5),
        (13,'Schindlers List',1993,7,2,195,22.0,322.0,8.9),
        (14,'Selma',2014,8,2,128,20.0,66.0,7.5),
        (15,'Tenet',2020,1,5,150,200.0,363.0,7.3),
    ]
    c.executemany("INSERT OR IGNORE INTO movies VALUES (?,?,?,?,?,?,?,?,?)", movies)

    actors = [(1,'Cillian Murphy','Irish',1976),(2,'Margot Robbie','Australian',1990),
              (3,'Timothée Chalamet','American',1995),(4,'Daniel Kaluuya','British',1989),
              (5,'Song Kang-ho','South Korean',1967),(6,'Matt Damon','American',1970),
              (7,'Zendaya','American',1996),(8,'Ryan Gosling','Canadian',1980),
              (9,'Florence Pugh','British',1996),(10,'Saoirse Ronan','Irish-American',1994)]
    c.executemany("INSERT OR IGNORE INTO actors VALUES (?,?,?,?)", actors)

    cast = [(None,1,1,'J. Robert Oppenheimer',1),(None,1,9,'Jean Tatlock',2),
            (None,2,2,'Barbie',1),(None,2,8,'Ken',2),(None,3,3,'Paul Atreides',1),
            (None,3,7,'Chani',2),(None,4,4,'Chris Washington',1),(None,5,5,'Ki-taek',1),
            (None,6,6,'Mark Watney',1),(None,7,6,'Cooper',1),(None,8,10,'Christine',1),
            (None,12,5,'Maximus',1),(None,13,6,'Oskar Schindler',1),(None,15,3,'Neil',1)]
    c.executemany("INSERT OR IGNORE INTO movie_cast VALUES (?,?,?,?,?)", cast)

    for movie_id in range(1,16):
        imdb = movies[movie_id-1][8]
        c.execute("INSERT OR IGNORE INTO ratings VALUES (?,?,?,?,?)",(None,movie_id,'IMDb',imdb,10))
        c.execute("INSERT OR IGNORE INTO ratings VALUES (?,?,?,?,?)",(None,movie_id,'Metacritic',round(imdb*9+random.randint(-5,5),0),100))

    conn.commit(); conn.close()


def seed_sports(path: str):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY, name TEXT, city TEXT, division TEXT, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY, name TEXT, team_id INTEGER, position TEXT,
        age INTEGER, salary_m REAL, FOREIGN KEY(team_id) REFERENCES teams(id)
    );
    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY, home_team_id INTEGER, away_team_id INTEGER,
        home_score INTEGER, away_score INTEGER, played_at TEXT, season TEXT
    );
    CREATE TABLE IF NOT EXISTS game_stats (
        id INTEGER PRIMARY KEY, game_id INTEGER, player_id INTEGER,
        points INTEGER, assists INTEGER, rebounds INTEGER, minutes INTEGER
    );
    CREATE TABLE IF NOT EXISTS standings (
        id INTEGER PRIMARY KEY, team_id INTEGER, season TEXT,
        wins INTEGER, losses INTEGER, points_for INTEGER, points_against INTEGER
    );
    """)

    teams = [(1,'Lakers','Los Angeles','West',0,0),(2,'Celtics','Boston','East',0,0),
             (3,'Warriors','San Francisco','West',0,0),(4,'Heat','Miami','East',0,0),
             (5,'Nuggets','Denver','West',0,0),(6,'Bucks','Milwaukee','East',0,0),
             (7,'Suns','Phoenix','West',0,0),(8,'76ers','Philadelphia','East',0,0)]
    c.executemany("INSERT OR IGNORE INTO teams VALUES (?,?,?,?,?,?)", teams)

    positions = ['PG','SG','SF','PF','C']
    player_names = ['James Walker','Chris Jordan','Mike Thompson','Kevin Davis','Anthony Harris',
                    'Stephen Brown','Damian Wilson','Kawhi Moore','Joel Taylor','Giannis Martinez',
                    'Devin Jackson','Nikola White','Ja Anderson','Luka Thomas','Jayson Garcia',
                    'Donovan Lee','Trae Robinson','Zion Clark','LaMelo Lewis','Karl Young']

    for i,name in enumerate(player_names,1):
        team_id = (i-1)//3 + 1 if i <= 24 else random.randint(1,8)
        pos = positions[i % 5]
        age = random.randint(20,35)
        salary = round(random.uniform(2.0,45.0),1)
        c.execute("INSERT OR IGNORE INTO players VALUES (?,?,?,?,?,?)",(i,name,team_id,pos,age,salary))

    wins = {t:0 for t in range(1,9)}
    losses = {t:0 for t in range(1,9)}
    for i in range(1,81):
        home = random.randint(1,8)
        away = random.randint(1,8)
        while away == home: away = random.randint(1,8)
        hs = random.randint(95,128)
        as_ = random.randint(95,128)
        played = (datetime.now()-timedelta(days=random.randint(1,120))).strftime('%Y-%m-%d')
        c.execute("INSERT OR IGNORE INTO games VALUES (?,?,?,?,?,?,?)",(i,home,away,hs,as_,played,'2024-25'))
        if hs > as_: wins[home]+=1; losses[away]+=1
        else: wins[away]+=1; losses[home]+=1
        # stats for 5 random players
        players_in_game = random.sample(range(1,21),5)
        for pid in players_in_game:
            pts=random.randint(4,38); ast=random.randint(0,12); reb=random.randint(1,15); mins=random.randint(15,38)
            c.execute("INSERT OR IGNORE INTO game_stats VALUES (?,?,?,?,?,?,?)",(None,i,pid,pts,ast,reb,mins))

    for tid in range(1,9):
        c.execute("UPDATE teams SET wins=?,losses=? WHERE id=?",(wins[tid],losses[tid],tid))
        pts_for = random.randint(8000,10000)
        pts_against = random.randint(8000,10000)
        c.execute("INSERT OR IGNORE INTO standings VALUES (?,?,?,?,?,?,?)",
                  (tid,tid,'2024-25',wins[tid],losses[tid],pts_for,pts_against))

    conn.commit(); conn.close()


def ensure_sample_dbs():
    os.makedirs(DB_DIR, exist_ok=True)
    seeders = {
        "ecommerce": seed_ecommerce,
        "hr": seed_hr,
        "movies": seed_movies,
        "sports": seed_sports,
    }
    for name, seeder in seeders.items():
        path = f"{DB_DIR}/{name}.db"
        if not os.path.exists(path):
            seeder(path)
            print(f"Seeded {name} database")


def get_db_path(name: str) -> str:
    if name not in DATABASES:
        raise ValueError(f"Unknown database: {name}")
    return f"{DB_DIR}/{name}.db"
