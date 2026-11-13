from pathlib import Path

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import GameForm, ProfileForm
from .models import Difficulty, GameSession, Item, UserProfile
from .services import buy_item, click_coin, finish_game, leaderboard, profile_for


def home(request):
    return render(request, "game/home.html")


def register(request):
    form = UserCreationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        profile_for(form.save())
        messages.success(request, "Аккаунт создан. Теперь войдите.")
        return redirect("login")
    return render(request, "game/form.html", {"title": "Регистрация", "form": form, "submit": "Зарегистрироваться"})


@login_required
def play(request):
    profile = profile_for(request.user)
    form = GameForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        game = form.save(commit=False)
        game.player = profile
        game.save()
        return redirect("session", pk=game.pk)
    sessions = list(profile.sessions.all()[:20])
    return render(request, "game/play.html", {"form": form, "sessions": sessions, "profile": profile})


def owned_game(user, pk):
    return get_object_or_404(GameSession, pk=pk, player__user=user)


@login_required
def session(request, pk):
    game = owned_game(request.user, pk)
    return render(request, "game/session.html", {"game": game})


@login_required
@require_POST
def click(request, pk):
    game = owned_game(request.user, pk)
    try:
        game, coins = click_coin(game)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse({"score": game.score, "level": game.level, "clicks": game.game_state["clicks"], "coins": coins})


@login_required
@require_POST
def finish(request, pk):
    finish_game(owned_game(request.user, pk))
    messages.success(request, "Игра завершена. Лучший результат попал в рейтинг.")
    return redirect("session", pk=pk)


@login_required
@require_POST
def delete(request, pk):
    owned_game(request.user, pk).delete()
    messages.success(request, "Сохранение удалено.")
    return redirect("play")


def scores(request):
    difficulty = request.GET.get("difficulty", "")
    since = request.GET.get("since", "")
    return render(request, "game/leaderboard.html", {
        "rows": leaderboard(difficulty, since)[:100],
        "difficulty": difficulty, "since": since, "difficulties": Difficulty.choices,
    })


def public_profile(request, username):
    user = get_object_or_404(get_user_model().objects.select_related("profile"), username=username)
    return render(request, "game/profile.html", {"player": user, "profile": getattr(user, "profile", None)})


def avatar(request, username):
    profile = get_object_or_404(UserProfile.objects.select_related("user"), user__username=username)
    kinds = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    kind = kinds.get(Path(profile.avatar.name or "").suffix.lower())
    if not profile.avatar or not kind:
        raise Http404
    try:
        return FileResponse(profile.avatar.open("rb"), content_type=kind)
    except FileNotFoundError as error:
        raise Http404 from error


@login_required
def edit_profile(request):
    profile = profile_for(request.user)
    form = ProfileForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        instance=profile,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Профиль обновлён.")
        return redirect("profile", username=request.user.username)
    return render(request, "game/form.html", {"title": "Мой профиль", "form": form, "submit": "Сохранить"})


@login_required
def store(request):
    profile = profile_for(request.user)
    return render(request, "game/store.html", {
        "profile": profile, "items": Item.objects.all(),
        "owned": set(profile.purchases.values_list("item_id", flat=True)),
    })


@login_required
@require_POST
def buy(request, pk):
    item = get_object_or_404(Item, pk=pk)
    try:
        buy_item(profile_for(request.user), item)
    except ValueError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Куплено: {item.name}.")
    return redirect("store")
