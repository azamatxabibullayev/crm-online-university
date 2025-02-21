from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from app.EmailBackEnd import EmailBackEnd


def home(request):
    return render(request, 'index.html')


def loginPage(request):
    return render(request, 'login.html')


def registerPage(request):
    return render(request, 'register.html')


CustomUser = get_user_model()


def doRegister(request):
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:

        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        user_type = request.POST.get('user_type')

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('register')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already exists!")
            return redirect('register')

        try:
            user = CustomUser.objects.create(
                username=email,
                email=email,
                password=make_password(password),
                user_type=user_type
            )
            messages.success(request, "Account created successfully!")
            return redirect('login')
        except Exception as e:
            messages.error(request, f"Failed to create account: {str(e)}")
            return redirect('register')


def doLogin(request):
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        user = EmailBackEnd.authenticate(request, username=request.POST.get('email'),
                                         password=request.POST.get('password'))
        if user != None:
            login(request, user)
            user_type = user.user_type
            if user_type == '1':
                return redirect('admin_home')

            elif user_type == '2':
                return redirect('staff_home')

            elif user_type == '3':
                return redirect('student_home')
            else:
                messages.error(request, "Invalid Login!")
                return redirect('login')
        else:
            messages.error(request, "Invalid Login Credentials!")
            return redirect('login')


def get_user_details(request):
    if request.user != None:
        return HttpResponse("User: " + request.user.email + " User Type: " + request.user.user_type)
    else:
        return HttpResponse("Please Login First")


def logout_user(request):
    logout(request)
    return HttpResponseRedirect('/')
