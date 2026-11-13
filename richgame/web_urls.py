from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from game import views


urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", LoginView.as_view(
        template_name="game/form.html", extra_context={"title": "Вход", "submit": "Войти"},
    ), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("play/", views.play, name="play"),
    path("play/<int:pk>/", views.session, name="session"),
    path("play/<int:pk>/click/", views.click, name="click"),
    path("play/<int:pk>/finish/", views.finish, name="finish"),
    path("play/<int:pk>/delete/", views.delete, name="delete"),
    path("leaderboard/", views.scores, name="leaderboard"),
    path("players/<str:username>/", views.public_profile, name="profile"),
    path("players/<str:username>/avatar/", views.avatar, name="avatar"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("store/", views.store, name="store"),
    path("store/<int:pk>/buy/", views.buy, name="buy"),
]
