from django.shortcuts import render,redirect
from . import models
from django.contrib.auth import login as auth_login,logout
# Create your views here.
def user_login(request):
    print(request.method)
    if request.method =='POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        if not models.User.objects.filter(email=email).exists():
            return render(request,'login.html',{'error':"email does not exists!"})
        user = models.User.objects.get(email=email)

        if not user.check_password(password):
            return render(request,'login.html',{'error':"password must be same!"})
        auth_login(request,user)
        return redirect('home')
    return render(request,'login.html')

def user_logout(request):
    logout(request)
    return redirect('login')

def register(request):
    if request.method=='POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        # phone = request.POST.get('phone')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        is_active = bool(request.POST.get('is_active'))

        if models.User.objects.filter(email=email).exists():
            return render(request,'register.html',{'error':"email allready exists!"})
        
        if not password1 == password2:
            return render(request,'register.html',{'error':"password does not same!"})

        model = models.User.objects.create_user(
            first_name = first_name,
            last_name = last_name,
            username= username,
            email=email,
            # phone= phone,
            password=password1,
            is_active=is_active
        )
        return redirect('home')

    return render(request,'register.html')

def home(request):
    products = models.Product.objects.all().order_by('-id')[:8]

    
    return render(request,'home.html',{'products':products})