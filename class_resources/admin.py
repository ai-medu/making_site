from django.contrib import admin

from .models import AnnualPlan


@admin.register(AnnualPlan)
class AnnualPlanAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "order", "created_at")
    list_filter = ("category",)
