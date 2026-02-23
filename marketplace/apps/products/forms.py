from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, i) for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={'class': 'rating-input'})
    )

    class Meta:
        model = Review
        fields = ('rating', 'title', 'text', 'pros', 'cons')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Заголовок отзыва'}),
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Ваш отзыв...'}),
            'pros': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Достоинства товара'}),
            'cons': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Недостатки товара'}),
        }


class ProductFilterForm(forms.Form):
    q = forms.CharField(required=False, label='Поиск')
    price_min = forms.DecimalField(required=False, label='Цена от')
    price_max = forms.DecimalField(required=False, label='Цена до')
    rating = forms.ChoiceField(
        required=False,
        choices=[('', 'Любой'), ('4', '4+'), ('3', '3+')],
        label='Рейтинг'
    )
    in_stock = forms.BooleanField(required=False, label='В наличии')