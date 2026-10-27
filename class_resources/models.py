import os
import uuid

from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from teachers.storage import get_private_storage


def plan_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"annual_plans/{uuid.uuid4().hex}{ext}"


class AnnualPlan(models.Model):
    """수업자료 > 연간계획서 (PDF)"""
    CATEGORIES = (
        ("robot", "로봇"),
        ("science", "과학"),
        ("math", "창의수학"),
        ("3dpen", "3D펜"),
        ("drone", "항공드론"),
    )

    title = models.CharField("제목", max_length=100)
    category = models.CharField("분류", max_length=20, choices=CATEGORIES)
    description = models.CharField("설명", max_length=200, blank=True)
    pdf = models.FileField("PDF 파일", upload_to=plan_upload_to, storage=get_private_storage)
    order = models.PositiveIntegerField("정렬 순서", default=0)
    created_at = models.DateTimeField("등록일", auto_now_add=True)

    class Meta:
        ordering = ["order", "title"]
        verbose_name = "연간계획서"
        verbose_name_plural = "연간계획서"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


@receiver(post_delete, sender=AnnualPlan)
def _delete_plan_file(sender, instance, **kwargs):
    if instance.pdf:
        instance.pdf.delete(save=False)
