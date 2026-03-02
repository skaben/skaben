from core.admin import base_site
from django.contrib import admin

from polymorphic.admin import PolymorphicInlineSupportMixin, PolymorphicParentModelAdmin, PolymorphicChildModelAdmin

from peripheral_behavior.models import (
    AccessCode,
    SkabenUser,
    TerminalAccount,
    MenuItem,
    MenuItemImage,
    MenuItemVideo,
    MenuItemAudio,
    MenuItemText,
    MenuItemUserInput,
)


menu_inline_fields = ("label", "content", "timer")


class MenuItemAdmin(PolymorphicParentModelAdmin):
    verbose_name = "Пункт меню"
    verbose_name_plural = "Пункты меню"
    model = TerminalAccount.menu_items.through

    child_models = (
        MenuItemAudio,
        MenuItemVideo,
        MenuItemImage,
        MenuItemText,
        MenuItemUserInput,
    )


class PolymorphicChildInvisible(PolymorphicChildModelAdmin):
    def get_model_perms(self, request):
        return {"add": False, "change": False, "delete": False}


class MenuItemAudioAdmin(PolymorphicChildInvisible):
    model = MenuItemAudio
    fields = menu_inline_fields
    verbose_name = "Меню: аудио"


class MenuItemVideoAdmin(PolymorphicChildInvisible):
    model = MenuItemVideo
    fields = menu_inline_fields
    verbose_name = "Меню: видео"


class MenuItemImageAdmin(PolymorphicChildInvisible):
    model = MenuItemImage
    fields = menu_inline_fields
    verbose_name = "Меню: изображение"


class MenuItemTextAdmin(PolymorphicChildInvisible):
    model = MenuItemText
    fields = menu_inline_fields
    verbose_name = "Меню: текст"


class MenuItemUserInputAdmin(PolymorphicChildInvisible):
    model = MenuItemUserInput
    fields = ("label", "content", "input_label", "input_description", "timer")
    verbose_name = "Меню: пользовательский ввод"


class TerminalAccountAdmin(PolymorphicInlineSupportMixin, admin.ModelAdmin):
    fields = (
        "user",
        "password",
        "header",
        "footer",
        "menu_items",
    )


base_site.register(MenuItem, MenuItemAdmin, site=base_site)

# registering invisible polymorphic child admins
base_site.register(MenuItemText, MenuItemTextAdmin)
base_site.register(MenuItemAudio, MenuItemAudioAdmin)
base_site.register(MenuItemVideo, MenuItemVideoAdmin)
base_site.register(MenuItemImage, MenuItemImageAdmin)
base_site.register(MenuItemUserInput, MenuItemUserInputAdmin)

base_site.register(SkabenUser, admin.ModelAdmin, site=base_site)
base_site.register(AccessCode, admin.ModelAdmin, site=base_site)
base_site.register(TerminalAccount, TerminalAccountAdmin, site=base_site)
