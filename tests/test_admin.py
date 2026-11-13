from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from game.models import GameSession, UserProfile


User = get_user_model()


class AdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin", password="A-test-password-1")
        self.user = User.objects.create_user("=1+2", password="A-test-password-2")
        self.profile = UserProfile.objects.create(user=self.user)
        self.selected = GameSession.objects.create(player=self.profile, score=12)
        GameSession.objects.create(player=self.profile, score=99)

    def test_ordinary_user_cannot_open_admin(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get("/admin/"), "/admin/login/?next=/admin/")

    def test_xlsx_uses_only_selected_rows_and_columns_and_plain_strings(self):
        self.client.force_login(self.admin)
        url = reverse("admin:game_gamesession_changelist")
        action = {
            "action": "export_xlsx", "_selected_action": str(self.selected.pk), "index": 0,
        }
        choice = self.client.post(url, action)
        self.assertContains(choice, "Поля для выгрузки")
        response = self.client.post(url, {**action, "export": "1", "columns": ["player", "score"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        book = load_workbook(BytesIO(response.content))
        sheet = book.active
        self.assertEqual(list(sheet.values), [("Игрок", "Очки"), ("=1+2", 12)])
        self.assertEqual(sheet["A2"].data_type, "s")
