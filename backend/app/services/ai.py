import httpx
import json
import re
from app.core.config import settings


EXPLAIN_PROMPT = """You are an expert SQL teacher. Given a SQL query and its results, explain what it does in clear plain English.

Return ONLY valid JSON, no markdown, no backticks:
{
  "summary": "One sentence: what this query returns",
  "explanation": "2-3 sentences explaining HOW it works — joins, filters, aggregations etc.",
  "concepts": ["list", "of", "sql", "concepts", "used"],
  "difficulty": "beginner|intermediate|advanced"
}"""


OPTIMIZE_PROMPT = """You are an expert database engineer. Analyze this SQL query and suggest improvements.

Return ONLY valid JSON, no markdown, no backticks:
{
  "issues": [
    {
      "type": "performance|style|correctness|security",
      "description": "What the issue is",
      "suggestion": "How to fix it"
    }
  ],
  "optimized_sql": "Rewritten SQL if improvements are possible, or same SQL if already optimal",
  "improved": true or false,
  "explanation": "Brief explanation of what was changed and why"
}

Focus on: missing indexes hints, SELECT * usage, missing WHERE clauses, N+1 patterns, inefficient JOINs, subquery vs CTE opportunities."""


FIX_PROMPT = """You are an expert SQL debugger. Fix this broken SQL query.

Return ONLY valid JSON, no markdown, no backticks:
{
  "fixed_sql": "The corrected SQL query",
  "explanation": "What was wrong and what you fixed"
}"""


async def ai_explain(sql: str, schema_context: str, result_preview: str, groq_api_key: str = None) -> dict:
    api_key = groq_api_key or settings.GROQ_API_KEY
    if not api_key:
        return {"error": "No API key"}

    user_msg = f"Schema context:\n{schema_context}\n\nSQL Query:\n{sql}\n\nResult preview (first 3 rows):\n{result_preview}"

    return await _call_groq(api_key, EXPLAIN_PROMPT, user_msg)


async def ai_optimize(sql: str, schema_context: str, groq_api_key: str = None) -> dict:
    api_key = groq_api_key or settings.GROQ_API_KEY
    if not api_key:
        return {"error": "No API key"}

    user_msg = f"Schema context:\n{schema_context}\n\nSQL Query to optimize:\n{sql}"
    return await _call_groq(api_key, OPTIMIZE_PROMPT, user_msg)


async def ai_fix(sql: str, error: str, schema_context: str, groq_api_key: str = None) -> dict:
    api_key = groq_api_key or settings.GROQ_API_KEY
    if not api_key:
        return {"error": "No API key"}

    user_msg = f"Schema:\n{schema_context}\n\nBroken SQL:\n{sql}\n\nError:\n{error}"
    return await _call_groq(api_key, FIX_PROMPT, user_msg)


async def _call_groq(api_key: str, system: str, user: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [{"role":"system","content":system},{"role":"user","content":user}],
                    "temperature": 0.2,
                    "max_tokens": 1024,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            try:
                return json.loads(raw)
            except Exception:
                m = re.search(r'\{.*\}', raw, re.DOTALL)
                return json.loads(m.group()) if m else {"error": "Invalid JSON from model"}
    except Exception as e:
        return {"error": str(e)}


def build_schema_context(schema: list[dict]) -> str:
    """Build a compact schema string for prompt context."""
    lines = []
    for tbl in schema:
        cols = ", ".join(f"{c['name']} {c['type']}{'(PK)' if c['pk'] else ''}" for c in tbl['columns'])
        lines.append(f"  {tbl['table']} ({tbl['row_count']} rows): {cols}")
    return "\n".join(lines)
