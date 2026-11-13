from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import GameSession, Item, UserProfile
from .serializers import (
    AchievementSerializer, GameSerializer, ItemSerializer, LeaderboardSerializer,
    OwnProfileSerializer, PublicProfileSerializer, PurchaseSerializer, RegisterSerializer,
)
from .services import buy_item, click_coin, finish_game, leaderboard, profile_for


class Register(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class PublicProfile(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicProfileSerializer
    queryset = UserProfile.objects.select_related("user").prefetch_related("achievements")
    lookup_field = "user__username"
    lookup_url_kwarg = "username"


class OwnProfile(generics.RetrieveUpdateAPIView):
    serializer_class = OwnProfileSerializer

    def get_object(self):
        return profile_for(self.request.user)


class Games(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
            mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = GameSerializer

    def get_queryset(self):
        return GameSession.objects.filter(player__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(player=profile_for(self.request.user))

    @action(detail=False, methods=["get"])
    def latest(self, request):
        game = self.get_queryset().first()
        if game is None:
            raise NotFound("Сохранений пока нет.")
        return Response(self.get_serializer(game).data)

    @action(detail=True, methods=["post"])
    def click(self, request, pk=None):
        try:
            game, coins = click_coin(self.get_object())
        except ValueError as error:
            raise ValidationError(str(error)) from error
        return Response({**self.get_serializer(game).data, "coins": coins})

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        game = finish_game(self.get_object())
        return Response(self.get_serializer(game).data)


class Scores(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = LeaderboardSerializer

    def get_queryset(self):
        return leaderboard(
            self.request.query_params.get("difficulty", ""),
            self.request.query_params.get("since", ""),
        )[:100]


class Achievements(generics.ListAPIView):
    serializer_class = AchievementSerializer

    def get_queryset(self):
        return profile_for(self.request.user).achievements.all()


class Items(generics.ListAPIView):
    serializer_class = ItemSerializer

    def get_queryset(self):
        owned = set(profile_for(self.request.user).purchases.values_list("item_id", flat=True))
        items = list(Item.objects.all())
        for item in items:
            item.owned = item.pk in owned
        return items


class Buy(generics.GenericAPIView):
    serializer_class = PurchaseSerializer

    def post(self, request, pk):
        item = get_object_or_404(Item, pk=pk)
        try:
            purchase = buy_item(profile_for(request.user), item)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        return Response(self.get_serializer(purchase).data, status=status.HTTP_201_CREATED)
