from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import Achievement, Difficulty, GameSession, Leaderboard, Purchase, UserProfile


POINTS_PER_LEVEL = {Difficulty.EASY: 20, Difficulty.MEDIUM: 35, Difficulty.HARD: 50}


def profile_for(user):
    return UserProfile.objects.get_or_create(user=user)[0]


def leaderboard(difficulty="", since=""):
    rows = Leaderboard.objects.select_related("player__user")
    if difficulty in Difficulty.values:
        rows = rows.filter(difficulty=difficulty)
    try:
        date = parse_date(since) if since else None
    except ValueError:
        date = None
    if date:
        rows = rows.filter(date_achieved__date__gte=date)
    return rows


@transaction.atomic
def click_coin(game):
    player = UserProfile.objects.select_for_update().get(pk=game.player_id)
    game = GameSession.objects.select_for_update().get(pk=game.pk)
    if game.is_completed:
        raise ValueError("Эта игра уже завершена.")

    bonus = player.purchases.aggregate(total=Sum("item__click_bonus"))["total"] or 0
    now = timezone.now()
    clicks = game.game_state.get("clicks", 0)
    # Перерыв между заходами в игру не засчитываем как активное время.
    game.time_played += min(10, max(0, int((now - game.updated_at).total_seconds())))
    game.game_state = {"clicks": clicks + 1}
    game.score += 1 + bonus
    game.level = 1 + game.score // POINTS_PER_LEVEL[game.difficulty]
    game.save()
    player.coins += 1 + bonus
    player.save(update_fields=["coins", "updated_at"])
    earned = Achievement.objects.filter(score_required__lte=game.score).exclude(profiles=player)
    player.achievements.add(*earned)
    return game, player.coins


@transaction.atomic
def finish_game(game):
    player = UserProfile.objects.select_for_update().get(pk=game.player_id)
    game = GameSession.objects.select_for_update().get(pk=game.pk)
    if game.is_completed:
        return game
    game.is_completed = True
    game.save(update_fields=["is_completed", "updated_at"])
    if not game.score:
        return game

    record, created = Leaderboard.objects.get_or_create(
        player=player, difficulty=game.difficulty, defaults={"score": game.score},
    )
    if not created and game.score <= record.score:
        return game
    if not created:
        record.score = game.score
        record.date_achieved = timezone.now()
        record.save(update_fields=["score", "date_achieved", "updated_at"])

    changed = []
    for rank, row in enumerate(Leaderboard.objects.filter(difficulty=game.difficulty), start=1):
        if row.rank != rank:
            row.rank = rank
            row.updated_at = timezone.now()
            changed.append(row)
    Leaderboard.objects.bulk_update(changed, ["rank", "updated_at"])
    return game


@transaction.atomic
def buy_item(profile, item):
    profile = UserProfile.objects.select_for_update().get(pk=profile.pk)
    if Purchase.objects.filter(player=profile, item=item).exists():
        raise ValueError("Этот предмет уже куплен.")
    if profile.coins < item.price:
        raise ValueError("Не хватает монет.")
    profile.coins -= item.price
    profile.save(update_fields=["coins", "updated_at"])
    return Purchase.objects.create(player=profile, item=item, paid=item.price)
