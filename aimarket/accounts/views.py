from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("home")

        messages.error(request, "Неверный логин или пароль.")
        return redirect("login")

    return render(request, "accounts/login.html")

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "").strip()
        password2 = request.POST.get("password2", "").strip()

        if not username or not password1:
            messages.error(request, "Заполни логин и пароль.")
            return redirect("register")

        if password1 != password2:
            messages.error(request, "Пароли не совпадают.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Такой логин уже занят.")
            return redirect("register")

        user = User.objects.create_user(username=username, email=email, password=password1)
        login(request, user)
        return redirect("home")

    return render(request, "accounts/register.html")

def logout_view(request):
    logout(request)
    return redirect("home")
