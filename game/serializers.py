from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers

from .forms import validate_avatar
from .models import Achievement, GameSession, Item, Leaderboard, Purchase, UserProfile
from .services import profile_for


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = get_user_model()
        fields = ("username", "password")

    def validate(self, data):
        try:
            validate_password(data["password"], self.Meta.model(username=data["username"]))
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages}) from error
        return data

    def create(self, validated_data):
        user = self.Meta.model.objects.create_user(**validated_data)
        profile_for(user)
        return user


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ("id", "name", "description", "score_required")


class PublicProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    avatar = serializers.SerializerMethodField()
    achievements = AchievementSerializer(many=True, read_only=True)

    class Meta:
        model = UserProfile
        fields = ("username", "bio", "avatar", "achievements")

    def get_avatar(self, profile):
        if profile.avatar:
            return reverse("avatar", args=[profile.user.username])
        return None


class OwnProfileSerializer(PublicProfileSerializer):
    avatar_upload = serializers.ImageField(source="avatar", write_only=True, required=False)

    class Meta(PublicProfileSerializer.Meta):
        fields = PublicProfileSerializer.Meta.fields + ("date_of_birth", "coins", "avatar_upload")
        read_only_fields = ("coins",)

    def validate_date_of_birth(self, date):
        if date and date > timezone.localdate():
            raise serializers.ValidationError("Дата рождения не может быть в будущем.")
        return date

    def validate_avatar_upload(self, upload):
        try:
            return validate_avatar(upload)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameSession
        fields = ("id", "difficulty", "game_state", "score", "level", "time_played", "is_completed", "created_at", "updated_at")
        read_only_fields = ("game_state", "score", "level", "time_played", "is_completed")


class LeaderboardSerializer(serializers.ModelSerializer):
    player = serializers.CharField(source="player.user.username", read_only=True)

    class Meta:
        model = Leaderboard
        fields = ("player", "difficulty", "score", "rank", "date_achieved")


class ItemSerializer(serializers.ModelSerializer):
    owned = serializers.BooleanField(read_only=True)

    class Meta:
        model = Item
        fields = ("id", "name", "description", "price", "click_bonus", "owned")


class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = ("id", "item", "paid", "created_at")
