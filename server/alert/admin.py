from alert.models import AlertCounter, AlertState
from core.admin import base_site
from django.contrib import admin


class AlertStateCustomAdmin(admin.ModelAdmin):
    """Админка статусов тревоги."""

    ordering = ["order"]
    list_display = ("name", "id", "current", "ingame", "info", "threshold", "counter_increase", "counter_decrease")
    list_filter = ["ingame"]

    fieldsets = (
        (
            "Параметры уровня тревоги",
            {"classes": ("none",), "fields": (("name", "current"), ("info", "order"), "ingame", "threshold")},
        ),
        (
            "Реакции на действие игроков",
            {
                "classes": ("none",),
                "fields": ("counter_increase", "counter_decrease"),
            },
        ),
        (
            "Автоматическое изменение уровня",
            {
                "classes": ("none",),
                "fields": ("auto_change", "auto_level", "auto_timeout"),
            },
        ),
    )


class AlertCounterCustomAdmin(admin.ModelAdmin):
    """Админка счетчиков тревоги."""

    list_display = ("timestamp", "value", "comment")
    readonly_fields = ("timestamp",)


base_site.register(AlertCounter, AlertCounterCustomAdmin, site=base_site)
base_site.register(AlertState, AlertStateCustomAdmin, site=base_site)
