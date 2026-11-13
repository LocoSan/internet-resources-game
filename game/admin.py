from io import BytesIO

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from openpyxl import Workbook

from .forms import validate_avatar
from .models import Achievement, GameSession, Item, Leaderboard, Purchase, UserProfile


class ProfileAdminForm(forms.ModelForm):
    def clean_avatar(self):
        return validate_avatar(self.cleaned_data.get("avatar"))


@admin.register(UserProfile)
class ProfileAdmin(admin.ModelAdmin):
    form = ProfileAdminForm
    list_display = ("user", "coins", "updated_at")
    search_fields = ("user__username",)
    filter_horizontal = ("achievements",)


COLUMNS = {
    "player": ("Игрок", lambda game: game.player.user.username),
    "date": ("Когда", lambda game: timezone.localtime(game.updated_at).replace(tzinfo=None)),
    "difficulty": ("Сложность", lambda game: game.get_difficulty_display()),
    "score": ("Очки", lambda game: game.score),
    "level": ("Уровень", lambda game: game.level),
    "time_played": ("Время, с", lambda game: game.time_played),
    "is_completed": ("Завершена", lambda game: game.is_completed),
}


class ExportForm(forms.Form):
    columns = forms.MultipleChoiceField(
        label="Поля для выгрузки", widget=forms.CheckboxSelectMultiple,
        choices=[(name, label) for name, (label, _) in COLUMNS.items()],
        initial=("player", "date", "score"),
    )


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ("player", "difficulty", "score", "level", "is_completed", "updated_at")
    list_select_related = ("player__user",)
    list_filter = ("difficulty", "is_completed")
    search_fields = ("player__user__username",)
    actions = ("export_xlsx",)

    @admin.action(description="Выгрузить выбранные игры в XLSX")
    def export_xlsx(self, request, queryset):
        form = ExportForm(request.POST if "export" in request.POST else None)
        if "export" in request.POST and form.is_valid():
            columns = [name for name in COLUMNS if name in form.cleaned_data["columns"]]
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Игровые сессии"
            sheet.append([COLUMNS[name][0] for name in columns])
            for game in queryset.select_related("player__user").iterator():
                sheet.append([COLUMNS[name][1](game) for name in columns])
                # Текст из профиля должен остаться текстом, даже если начинается с "=".
                for cell in sheet[sheet.max_row]:
                    if cell.data_type == "f":
                        cell.data_type = "s"
            data = BytesIO()
            workbook.save(data)
            response = HttpResponse(data.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response["Content-Disposition"] = 'attachment; filename="game-sessions.xlsx"'
            return response
        if form.errors:
            self.message_user(request, "Выберите хотя бы один столбец.", messages.WARNING)
        return TemplateResponse(request, "admin/export_games.html", {
            **self.admin_site.each_context(request),
            "title": "Выгрузка игровых сессий",
            "form": form, "selected": request.POST.getlist(ACTION_CHECKBOX_NAME),
            "select_across": request.POST.get("select_across", "0"),
        })


admin.site.register((Leaderboard, Achievement, Item, Purchase))
admin.site.site_header = "Управление игрой «Богатей»"
