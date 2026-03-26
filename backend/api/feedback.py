"""
Feedback API endpoint.
Records thumbs-up / thumbs-down on triage results.
"""
from fastapi import APIRouter, HTTPException

from db import update_triage_feedback, get_alert_by_id
from models import FeedbackRequest

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("")
async def submit_feedback(body: FeedbackRequest) -> dict:
    existing = await get_alert_by_id(body.alert_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Alert not found")

    await update_triage_feedback(body.alert_id, body.rating)
    return {"status": "ok", "alert_id": body.alert_id, "rating": body.rating}
