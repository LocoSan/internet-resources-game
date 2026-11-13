from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from .models import GameSession, UserProfile


def validate_avatar(upload):
    if upload and hasattr(upload, "image"):
        if upload.size > 1024 * 1024:
            raise ValidationError("Изображение должно быть не больше 1 МБ.")
        extensions = {"PNG": {".png"}, "JPEG": {".jpg", ".jpeg"}, "WEBP": {".webp"}}
        if Path(upload.name).suffix.lower() not in extensions.get(upload.image.format, set()):
            raise ValidationError("Выберите изображение PNG, JPEG или WebP.")
    return upload


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("bio", "date_of_birth", "avatar")
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def clean_avatar(self):
        return validate_avatar(self.cleaned_data.get("avatar"))


class GameForm(forms.ModelForm):
    class Meta:
        model = GameSession
        fields = ("difficulty",)
