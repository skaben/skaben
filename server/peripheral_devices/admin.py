from core.admin import base_site
from django.contrib import admin
from peripheral_behavior.models import Permission, TerminalMenuSet
from peripheral_devices.models.lock import LockDevice
from peripheral_devices.models.terminal import TerminalDevice
from peripheral_devices.models.passive import PassiveConfig


class PermissionInline(admin.StackedInline):
    model = Permission
    extra = 1


class TerminalMenuSetInline(admin.StackedInline):
    model = TerminalMenuSet
    extra = 1


class PassiveDeviceAdmin(admin.ModelAdmin):
    model = PassiveConfig

    list_display = ("topic", "get_state_name", "get_details")

    @admin.display(ordering="state__order", description="Уровень тревоги")
    def get_state_name(self, obj):
        return obj.state.name

    @admin.display(description="Описание")
    def get_details(self, obj):
        return obj.comment or str(obj.config)[:30]


class DeviceAdmin(admin.ModelAdmin):
    readonly_fields = ("timestamp", "alert", "online")
    list_display = (
        "description",
        "online",
        "ip",
        "mac_addr",
    )

    fieldsets = (
        (
            None,
            {
                "classes": ("none",),
                "fields": ("timestamp", "alert", "online"),
            },
        ),
        (
            "Параметры устройства",
            {
                "classes": ("none",),
                "fields": ("ip", "mac_addr", "description"),
            },
        ),
        (
            "Отключить авто-обновление конфигурации",
            {
                "classes": ("collapse",),
                "fields": ("override",),
            },
        ),
    )

    def save_formset(self, request, form, formset, change):
        formset.save()
        form.instance.save()


class LockAdmin(DeviceAdmin):
    inlines = [PermissionInline]
    list_display = DeviceAdmin.list_display + ("closed", "blocked", "sound", "override")
    list_editable = DeviceAdmin.list_editable + ("closed", "blocked", "sound")
    fieldsets = DeviceAdmin.fieldsets + (
        (
            "Настройки замка",
            {
                "classes": ("none",),
                "fields": ("closed", "blocked", "sound", "timer"),
            },
        ),
    )


class TerminalAdmin(DeviceAdmin):
    inlines = [TerminalMenuSetInline]
    list_display = DeviceAdmin.list_display + ("blocked", "powered")
    list_editable = DeviceAdmin.list_editable + ("blocked", "powered")
    fieldsets = DeviceAdmin.fieldsets + (
        (
            "Настройки терминала",
            {
                "classes": ("none",),
                "fields": ("powered", "blocked"),
            },
        ),
    )


base_site.register(LockDevice, LockAdmin, site=base_site)
base_site.register(TerminalDevice, TerminalAdmin, site=base_site)
# регистрируется как девайс, т.к. нет отдельного поведения
base_site.register(PassiveConfig, PassiveDeviceAdmin, site=base_site)
