from core.admin import base_site
from django.contrib import admin

from streams.models import StreamRecord


class StreamRecordAdmin(admin.ModelAdmin):
    ordering = ("-timestamp",)
    list_display = ("human_time", "stream", "source", "mark", "message")
    list_filter = ("stream", "source", "mark")
    search_fields = ("stream", "source", "mark", "message")


base_site.register(StreamRecord, StreamRecordAdmin, base_site=base_site)
