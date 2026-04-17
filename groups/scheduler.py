import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django.utils import timezone
from .models import Discussion

logger = logging.getLogger(__name__)

def cleanup_expired_proposals():
    """Cancel POOLING/VOTING proposals that have expired due to insufficient funding."""
    now = timezone.now()
    
    # Check for POOLING proposals that passed expires_at
    expired_proposals = Discussion.objects.filter(
        status='pooling',
        expires_at__lt=now
    )
    
    count = expired_proposals.count()
    if count > 0:
        # We don't automatically refund here because the funds are in the pooled GroupWallet.
        # But we do close the proposal to free the group to propose something else.
        expired_proposals.update(status='cancelled')
        print(f"[Scheduler] Cancelled {count} unfunded expired proposals.")

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    scheduler.add_job(
        cleanup_expired_proposals,
        trigger=IntervalTrigger(minutes=1),  # Check every 1 minute
        id="cleanup_expired_proposals",
        max_instances=1,
        replace_existing=True,
    )
    
    try:
        scheduler.start()
        print("[Scheduler] Started background jobs.")
    except Exception as e:
        print(f"[Scheduler] Failed to start scheduler: {e}")
