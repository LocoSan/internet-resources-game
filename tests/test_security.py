from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from game.models import GameSession, Leaderboard, UserProfile


User = get_user_model()
PASSWORD = "s0me-test-Pass!"


class SecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("player", password=PASSWORD)
        cls.profile = UserProfile.objects.create(user=cls.user, bio='<img src=x onerror="alert(1)">')
        cls.game = GameSession.objects.create(player=cls.profile)
        Leaderboard.objects.create(player=cls.profile, difficulty="easy", score=10)

    def test_password_is_hashed(self):
        self.assertNotEqual(self.user.password, PASSWORD)
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_login_input_cannot_inject_sql(self):
        response = self.client.post("/login/", {"username": "' OR 1=1 --", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_escapes_xss(self):
        response = self.client.get("/players/player/")
        self.assertContains(response, "&lt;img")
        self.assertNotContains(response, '<img src=x onerror="alert(1)">')

    def test_admin_search_uses_safe_orm_and_escapes_profile_content(self):
        admin = User.objects.create_superuser("admin", password=PASSWORD)
        self.client.force_login(admin)
        response = self.client.get("/admin/game/gamesession/", {"q": "' OR 1=1 --"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["cl"].result_count, 0)
        self.assertEqual(GameSession.objects.count(), 1)
        profile = self.client.get(f"/admin/game/userprofile/{self.profile.pk}/change/")
        self.assertContains(profile, "&lt;img")
        self.assertNotContains(profile, '<img src=x onerror="alert(1)">')

    def test_click_requires_post_and_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        url = f"/play/{self.game.pk}/click/"
        self.assertEqual(client.get(url).status_code, 405)
        self.assertEqual(client.post(url).status_code, 403)
        self.game.refresh_from_db()
        self.assertEqual(self.game.score, 0)

    def test_leaderboard_query_count_does_not_grow_with_players(self):
        for number in range(8):
            profile = UserProfile.objects.create(user=User.objects.create_user(f"p{number}"))
            Leaderboard.objects.create(player=profile, difficulty="easy", score=number)
        with self.assertNumQueries(1):
            response = self.client.get("/leaderboard/?difficulty=easy")
        self.assertContains(response, "p7")
