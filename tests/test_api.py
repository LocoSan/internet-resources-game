from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from game.models import Achievement, GameSession, Item, Purchase, UserProfile


User = get_user_model()
PASSWORD = "s0me-test-Pass!"


class ApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("player", password=PASSWORD)
        self.profile = UserProfile.objects.create(user=self.user)

    def login(self):
        result = self.client.post("/api/token/", {"username": "player", "password": PASSWORD})
        self.assertEqual(result.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + result.data["access"])
        return result.data["refresh"]

    def test_jwt_registration_validation_and_refresh(self):
        self.assertEqual(self.client.post("/api/register/", {"username": "a", "password": "1"}).status_code, 400)
        self.assertEqual(self.client.post("/api/register/", {"username": "other", "password": PASSWORD}).status_code, 201)
        self.assertEqual(self.client.post("/api/token/refresh/", {"refresh": self.login()}).status_code, 200)

    def test_guest_can_only_see_public_game_data(self):
        self.assertEqual(self.client.get("/api/leaderboard/").status_code, 200)
        response = self.client.get("/api/players/player/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("date_of_birth", response.data)
        for path in ["/api/profile/", "/api/games/", "/api/games/latest/", "/api/achievements/", "/api/items/"]:
            self.assertEqual(self.client.get(path).status_code, 401, path)

    def test_game_cycle_and_ownership(self):
        Achievement.objects.create(name="Первый клик", score_required=1)
        other = UserProfile.objects.create(user=User.objects.create_user("other"))
        foreign_game = GameSession.objects.create(player=other, score=1000)
        self.login()
        self.assertEqual(self.client.get("/api/games/latest/").status_code, 404)
        response = self.client.post("/api/games/", {"difficulty": "hard"})
        self.assertEqual(response.status_code, 201)
        game_id = response.data["id"]
        url = f"/api/games/{game_id}/"
        self.assertEqual(self.client.get(url).data["score"], 0)
        self.assertEqual(self.client.post(url + "click/", {"score": 999}).data["score"], 1)
        self.assertEqual(self.client.get("/api/games/latest/").data["game_state"]["clicks"], 1)
        self.assertEqual(self.client.get(f"/api/games/{foreign_game.pk}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/games/{foreign_game.pk}/").status_code, 404)
        self.assertEqual(self.client.post(url + "finish/").status_code, 200)
        self.assertEqual(self.client.post(url + "click/").status_code, 400)
        self.assertEqual(self.client.get("/api/leaderboard/?difficulty=hard").data[0]["score"], 1)
        self.assertEqual(len(self.client.get("/api/leaderboard/?difficulty=easy").data), 0)
        self.assertEqual(len(self.client.get("/api/leaderboard/?since=2099-01-01").data), 0)
        self.assertEqual(len(self.client.get("/api/achievements/").data), 1)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(GameSession.objects.filter(pk=game_id).exists())

    def test_store_checks_balance_duplicate_and_applies_bonus(self):
        item = Item.objects.create(name="Кольцо", price=2, click_bonus=3)
        self.login()
        url = f"/api/items/{item.pk}/buy/"
        self.assertEqual(self.client.post(url).status_code, 400)
        self.profile.coins = 5
        self.profile.save()
        self.assertEqual(self.client.post(url).status_code, 201)
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertEqual(Purchase.objects.get().paid, 2)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.coins, 3)
        game = GameSession.objects.create(player=self.profile)
        self.assertEqual(self.client.post(f"/api/games/{game.pk}/click/").data["score"], 4)
