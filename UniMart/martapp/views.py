from django.shortcuts import render,redirect,get_object_or_404
from . import models
from django.contrib.auth import login as auth_login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
# Create your views here.
def user_login(request):
    print(request.method)
    if request.method =='POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        if not models.User.objects.filter(email=email).exists():
            messages.error(request,"email does not exists!")
            return render(request,'login.html')
        user = models.User.objects.get(email=email)

        if not user.check_password(password):
            messages.error(request,'Password Invalid!')
            return render(request,'login.html')
        auth_login(request,user)
        request.session.set_expiry(86400 * 7)
        messages.success(request,"Login success!")
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
            messages.error(request,'Email allready exists!')
            return render(request,'register.html')
        
        if not password1 == password2:
            messages.error(request,"password does not same!")
            return render(request,'register.html')

        user = models.User.objects.create_user(
            first_name = first_name,
            last_name = last_name,
            username= username,
            email=email,
            # phone= phone,
            password=password1,
            is_active=is_active
        )
        auth_login(request,user)
        messages.success(request,"Registration successful!")
        return redirect('home')

    return render(request,'register.html')

def home(request):


    products = models.Product.objects.all().order_by('-id')[:12]
    categorys = models.Category.objects.all().order_by('-created_at')[:4]
    banners = models.HeroBanner.objects.filter(is_active=True)



    contex = {
        'products':products,
        'categories':categorys,
        'banners':banners,
        
    }
    
    
    return render(request,'home.html',contex)

# def profile(request):
#     # if request.method=='GET':
#         user = get_object_or_404(models.User,id = request.user.id)
#         return render(request,'user/profile.html',{'user':request.user})

@login_required(login_url='login')
def profile(request):
    return render(request, 'user/profile.html')

def productList(request):
    
    categoryQ = request.GET.get('category')
    conditionQ = request.GET.get('condition')
    searchQ = request.GET.get('search')

    products = models.Product.objects.all()
    category = models.Category.objects.all()

    if categoryQ:
        products = products.filter(category__name = categoryQ)
    if conditionQ:
        products = products.filter(condition = conditionQ)
    if searchQ:
        products = products.filter(
            Q(name__icontains = searchQ)
            |Q(description__icontains = searchQ)
            |Q(condition__icontains = searchQ)
            |Q(slug__icontains = searchQ)
            
        ).distinct()

    contex = {
        'products':products,
        'searchQ':searchQ,
        'categoryQ':categoryQ,
        'conditionQ':conditionQ,
    }

    return render(request,'product_list.html',contex)