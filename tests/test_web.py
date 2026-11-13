from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings


User = get_user_model()


class PublicAndAccountTests(TestCase):
    def test_guest_sees_public_pages_and_is_redirected_from_game(self):
        self.assertContains(self.client.get("/"), "Богатей")
        self.assertEqual(self.client.get("/leaderboard/").status_code, 200)
        self.assertRedirects(self.client.get("/play/"), "/login/?next=/play/")

    def test_registration_shows_error_for_short_password(self):
        response = self.client.post("/register/", {
            "username": "newplayer", "password1": "1", "password2": "1",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="newplayer").exists())

    def test_valid_registration_login_and_logout(self):
        data = {"username": "newplayer", "password1": "s0me-test-Pass!", "password2": "s0me-test-Pass!"}
        self.assertRedirects(self.client.post("/register/", data), "/login/")
        bad_login = self.client.post("/login/", {"username": "newplayer", "password": "wrong"})
        self.assertTrue(bad_login.context["form"].errors)
        self.assertRedirects(self.client.post("/login/", {
            "username": "newplayer", "password": data["password1"],
        }), "/play/")
        self.assertRedirects(self.client.post("/logout/"), "/")
        self.assertRedirects(self.client.get("/play/"), "/login/?next=/play/")

    @override_settings(DEBUG=False)
    def test_custom_404(self):
        self.assertContains(self.client.get("/missing/"), "Страница не найдена", status_code=404)
