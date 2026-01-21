from celery import shared_task
from .services import BookingService


@shared_task
def expire_old_seat_holds():
    expired_count = BookingService.expire_old_seat_holds()
    return f"Expired {expired_count} seat holds"
