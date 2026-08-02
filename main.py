import os
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from dotenv import load_dotenv
from google import genai

# Load variables from .env into the environment
load_dotenv()

app = FastAPI(title="Preflight - Startup Systems Check API")


def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "failure_prediction_ai"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )


@app.on_event("startup")
def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY, startup_name VARCHAR(255) NOT NULL, industry VARCHAR(100),
        business_model VARCHAR(100), target_market VARCHAR(100), budget VARCHAR(50),
        description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS analyses (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        sector_growth VARCHAR(20), overall_risk NUMERIC(5,2), market_risk NUMERIC(5,2),
        capital_risk NUMERIC(5,2), execution_risk NUMERIC(5,2), competition_risk NUMERIC(5,2),
        regulatory_risk NUMERIC(5,2), success_probability NUMERIC(5,2), failure_probability NUMERIC(5,2),
        revenue_projection JSONB, positioning_summary TEXT, audience_profile TEXT,
        market_maturity VARCHAR(20), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS market_sizing (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        tam NUMERIC(18,2), sam NUMERIC(18,2), som NUMERIC(18,2), methodology_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS market_trends (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        trend VARCHAR(150), description TEXT, impact VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS customer_segments (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        segment VARCHAR(150), description TEXT, percentage NUMERIC(5,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS competitors (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        competitor_name VARCHAR(150), market_share_estimate NUMERIC(5,2), positioning_notes TEXT,
        funding_stage VARCHAR(50), threat_level VARCHAR(20), strengths JSONB, weaknesses JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS risk_mitigations (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        category VARCHAR(50), mitigation TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS recommendations (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        category VARCHAR(20), recommendation_text TEXT, priority VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS action_plan (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        phase VARCHAR(30), focus TEXT, actions JSONB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS adoption_distribution (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        segment VARCHAR(50), percentage NUMERIC(5,2), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS market_growth_history (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        year INT, market_size NUMERIC(18,2), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS industry_challenges (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        challenge VARCHAR(200), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS growth_potential (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        score NUMERIC(5,2), explanation TEXT, market_validation NUMERIC(5,2),
        competitive_position NUMERIC(5,2), financial_model NUMERIC(5,2), technical_readiness NUMERIC(5,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS market_opportunities (
        id SERIAL PRIMARY KEY, project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        opportunity VARCHAR(200), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    cur.close()
    conn.close()


# Enable CORS so the React frontend (running on a different port) can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartupSubmission(BaseModel):
    startup_name: str
    industry: str
    business_model: str
    target_market: str
    budget: str
    description: str


@app.post("/api/analyze")
async def analyze_project(data: StartupSubmission):
    # 1. Persist the raw submission
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO projects (startup_name, industry, business_model, target_market, budget, description)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
            """,
            (data.startup_name, data.industry, data.business_model,
             data.target_market, data.budget, data.description),
        )
        project_id = cur.fetchone()[0]
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database insert failed: {e}")

    # 2. Call Gemini for the risk/market analysis
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        cur.close()
        conn.close()
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set in the environment")

    client = genai.Client(api_key=api_key)

    prompt = f"""
    Analyze this startup project and provide JSON output only, no markdown, no commentary.

    Name: {data.startup_name}
    Industry: {data.industry}
    Business Model: {data.business_model}
    Target Market: {data.target_market}
    Budget: {data.budget}
    Description: {data.description}

    Return JSON strictly in this format:
    {{
        "sector_growth": "34%",
        "overall_risk": 47,
        "success_probability": 62,
        "failure_probability": 38,
        "risks": {{
            "market": 22,
            "capital": 52,
            "execution": 59,
            "competition": 54,
            "regulatory": 18
        }},
        "risk_mitigations": [
            {{"category": "Market", "mitigation": "Short, concrete mitigation step."}},
            {{"category": "Capital", "mitigation": "Short, concrete mitigation step."}},
            {{"category": "Execution", "mitigation": "Short, concrete mitigation step."}},
            {{"category": "Competition", "mitigation": "Short, concrete mitigation step."}},
            {{"category": "Regulatory", "mitigation": "Short, concrete mitigation step."}}
        ],
        "revenue_projection": [4000, 6000, 8000, 11000, 14000, 18000],
        "positioning_summary": "Summary text here...",
        "market_sizing": {{
            "tam": 500000000,
            "sam": 80000000,
            "som": 4000000,
            "methodology_notes": "One or two sentences on how these were estimated."
        }},
        "market_trends": [
            {{"trend": "Short trend name", "description": "One sentence on why it matters.", "impact": "High"}},
            {{"trend": "Short trend name", "description": "One sentence on why it matters.", "impact": "Medium"}}
        ],
        "customer_segments": [
            {{"segment": "Segment name", "description": "Who they are and why they buy.", "percentage": 45}},
            {{"segment": "Segment name", "description": "Who they are and why they buy.", "percentage": 30}},
            {{"segment": "Segment name", "description": "Who they are and why they buy.", "percentage": 25}}
        ],
        "competitors": [
            {{
                "name": "Competitor A",
                "market_share_estimate": 18,
                "positioning_notes": "Short note on their angle.",
                "funding_stage": "Series B",
                "threat_level": "High",
                "strengths": ["Short strength", "Short strength"],
                "weaknesses": ["Short weakness", "Short weakness"]
            }},
            {{
                "name": "Competitor B",
                "market_share_estimate": 11,
                "positioning_notes": "Short note on their angle.",
                "funding_stage": "Seed",
                "threat_level": "Medium",
                "strengths": ["Short strength", "Short strength"],
                "weaknesses": ["Short weakness", "Short weakness"]
            }}
        ],
        "recommendations": [
            {{"category": "Strength", "text": "Short strategic note.", "priority": "High"}},
            {{"category": "Weakness", "text": "Short strategic note.", "priority": "Medium"}},
            {{"category": "Opportunity", "text": "Short strategic note.", "priority": "High"}},
            {{"category": "Threat", "text": "Short strategic note.", "priority": "Medium"}}
        ],
        "action_plan": [
            {{"phase": "0-30 days", "focus": "Short phase focus.", "actions": ["Action item", "Action item", "Action item"]}},
            {{"phase": "30-60 days", "focus": "Short phase focus.", "actions": ["Action item", "Action item", "Action item"]}},
            {{"phase": "60-90 days", "focus": "Short phase focus.", "actions": ["Action item", "Action item", "Action item"]}}
        ],
        "adoption_distribution": [
            {{"segment": "Innovators", "percentage": 5}},
            {{"segment": "Early Adopters", "percentage": 15}},
            {{"segment": "Early Majority", "percentage": 35}},
            {{"segment": "Late Majority", "percentage": 35}},
            {{"segment": "Laggards", "percentage": 10}}
        ],
        "audience_maturity": {{
            "audience_profile": "One sentence describing the core target audience.",
            "market_maturity": "Growing"
        }},
        "market_growth_history": [
            {{"year": 2021, "market_size": 700000000}},
            {{"year": 2022, "market_size": 850000000}},
            {{"year": 2023, "market_size": 1000000000}},
            {{"year": 2024, "market_size": 1100000000}},
            {{"year": 2025, "market_size": 1200000000}}
        ],
        "industry_challenges": [
            "Short challenge name",
            "Short challenge name",
            "Short challenge name"
        ],
        "growth_potential": {{
            "score": 78,
            "explanation": "One or two sentences on what drives and limits this score.",
            "market_validation": 65,
            "competitive_position": 55,
            "financial_model": 60,
            "technical_readiness": 70
        }},
        "market_opportunities": [
            "Short concrete opportunity",
            "Short concrete opportunity",
            "Short concrete opportunity"
        ]
    }}

    tam, sam, and som must be raw numbers in USD (no currency symbols, no abbreviations).
    List 2 to 4 real or realistic competitors, each with 2-3 strengths and 2-3 weaknesses.
    threat_level must be one of "High", "Medium", "Low".
    success_probability and failure_probability must each be 0-100 and sum to 100.
    Provide exactly one recommendation per SWOT category (Strength, Weakness, Opportunity, Threat).
    Provide exactly one mitigation per risk category (Market, Capital, Execution, Competition, Regulatory).
    Provide 3-5 market_trends items and 2-4 customer_segments items whose percentage values sum to 100.
    Provide exactly 3 action_plan phases (0-30, 30-60, 60-90 days), each with 2-4 concrete actions.
    adoption_distribution percentages must sum to 100.
    market_maturity must be one of "Emerging", "Growing", "Mature", "Declining".
    market_growth_history must have exactly 5 consecutive years ending with the current year, each market_size a raw USD number, generally increasing to reflect sector_growth.
    Provide 3-5 industry_challenges items (short phrases, sector-wide, not specific to one competitor).
    growth_potential.score and its four sub-scores must each be 0-100.
    Provide 3-5 market_opportunities items — short, concrete, specific to this startup (not generic advice).
    """

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "max_output_tokens": 4500,
                "thinking_config": {"thinking_budget": 0},
            },
        )
        analysis = json.loads(response.text)
    except Exception as e:
        cur.close()
        conn.close()
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {e}")

    # 3. Persist the analysis so it doesn't need to be recomputed later
    try:
        cur.execute(
            """
            INSERT INTO analyses
                (project_id, sector_growth, overall_risk, market_risk, capital_risk,
                 execution_risk, competition_risk, regulatory_risk, success_probability,
                 failure_probability, revenue_projection, positioning_summary,
                 audience_profile, market_maturity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                project_id,
                analysis.get("sector_growth"),
                analysis.get("overall_risk"),
                analysis.get("risks", {}).get("market"),
                analysis.get("risks", {}).get("capital"),
                analysis.get("risks", {}).get("execution"),
                analysis.get("risks", {}).get("competition"),
                analysis.get("risks", {}).get("regulatory"),
                analysis.get("success_probability"),
                analysis.get("failure_probability"),
                json.dumps(analysis.get("revenue_projection", [])),
                analysis.get("positioning_summary"),
                analysis.get("audience_maturity", {}).get("audience_profile"),
                analysis.get("audience_maturity", {}).get("market_maturity"),
            ),
        )

        sizing = analysis.get("market_sizing", {})
        cur.execute(
            """
            INSERT INTO market_sizing (project_id, tam, sam, som, methodology_notes)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (
                project_id,
                sizing.get("tam"),
                sizing.get("sam"),
                sizing.get("som"),
                sizing.get("methodology_notes"),
            ),
        )

        for comp in analysis.get("competitors", []):
            cur.execute(
                """
                INSERT INTO competitors
                    (project_id, competitor_name, market_share_estimate, positioning_notes,
                     funding_stage, threat_level, strengths, weaknesses)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    project_id,
                    comp.get("name"),
                    comp.get("market_share_estimate"),
                    comp.get("positioning_notes"),
                    comp.get("funding_stage"),
                    comp.get("threat_level"),
                    json.dumps(comp.get("strengths", [])),
                    json.dumps(comp.get("weaknesses", [])),
                ),
            )

        for rec in analysis.get("recommendations", []):
            cur.execute(
                """
                INSERT INTO recommendations (project_id, category, recommendation_text, priority)
                VALUES (%s, %s, %s, %s);
                """,
                (
                    project_id,
                    rec.get("category"),
                    rec.get("text"),
                    rec.get("priority"),
                ),
            )

        for seg in analysis.get("adoption_distribution", []):
            cur.execute(
                """
                INSERT INTO adoption_distribution (project_id, segment, percentage)
                VALUES (%s, %s, %s);
                """,
                (
                    project_id,
                    seg.get("segment"),
                    seg.get("percentage"),
                ),
            )

        for trend in analysis.get("market_trends", []):
            cur.execute(
                """
                INSERT INTO market_trends (project_id, trend, description, impact)
                VALUES (%s, %s, %s, %s);
                """,
                (
                    project_id,
                    trend.get("trend"),
                    trend.get("description"),
                    trend.get("impact"),
                ),
            )

        for seg in analysis.get("customer_segments", []):
            cur.execute(
                """
                INSERT INTO customer_segments (project_id, segment, description, percentage)
                VALUES (%s, %s, %s, %s);
                """,
                (
                    project_id,
                    seg.get("segment"),
                    seg.get("description"),
                    seg.get("percentage"),
                ),
            )

        for mit in analysis.get("risk_mitigations", []):
            cur.execute(
                """
                INSERT INTO risk_mitigations (project_id, category, mitigation)
                VALUES (%s, %s, %s);
                """,
                (
                    project_id,
                    mit.get("category"),
                    mit.get("mitigation"),
                ),
            )

        for phase in analysis.get("action_plan", []):
            cur.execute(
                """
                INSERT INTO action_plan (project_id, phase, focus, actions)
                VALUES (%s, %s, %s, %s);
                """,
                (
                    project_id,
                    phase.get("phase"),
                    phase.get("focus"),
                    json.dumps(phase.get("actions", [])),
                ),
            )

        for point in analysis.get("market_growth_history", []):
            cur.execute(
                """
                INSERT INTO market_growth_history (project_id, year, market_size)
                VALUES (%s, %s, %s);
                """,
                (
                    project_id,
                    point.get("year"),
                    point.get("market_size"),
                ),
            )

        for challenge in analysis.get("industry_challenges", []):
            cur.execute(
                """
                INSERT INTO industry_challenges (project_id, challenge)
                VALUES (%s, %s);
                """,
                (
                    project_id,
                    challenge,
                ),
            )

        gp = analysis.get("growth_potential", {})
        if gp:
            cur.execute(
                """
                INSERT INTO growth_potential
                    (project_id, score, explanation, market_validation,
                     competitive_position, financial_model, technical_readiness)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    project_id,
                    gp.get("score"),
                    gp.get("explanation"),
                    gp.get("market_validation"),
                    gp.get("competitive_position"),
                    gp.get("financial_model"),
                    gp.get("technical_readiness"),
                ),
            )

        for opp in analysis.get("market_opportunities", []):
            cur.execute(
                """
                INSERT INTO market_opportunities (project_id, opportunity)
                VALUES (%s, %s);
                """,
                (
                    project_id,
                    opp,
                ),
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Warning: failed to persist analysis: {e}")
    finally:
        cur.close()
        conn.close()

    return {"project_id": project_id, "analysis": analysis}


@app.get("/api/projects/{project_id}")
async def get_project(project_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT startup_name, industry, business_model, target_market, budget, description, created_at "
        "FROM projects WHERE id = %s;", (project_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "startup_name": row[0], "industry": row[1], "business_model": row[2],
        "target_market": row[3], "budget": row[4], "description": row[5],
        "created_at": row[6].isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
