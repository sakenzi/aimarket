from django import forms


class CheckoutForm(forms.Form):
    full_name = forms.CharField(
        max_length=200, label='Полное имя',
        widget=forms.TextInput(attrs={'placeholder': 'Иван Иванов'})
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'placeholder': 'ivan@example.com'})
    )
    phone = forms.CharField(
        max_length=20, label='Телефон',
        widget=forms.TextInput(attrs={'placeholder': '+7 (999) 123-45-67'})
    )
    city = forms.CharField(
        max_length=100, label='Город',
        widget=forms.TextInput(attrs={'placeholder': 'Москва'})
    )
    address = forms.CharField(
        label='Адрес доставки',
        widget=forms.TextInput(attrs={'placeholder': 'ул. Пушкина, д. 1, кв. 1'})
    )
    postal_code = forms.CharField(
        max_length=20, label='Почтовый индекс',
        widget=forms.TextInput(attrs={'placeholder': '123456'})
    )
    comment = forms.CharField(
        required=False, label='Комментарий к заказу',
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Дополнительная информация...'})
    )