from django.urls import include, path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from game import api


router = SimpleRouter()
router.register("games", api.Games, basename="api-games")

urlpatterns = [
    path("register/", api.Register.as_view()),
    path("token/", TokenObtainPairView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("players/<str:username>/", api.PublicProfile.as_view()),
    path("profile/", api.OwnProfile.as_view()),
    path("leaderboard/", api.Scores.as_view()),
    path("achievements/", api.Achievements.as_view()),
    path("items/", api.Items.as_view()),
    path("items/<int:pk>/buy/", api.Buy.as_view()),
    path("", include(router.urls)),
]
