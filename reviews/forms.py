from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)],
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Write your review here...',
        }),
    )

    class Meta:
        model = Review
        fields = ['rating', 'comment']
