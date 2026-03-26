"""
Webhook router — mounts all webhook source routers under /webhooks.
"""
from fastapi import APIRouter

from webhook.pagerduty import router as pd_router
from webhook.alertmanager import router as am_router
from webhook.datadog_events import router as dd_router

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

router.include_router(pd_router)
router.include_router(am_router)
router.include_router(dd_router)
