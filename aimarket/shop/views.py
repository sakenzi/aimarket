from django.shortcuts import render


def home(request):
    products = [
        {"title": "Смартфон X", "price": "129 990 ₸", "tag": "Рассрочка 0-0-12", "rating": "4.8", "reviews": 312},
        {"title": "Наушники Pro", "price": "19 990 ₸", "tag": "Хит продаж", "rating": "4.7", "reviews": 120},
        {"title": "Ноутбук Air", "price": "399 990 ₸", "tag": "Доставка сегодня", "rating": "4.9", "reviews": 88},
        {"title": "Пылесос Robot", "price": "89 990 ₸", "tag": "Скидка -15%", "rating": "4.6", "reviews": 54},
        {"title": "Игровая мышь", "price": "12 490 ₸", "tag": "Топ", "rating": "4.5", "reviews": 203},
        {"title": "Монитор 27”", "price": "109 990 ₸", "tag": "Гарантия", "rating": "4.7", "reviews": 61},
        {"title": "PowerBank 20k", "price": "14 990 ₸", "tag": "Быстрая зарядка", "rating": "4.4", "reviews": 177},
        {"title": "Кофемашина", "price": "159 990 ₸", "tag": "Для дома", "rating": "4.8", "reviews": 39},
    ]
    categories = ["Смартфоны", "Ноутбуки", "ТВ", "Бытовая техника", "Красота", "Детям", "Спорт", "Авто"]
    return render(request, "shop/home.html", {"products": products, "categories": categories})
