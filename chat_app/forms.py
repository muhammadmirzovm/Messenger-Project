from django import forms
from .models import Room

class CreateRoomForm(forms.ModelForm):
    nickname = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Your nickname in this room"
        }),
        label="Your nickname"
    )

    class Meta:
        model = Room
        fields = ["name", "description", "nickname"] 
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Room name"}),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Description (optional)"
            }),
        }


class JoinRoomForm(forms.Form):
    nickname = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter a nickname for this room"
        })
    )

