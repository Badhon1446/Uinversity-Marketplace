from django.shortcuts import render,redirect,get_object_or_404
from . import models
from .form import RatingForm,CheckOutForm
from .models import User
from django.contrib.auth import login as auth_login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q,Min,Max,Avg
# Create your views here.
def user_login(request):
    print(request.method)
    if request.method =='POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        if not User.objects.filter(email=email).exists():
            messages.error(request,"email does not exists!")
            return render(request,'login.html')
        user = User.objects.get(email=email)

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

        if User.objects.filter(email=email).exists():
            messages.error(request,'Email allready exists!')
            return render(request,'register.html')
        
        if not password1 == password2:
            messages.error(request,"password does not same!")
            return render(request,'register.html')

        user = User.objects.create_user(
            first_name = first_name,
            last_name = last_name,
            username= username,
            email=email,
            # phone= phone,
            password=password1,
            is_active=is_active
        )
        profile = models.Profile.objects.create(user=user)
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
#         user = get_object_or_404(User,id = request.user.id)
#         return render(request,'user/profile.html',{'user':request.user})

@login_required(login_url='login')
def profile(request):
    user = request.user
    profile = user.profile

    contex = {
        'user':user,
        'profile':profile
    }

    return render(request, 'user/profile.html',contex)


@login_required(login_url='login')
def edit_profile(request):

    user = request.user
    profile = user.profile
    if request.method =='POST':
        user.first_name = request.POST.get('name')
        user.last_name = request.POST.get('last_name')
        user.username = request.POST.get('username')
        email = request.POST.get('email')
        check_email = User.objects.filter(email=email).exclude(id=request.user.id)
        
        profile.phone = request.POST.get('phone')
        profile.bio = request.POST.get('bio')
        profile.university = request.POST.get('university')
        profile.department = request.POST.get('department')
        profile.gender = request.POST.get('gender')
        image = request.FILES.get('image')

        if image:
            profile.image = image

        if check_email.exists():
            messages.error(request,"email already exists!")
            return redirect("edit_profile")
        else:
            user.email = email        

        profile.save()
        user.save()

    context = {
        'profile':profile,
        'user':user
    }

    return render(request,'user/edit_profile.html',context)


def productList(request):
    
    categoryQ = request.GET.get('category','').strip()
    conditionQ = request.GET.get('condition','').strip()
    searchQ = request.GET.get('search','').strip()

    products = models.Product.objects.all().order_by('-id')
    categorys = models.Category.objects.all().order_by('-id')

    if categoryQ:
        products = products.filter(Q(category__slug=categoryQ) | Q(category__name__iexact=categoryQ))
    if conditionQ:
        products = products.filter(condition = conditionQ)
    if searchQ:
        products = products.filter(
            Q(name__icontains = searchQ)
            |Q(description__icontains = searchQ)
            |Q(condition__icontains = searchQ)
            |Q(slug__icontains = searchQ)
            
        ).distinct()

    min_price = products.aggregate(Min('price'))['price__min']
    max_price = products.aggregate(Max('price'))['price__max']

    if request.GET.get('min_price'):
        products = products.filter(price__gte=request.GET.get('min_price'))
    if request.GET.get('max_price'):
        products = products.filter(price__lte=request.GET.get('max_price'))

    contex = {
        'products':products,
        'categories': categorys,
        'searchQ':searchQ,
        'categoryQ':categoryQ,
        'conditionQ':conditionQ,
        'min_price':min_price,
        'max_price':max_price
    }

    return render(request,'product_list.html',contex)


@login_required(login_url='login')
def product_details(request,slug):

    products = get_object_or_404(models.Product,slug=slug)
    related_products = models.Product.objects.filter(category = products.category).exclude(id = products.id)
    user_rating = None

    if request.user.is_authenticated:
        try:
            user_rating = models.Rating.objects.get(product=products, user = request.user)
        except models.Rating.DoesNotExist:
            user_rating = None

    rating_form = RatingForm(instance=user_rating)    

    # if request.method == 'POST':
    #     rate_product = request.POST.get('rate_product')
       
    #     if rating.is_valid():
    #         rating.save()


    contex = {
        'products':products,
        'related_products':related_products,
        'user_rating':user_rating,
        'rating_form':rating_form
    }


    return render(request,'product_details.html',contex)

@login_required(login_url='login')
def cart_details(request):
    try:
        cart = models.Cart.objects.get(user=request.user)
    except models.Cart.DoesNotExist:
        cart = models.Cart.objects.create(user = request.user)

    subtotal = cart.get_total_price()
    shipping_fee = 60 
    tax_amount = round(subtotal * 0.02, 2)
    total_amount = subtotal + shipping_fee + tax_amount

    context = {
        'cart': cart,
        'shipping_fee': shipping_fee,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
    }

    return render(request,'cart_item.html',context)

@login_required(login_url='login')
def add_to_cart(request,product_id):

    product = get_object_or_404(models.Product, id=product_id)
    try:
        cart = models.Cart.objects.get(user=request.user)
    except models.Cart.DoesNotExist:
        cart = models.Cart.objects.create(user = request.user)

    try:
        cart_item = models.CartItem.objects.get(cart=cart, product=product)
        if cart_item.quantity >= product.stock:
            messages.info(request, f"Only {product.stock} items available!")
            return redirect('cart')

        cart_item.quantity += 1
        cart_item.save()

    except models.CartItem.DoesNotExist:
        if product.stock <= 0:
            messages.error(request, f"{product.name} is out of stock!")
            return redirect('cart')

        cart_item = models.CartItem.objects.create(cart=cart,product=product,quantity=1)
    messages.info(request, f"{product.name} has been added to your cart!")
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required(login_url='login')
def cart_remove(request,product_id):

    cart = get_object_or_404(models.Cart, user = request.user)
    product = get_object_or_404(models.Product, id=product_id)
    cart_item = get_object_or_404(models.CartItem, cart=cart, product=product)
    cart_item.delete()

    messages.success(request,f"{product.name} has been removed from your cart!")
    return redirect('cart')

@login_required(login_url='login')
def cart_update(request,product_id):
    cart = get_object_or_404(models.Cart, user = request.user)
    product = get_object_or_404(models.Product, id=product_id)
    cart_item = get_object_or_404(models.CartItem, cart=cart, product=product)

    quantity = int(request.GET.get('quantity',1))   

    if quantity <=0:
        cart_item.delete()
        messages.success(request,f"{product.name} has been removed from your cart!")
    elif quantity > product.stock:
        messages.error(request, f"Only {product.stock} items available!")

    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request,'Cart was updated!')

    return redirect('cart')

@login_required(login_url='login')
def checkout(request):
    try:
        cart = models.Cart.objects.get(user=request.user)
        if not cart.items.exists():
            messages.warning(request, 'Your cart is empty!')
            return redirect('cart')
    except models.Cart.DoesNotExist:
        messages.warning(request, 'your cart is empty!')
        return redirect('cart')

    subtotal = cart.get_total_price()
    shipping_fee = 60
    tax_amount = round(subtotal * 0.02, 2)
    total_amount = round(subtotal + shipping_fee + tax_amount, 2)

    if request.method == 'POST':
        form = CheckOutForm(request.POST)

        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()

            for item in cart.items.all():
                models.OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity
                )

            cart.items.all().delete()
            request.session['order_id'] = order.id

            return redirect('checkout')

    else:
        initial_data = {}

        if request.user.first_name:
            initial_data['first_name'] = request.user.first_name

        if request.user.last_name:
            initial_data['last_name'] = request.user.last_name

        if request.user.email:
            initial_data['email'] = request.user.email

        form = CheckOutForm(initial=initial_data)

    return render(request, 'checkout.html', {
        'cart': cart,
        'form': form,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'tax_amount': tax_amount,
        'total_amount': total_amount
    })

@login_required(login_url='login')
def buy_now(request, product_id):
    product = get_object_or_404(models.Product, id=product_id)

    cart, created = models.Cart.objects.get_or_create(user=request.user)
    item, created = models.CartItem.objects.get_or_create( cart=cart, product=product)

    if not created:
        item.quantity += 1
        item.save()

    return redirect('checkout')

@login_required(login_url='login')
def payment_process(request):
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('checkout')
    order_id = get_object_or_404(models.Order, id = order_id)
    order_data = []