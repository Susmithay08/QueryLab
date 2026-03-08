import json
import random
import string
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.core.database import get_db, QueryHistory, SharedQuery
from app.services.executor import execute_query, get_schema
from app.services.csv_import import import_csv, list_user_databases, delete_user_database, USER_DATABASES
from app.services.sample_dbs import DATABASES, ensure_sample_dbs
from app.services.ai import ai_explain, ai_optimize, ai_fix, build_schema_context

router = APIRouter()


# ── Databases ────────────────────────────────────────────────────────────────
@router.get("/databases")
async def list_databases():
    base = [{"id": k, "name": v, "user_upload": False} for k, v in DATABASES.items()]
    user = [{"id": u["id"], "name": u["name"], "user_upload": True, "rows": u["rows"]}
            for u in list_user_databases()]
    return base + user


@router.get("/databases/{db_name}/schema")
async def database_schema(db_name: str):
    schema = get_schema(db_name)
    if not schema:
        raise HTTPException(404, f"Database '{db_name}' not found")
    return schema


# ── Query execution ──────────────────────────────────────────────────────────
class RunQueryRequest(BaseModel):
    sql: str
    database: str
    groq_api_key: Optional[str] = None
    auto_explain: bool = False


@router.post("/query/run")
async def run_query(req: RunQueryRequest, db: AsyncSession = Depends(get_db)):
    result = execute_query(req.database, req.sql)

    # Save to history
    history = QueryHistory(
        database_name=req.database,
        sql=req.sql,
        row_count=result.get("row_count"),
        exec_ms=result.get("exec_ms"),
        had_error=bool(result.get("error")),
        error_msg=result.get("error"),
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)

    response = {**result, "history_id": history.id}

    # Auto-explain if requested and query succeeded
    if req.auto_explain and not result.get("error") and result.get("rows"):
        schema = get_schema(req.database)
        schema_ctx = build_schema_context(schema)
        preview = str(result["columns"]) + "\n" + str(result["rows"][:3])
        explanation = await ai_explain(req.sql, schema_ctx, preview, req.groq_api_key)
        response["explanation"] = explanation
        if not explanation.get("error"):
            history.ai_explanation = json.dumps(explanation)
            await db.commit()

    return response


# ── AI endpoints ─────────────────────────────────────────────────────────────
class AIRequest(BaseModel):
    sql: str
    database: str
    error: Optional[str] = None
    groq_api_key: Optional[str] = None


@router.post("/query/explain")
async def explain_query(req: AIRequest):
    schema = get_schema(req.database)
    schema_ctx = build_schema_context(schema)
    result = execute_query(req.database, req.sql)
    preview = str(result.get("columns", [])) + "\n" + str(result.get("rows", [])[:3])
    return await ai_explain(req.sql, schema_ctx, preview, req.groq_api_key)


@router.post("/query/optimize")
async def optimize_query(req: AIRequest):
    schema = get_schema(req.database)
    schema_ctx = build_schema_context(schema)
    return await ai_optimize(req.sql, schema_ctx, req.groq_api_key)


@router.post("/query/fix")
async def fix_query(req: AIRequest):
    if not req.error:
        raise HTTPException(400, "Error message required")
    schema = get_schema(req.database)
    schema_ctx = build_schema_context(schema)
    return await ai_fix(req.sql, req.error, schema_ctx, req.groq_api_key)


# ── History ──────────────────────────────────────────────────────────────────
@router.get("/history")
async def query_history(database: Optional[str] = None, limit: int = 30,
                         db: AsyncSession = Depends(get_db)):
    q = select(QueryHistory).order_by(desc(QueryHistory.created_at)).limit(limit)
    if database:
        q = q.where(QueryHistory.database_name == database)
    res = await db.execute(q)
    return [
        {
            "id": h.id, "database_name": h.database_name, "sql": h.sql,
            "row_count": h.row_count, "exec_ms": h.exec_ms,
            "had_error": h.had_error, "created_at": h.created_at,
        }
        for h in res.scalars().all()
    ]


@router.delete("/history/{item_id}")
async def delete_history(item_id: str, db: AsyncSession = Depends(get_db)):
    h = await db.get(QueryHistory, item_id)
    if not h: raise HTTPException(404)
    await db.delete(h)
    await db.commit()
    return {"deleted": True}


# ── Shared queries ────────────────────────────────────────────────────────────
class ShareRequest(BaseModel):
    sql: str
    database: str
    title: Optional[str] = None
    description: Optional[str] = None


@router.post("/query/share")
async def share_query(req: ShareRequest, db: AsyncSession = Depends(get_db)):
    slug = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    shared = SharedQuery(
        slug=slug, database_name=req.database, sql=req.sql,
        title=req.title, description=req.description,
    )
    db.add(shared)
    await db.commit()
    return {"slug": slug, "url": f"/shared/{slug}"}


@router.get("/query/shared/{slug}")
async def get_shared(slug: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SharedQuery).where(SharedQuery.slug == slug))
    shared = res.scalar_one_or_none()
    if not shared: raise HTTPException(404, "Shared query not found")
    shared.view_count += 1
    await db.commit()
    return {
        "slug": shared.slug, "database_name": shared.database_name,
        "sql": shared.sql, "title": shared.title, "description": shared.description,
        "view_count": shared.view_count, "created_at": shared.created_at,
    }


# ── CSV import ───────────────────────────────────────────────────────────────
@router.post("/csv/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(400, "Only CSV files are supported")
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large — max 10MB")
    try:
        result = import_csv(file_bytes, file.filename)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/csv/list")
async def list_csv_databases():
    return list_user_databases()


@router.delete("/csv/{db_id}")
async def delete_csv_database(db_id: str):
    delete_user_database(db_id)
    return {"deleted": True}


# ── Example queries ───────────────────────────────────────────────────────────
EXAMPLES = {
    "ecommerce": [
        {"label":"Top customers by spend","sql":"SELECT c.name, c.city, SUM(o.total) as total_spent,\n  COUNT(o.id) as order_count\nFROM customers c\nJOIN orders o ON o.customer_id = c.id\nWHERE o.status = 'delivered'\nGROUP BY c.id\nORDER BY total_spent DESC\nLIMIT 10"},
        {"label":"Revenue by category","sql":"SELECT cat.name as category,\n  COUNT(oi.id) as items_sold,\n  ROUND(SUM(oi.quantity * oi.unit_price), 2) as revenue\nFROM categories cat\nJOIN products p ON p.category_id = cat.id\nJOIN order_items oi ON oi.product_id = p.id\nJOIN orders o ON o.id = oi.order_id\nWHERE o.status != 'cancelled'\nGROUP BY cat.id\nORDER BY revenue DESC"},
        {"label":"Monthly order trends","sql":"SELECT strftime('%Y-%m', created_at) as month,\n  COUNT(*) as orders,\n  ROUND(AVG(total), 2) as avg_order_value\nFROM orders\nGROUP BY month\nORDER BY month"},
        {"label":"Low stock products","sql":"SELECT name, stock, price, rating\nFROM products\nWHERE stock < 50\nORDER BY stock ASC"},
    ],
    "hr": [
        {"label":"Salary by department","sql":"SELECT d.name as department,\n  COUNT(e.id) as headcount,\n  ROUND(AVG(s.amount), 0) as avg_salary,\n  ROUND(MAX(s.amount), 0) as max_salary\nFROM departments d\nJOIN employees e ON e.department_id = d.id\nJOIN salaries s ON s.employee_id = e.id\nGROUP BY d.id\nORDER BY avg_salary DESC"},
        {"label":"Most senior employees","sql":"SELECT name, role, level, hire_date,\n  CAST((julianday('now') - julianday(hire_date)) / 365 AS INT) as years_at_company\nFROM employees\nORDER BY hire_date ASC\nLIMIT 10"},
        {"label":"Project workload","sql":"SELECT p.name as project, p.status,\n  COUNT(pa.employee_id) as team_size,\n  SUM(pa.hours_per_week) as total_hours_per_week\nFROM projects p\nLEFT JOIN project_assignments pa ON pa.project_id = p.id\nGROUP BY p.id\nORDER BY total_hours_per_week DESC"},
        {"label":"Employees by level","sql":"SELECT level, COUNT(*) as count,\n  ROUND(AVG(s.amount),0) as avg_salary\nFROM employees e JOIN salaries s ON s.employee_id = e.id\nGROUP BY level ORDER BY avg_salary DESC"},
    ],
    "movies": [
        {"label":"Highest grossing films","sql":"SELECT m.title, m.year, d.name as director,\n  m.budget_m, m.box_office_m,\n  ROUND(m.box_office_m / m.budget_m, 1) as roi_multiplier\nFROM movies m\nJOIN directors d ON d.id = m.director_id\nORDER BY m.box_office_m DESC"},
        {"label":"Director stats","sql":"SELECT d.name, d.nationality,\n  COUNT(m.id) as films,\n  ROUND(AVG(m.imdb_rating), 2) as avg_rating,\n  SUM(m.box_office_m) as total_box_office_m\nFROM directors d\nJOIN movies m ON m.director_id = d.id\nGROUP BY d.id\nORDER BY avg_rating DESC"},
        {"label":"Top rated by genre","sql":"SELECT g.name as genre,\n  COUNT(m.id) as movies,\n  ROUND(AVG(m.imdb_rating), 2) as avg_imdb\nFROM genres g\nJOIN movies m ON m.genre_id = g.id\nGROUP BY g.id\nORDER BY avg_imdb DESC"},
        {"label":"Actor filmography","sql":"SELECT a.name as actor, a.nationality,\n  COUNT(mc.movie_id) as films,\n  GROUP_CONCAT(m.title, ', ') as movies\nFROM actors a\nJOIN movie_cast mc ON mc.actor_id = a.id\nJOIN movies m ON m.id = mc.movie_id\nGROUP BY a.id\nORDER BY films DESC"},
    ],
    "sports": [
        {"label":"League standings","sql":"SELECT t.name, t.city, t.division,\n  t.wins, t.losses,\n  ROUND(t.wins * 100.0 / (t.wins + t.losses), 1) as win_pct\nFROM teams t\nORDER BY win_pct DESC"},
        {"label":"Top scorers","sql":"SELECT p.name, t.name as team, p.position,\n  SUM(gs.points) as total_points,\n  ROUND(AVG(gs.points), 1) as ppg,\n  ROUND(AVG(gs.assists), 1) as apg\nFROM players p\nJOIN teams t ON t.id = p.team_id\nJOIN game_stats gs ON gs.player_id = p.id\nGROUP BY p.id\nORDER BY ppg DESC\nLIMIT 10"},
        {"label":"High scoring games","sql":"SELECT t1.name as home, t2.name as away,\n  g.home_score, g.away_score,\n  (g.home_score + g.away_score) as total_points,\n  g.played_at\nFROM games g\nJOIN teams t1 ON t1.id = g.home_team_id\nJOIN teams t2 ON t2.id = g.away_team_id\nORDER BY total_points DESC\nLIMIT 10"},
        {"label":"Best paid players","sql":"SELECT p.name, t.name as team, p.position,\n  p.age, p.salary_m\nFROM players p\nJOIN teams t ON t.id = p.team_id\nORDER BY p.salary_m DESC\nLIMIT 10"},
    ],
}


@router.get("/examples/{db_name}")
async def get_examples(db_name: str):
    return EXAMPLES.get(db_name, [])