import os
import tempfile
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from budget_ai.db.database import Database
from budget_ai.budgets import budget_report
from budget_ai.models import CATEGORIES, Budget, Goal, Receipt, LineItem
from budget_ai.vision.agent import VisionAgent
from budget_ai.reasoning.agent import ReasoningAgent
from budget_ai.api.deps import get_db, get_client
from openai import OpenAI

# Load config
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app = FastAPI(title="Budget AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request bodies
class ReceiptCreate(BaseModel):
    merchant: str
    purchase_date: Optional[str] = None
    currency: str = "USD"
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float
    category: str = "other"
    items: List[LineItem] = []
    confidence: float = 1.0

class BudgetCreate(BaseModel):
    monthly_limit: float

class GoalCreate(BaseModel):
    name: str
    target_amount: float
    saved_amount: float = 0.0
    target_date: Optional[str] = None

class GoalContribute(BaseModel):
    amount: float

class AdviceRequest(BaseModel):
    question: str

# Endpoints

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/categories")
def list_categories():
    return CATEGORIES

@app.get("/api/report")
def get_report(month: Optional[str] = None, db: Database = Depends(get_db)):
    try:
        return budget_report(db, month=month)
    except Exception as e:
        raise HTTPException(status_code=502, detail="Internal server error during report generation")

@app.get("/api/spending")
def get_spending(month: Optional[str] = None, db: Database = Depends(get_db)):
    try:
        if month:
            return db.spending_by_category_for_month(month)
        return db.spending_by_category()
    except Exception as e:
        raise HTTPException(status_code=502, detail="Internal server error during spending calculation")

@app.get("/api/receipts")
def list_receipts(
    limit: int = 20, 
    offset: int = 0, 
    category: Optional[str] = None, 
    db: Database = Depends(get_db)
):
    try:
        items = db.list_receipts(limit=limit, offset=offset, category=category)
        return {"items": items, "limit": limit, "offset": offset}
    except Exception as e:
        raise HTTPException(status_code=502, detail="Internal server error during receipt listing")

@app.get("/api/receipts/{receipt_id}")
def get_receipt(receipt_id: int, db: Database = Depends(get_db)):
    receipt = db.get_receipt_with_items(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt

@app.post("/api/receipts/extract", status_code=status.HTTP_200_OK)
async def extract_receipt(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    if file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10 MB limit")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        client = get_client()
        model = os.getenv("VISION_MODEL", "gemma")
        agent = VisionAgent(client, model)
        receipt = agent.extract(tmp_path)
        
        warnings = receipt.arithmetic_warnings()
        needs_review = receipt.confidence < 0.6 or len(warnings) > 0
        
        return {"receipt": receipt, "warnings": warnings, "needs_review": needs_review}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vision agent error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/api/receipts", status_code=status.HTTP_201_CREATED)
def save_receipt(receipt_data: ReceiptCreate, db: Database = Depends(get_db)):
    try:
        receipt = Receipt(**receipt_data.model_dump())
        receipt_id = db.save_receipt(receipt)
        return {"id": receipt_id}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error saving receipt: {str(e)}")

@app.get("/api/budgets")
def list_budgets(db: Database = Depends(get_db)):
    return budget_report(db)["budgets"]

@app.put("/api/budgets/{category}")
def set_budget(category: str, budget_data: BudgetCreate, db: Database = Depends(get_db)):
    try:
        budget = Budget(category=category, monthly_limit=budget_data.monthly_limit)
        db.set_budget(budget)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error setting budget: {str(e)}")

@app.delete("/api/budgets/{category}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(category: str, db: Database = Depends(get_db)):
    db.delete_budget(category)
    return None

@app.get("/api/goals")
def list_goals(db: Database = Depends(get_db)):
    return budget_report(db)["goals"]

@app.post("/api/goals", status_code=status.HTTP_201_CREATED)
def add_goal(goal_data: GoalCreate, db: Database = Depends(get_db)):
    try:
        goal = Goal(**goal_data.model_dump())
        goal_id = db.add_goal(goal)
        return {"id": goal_id}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error adding goal: {str(e)}")

@app.post("/api/goals/{goal_id}/contribute")
def contribute_to_goal(goal_id: int, goal_data: GoalContribute, db: Database = Depends(get_db)):
    try:
        db.contribute_to_goal(goal_id, goal_data.amount)
        return {"status": "success"}
    except ValueError as e:
        if "does not exist" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error contributing to goal: {str(e)}")

@app.delete("/api/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: int, db: Database = Depends(get_db)):
    db.delete_goal(goal_id)
    return None

@app.post("/api/advice")
def get_advice(advice_data: AdviceRequest, db: Database = Depends(get_db)):
    try:
        client = get_client()
        model = os.getenv("REASONING_MODEL", "gemma")
        agent = ReasoningAgent(db, client, model)
        answer = agent.advise(advice_data.question)
        return {
            "answer": answer,
            "disclaimer": "General budgeting suggestions, not licensed financial advice."
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Reasoning agent error: {str(e)}")
