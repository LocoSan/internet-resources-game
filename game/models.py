from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Difficulty(models.TextChoices):
    EASY = "easy", "Легко"
    MEDIUM = "medium", "Средне"
    HARD = "hard", "Сложно"


class Achievement(TimeStampedModel):
    name = models.CharField("название", max_length=80, unique=True)
    description = models.CharField("описание", max_length=200)
    score_required = models.PositiveIntegerField("очки для получения", null=True, blank=True, unique=True)

    def __str__(self):
        return self.name


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField("аватар", upload_to="avatars/", blank=True)
    bio = models.TextField("о себе", max_length=300, blank=True)
    date_of_birth = models.DateField("дата рождения", null=True, blank=True)
    coins = models.PositiveIntegerField("монеты", default=0)
    achievements = models.ManyToManyField(Achievement, blank=True, related_name="profiles")

    def clean(self):
        if self.date_of_birth and self.date_of_birth > timezone.localdate():
            raise ValidationError({"date_of_birth": "Дата рождения не может быть в будущем."})

    def __str__(self):
        return self.user.username


class GameSession(TimeStampedModel):
    player = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="sessions")
    difficulty = models.CharField("сложность", max_length=6, choices=Difficulty.choices, default=Difficulty.EASY)
    game_state = models.JSONField("состояние", default=dict, blank=True)
    score = models.PositiveIntegerField("очки", default=0)
    level = models.PositiveIntegerField("уровень", default=1, validators=[MinValueValidator(1)])
    time_played = models.PositiveIntegerField("время игры, с", default=0)
    is_completed = models.BooleanField("завершена", default=False)

    class Meta:
        ordering = ("-updated_at", "-pk")

    def __str__(self):
        return f"{self.player} — {self.get_difficulty_display()}, {self.score} очков"


class Leaderboard(TimeStampedModel):
    player = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="records")
    difficulty = models.CharField("сложность", max_length=6, choices=Difficulty.choices)
    score = models.PositiveIntegerField("очки")
    rank = models.PositiveIntegerField("место", default=1, validators=[MinValueValidator(1)])
    date_achieved = models.DateTimeField("дата рекорда", default=timezone.now)

    class Meta:
        ordering = ("-score", "date_achieved", "pk")
        constraints = [
            models.UniqueConstraint(fields=("player", "difficulty"), name="one_record_per_difficulty"),
        ]

    def __str__(self):
        return f"{self.player} — {self.score}"


class Item(TimeStampedModel):
    name = models.CharField("название", max_length=80, unique=True)
    description = models.CharField("описание", max_length=200)
    price = models.PositiveIntegerField("цена", validators=[MinValueValidator(1)])
    click_bonus = models.PositiveIntegerField("бонус за клик", validators=[MinValueValidator(1), MaxValueValidator(100)])

    class Meta:
        ordering = ("price", "name")

    def __str__(self):
        return self.name


class Purchase(TimeStampedModel):
    player = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="purchases")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="purchases")
    paid = models.PositiveIntegerField("уплачено")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("player", "item"), name="one_purchase_per_player_and_item"),
        ]

    def __str__(self):
        return f"{self.player} — {self.item}"
