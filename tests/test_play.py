from django.contrib.auth import get_user_model
from django.test import TestCase

from game.models import Achievement, GameSession, Item, Leaderboard, UserProfile


User = get_user_model()


class WebGameTests(TestCase):
    def test_browser_views_create_update_read_finish_and_delete(self):
        user = User.objects.create_user("player")
        profile = UserProfile.objects.create(user=user)
        self.client.force_login(user)
        self.assertEqual(self.client.post("/play/", {"difficulty": "unknown"}).status_code, 200)
        self.assertFalse(GameSession.objects.exists())
        response = self.client.post("/play/", {"difficulty": "medium"})
        game = profile.sessions.get()
        url = f"/play/{game.pk}/"
        self.assertRedirects(response, url)
        self.assertEqual(self.client.post(url + "click/").json()["score"], 1)
        self.assertContains(self.client.get(url), '<strong id="score">1</strong>', html=True)
        self.assertRedirects(self.client.post(url + "finish/"), url)
        game.refresh_from_db()
        self.assertTrue(game.is_completed)
        self.assertEqual(Leaderboard.objects.get(player=profile).score, 1)
        self.assertContains(self.client.get("/leaderboard/?difficulty=medium"), "player")
        self.assertNotContains(self.client.get("/leaderboard/?difficulty=hard"), "/players/player/")
        self.assertRedirects(self.client.post(url + "delete/"), "/play/")
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_click_grants_achievement_and_store_debits_coins(self):
        user = User.objects.create_user("player")
        profile = UserProfile.objects.create(user=user, coins=4)
        game = GameSession.objects.create(player=profile)
        item = Item.objects.create(name="Кольцо", price=5, click_bonus=1)
        achievement = Achievement.objects.create(name="Первая монета", score_required=1)
        self.client.force_login(user)
        self.assertEqual(self.client.post(f"/play/{game.pk}/click/").status_code, 200)
        self.assertEqual(profile.achievements.get(), achievement)
        response = self.client.post(f"/store/{item.pk}/buy/", follow=True)
        self.assertContains(response, "Уже куплен")
        profile.refresh_from_db()
        self.assertEqual(profile.coins, 0)
        self.assertEqual(self.client.post(f"/play/{game.pk}/click/").json()["score"], 3)

    def test_another_player_cannot_open_or_edit_game(self):
        user = User.objects.create_user("owner")
        game = GameSession.objects.create(player=UserProfile.objects.create(user=user))
        self.client.force_login(User.objects.create_user("other"))
        self.assertEqual(self.client.get(f"/play/{game.pk}/").status_code, 404)
        self.assertEqual(self.client.post(f"/play/{game.pk}/click/").status_code, 404)
        self.assertEqual(self.client.post(f"/play/{game.pk}/delete/").status_code, 404)
        self.assertTrue(GameSession.objects.filter(pk=game.pk).exists())
