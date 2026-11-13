from django.core.management.base import BaseCommand

from game.models import Achievement, Item


class Command(BaseCommand):
    help = "Добавить начальные предметы и достижения."

    def handle(self, *args, **options):
        items = [
            ("Медное кольцо", "Первый помощник игрока.", 5, 1),
            ("Кошелёк", "Хранит больше монет.", 20, 3),
            ("Золотая перчатка", "Самый сильный предмет в магазине.", 60, 8),
        ]
        for name, description, price, click_bonus in items:
            Item.objects.get_or_create(name=name, defaults={
                "description": description, "price": price, "click_bonus": click_bonus,
            })
        for score, name, description in [
            (1, "Первая монета", "Собрать первую монету."),
            (20, "Копилка", "Набрать 20 очков за одну игру."),
            (50, "Богатей", "Набрать 50 очков за одну игру."),
        ]:
            Achievement.objects.get_or_create(score_required=score, defaults={
                "name": name, "description": description,
            })
        self.stdout.write(self.style.SUCCESS("Магазин и достижения готовы."))
