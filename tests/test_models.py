from datetime import datetime, timedelta, timezone as utc
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from game.forms import GameForm, ProfileForm
from game.models import Achievement, GameSession, Item, Leaderboard, Purchase, UserProfile
from game.serializers import OwnProfileSerializer
from game.services import leaderboard


User = get_user_model()


class ModelAndFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = UserProfile.objects.create(user=User.objects.create_user("player"))

    def test_create_all_models_and_load_relations(self):
        achievement = Achievement.objects.create(name="Первая монета", score_required=1)
        self.profile.achievements.add(achievement)
        game = GameSession.objects.create(player=self.profile, game_state={"clicks": 4})
        record = Leaderboard.objects.create(player=self.profile, difficulty="easy", score=4)
        item = Item.objects.create(name="Кольцо", price=5, click_bonus=1)
        purchase = Purchase.objects.create(player=self.profile, item=item, paid=5)
        self.assertEqual(self.profile.user.profile, self.profile)
        self.assertEqual(self.profile.achievements.get(), achievement)
        self.assertEqual(achievement.profiles.get(), self.profile)
        self.assertEqual(self.profile.sessions.get().game_state, {"clicks": 4})
        self.assertEqual(self.profile.records.get(), record)
        self.assertEqual(item.purchases.get(), purchase)
        self.assertEqual(purchase.player, game.player)
        for instance in (achievement, game, self.profile, record, item, purchase):
            self.assertIsNotNone(instance.created_at)
            self.assertIsNotNone(instance.updated_at)

    def test_timestamp_changes_only_updated_at_on_edit(self):
        start = datetime(2026, 1, 1, tzinfo=utc.utc)
        end = start + timedelta(seconds=5)
        with patch("django.utils.timezone.now", return_value=start):
            game = GameSession.objects.create(player=self.profile)
        with patch("django.utils.timezone.now", return_value=end):
            game.score = 4
            game.save()
        game.refresh_from_db()
        self.assertEqual(game.created_at, start)
        self.assertEqual(game.updated_at, end)

    def test_unique_record_and_purchase_constraints(self):
        item = Item.objects.create(name="Кольцо", price=5, click_bonus=1)
        Purchase.objects.create(player=self.profile, item=item, paid=5)
        Leaderboard.objects.create(player=self.profile, difficulty="easy", score=4)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Purchase.objects.create(player=self.profile, item=item, paid=5)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Leaderboard.objects.create(player=self.profile, difficulty="easy", score=5)

    def test_model_validators(self):
        with self.assertRaises(ValidationError) as caught:
            GameSession(player=self.profile, difficulty="unknown", level=0).full_clean()
        self.assertEqual(set(caught.exception.message_dict), {"difficulty", "level"})

    def test_game_form_and_profile_form_validate_input(self):
        self.assertTrue(GameForm({"difficulty": "easy"}).is_valid())
        self.assertIn("difficulty", GameForm({"difficulty": "unknown"}).errors)
        self.assertTrue(ProfileForm({"bio": "Игрок", "date_of_birth": "2000-01-01"}).is_valid())
        future = timezone.localdate() + timedelta(days=1)
        self.assertIn("date_of_birth", ProfileForm({"date_of_birth": future.isoformat()}).errors)

    def test_profile_form_does_not_overwrite_earned_coins(self):
        profile = UserProfile.objects.get(pk=self.profile.pk)
        form = ProfileForm({"bio": "Новое описание"}, instance=profile)
        self.assertTrue(form.is_valid())
        UserProfile.objects.filter(pk=profile.pk).update(coins=10)
        form.save()
        profile.refresh_from_db()
        self.assertEqual((profile.bio, profile.coins), ("Новое описание", 10))

    def test_profile_api_does_not_overwrite_earned_coins(self):
        profile = UserProfile.objects.get(pk=self.profile.pk)
        serializer = OwnProfileSerializer(profile, data={"bio": "Новый профиль"}, partial=True)
        self.assertTrue(serializer.is_valid())
        UserProfile.objects.filter(pk=profile.pk).update(coins=10)
        serializer.save()
        profile.refresh_from_db()
        self.assertEqual((profile.bio, profile.coins), ("Новый профиль", 10))

    def test_public_rank_follows_current_scores_after_admin_changes(self):
        other = UserProfile.objects.create(user=User.objects.create_user("other"))
        first = Leaderboard.objects.create(player=self.profile, difficulty="easy", score=10)
        Leaderboard.objects.create(player=other, difficulty="easy", score=5, rank=2)
        first.delete()
        self.assertEqual(leaderboard("easy").get().current_rank, 1)
