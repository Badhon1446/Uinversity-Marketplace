from django.shortcuts import render,redirect,get_object_or_404
from . import models
from .form import RatingForm,CheckOutForm
from .models import User
from django.contrib.auth import login as auth_login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q,Min,Max,Avg
from .utils import generate_sslcommerz_payment,send_order_confirmation_email
from django.views.decorators.csrf import csrf_exempt


from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings

# Create your views here.
def user_login(request):
    print(request.method)
    print("SITE_ID:", settings.SITE_ID)
    print("CURRENT SITE:", Site.objects.get_current().domain)
    print("SOCIAL APPS:", SocialApp.objects.all().values("id", "provider", "name"))
    print(
        "GOOGLE APP SITES:",
        SocialApp.objects.filter(provider="google").values(
            "id", "provider", "name"
        )
    )
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

    for_you_products = models.Product.objects.filter(is_offer=True).order_by('-id')[:10]    
    products = models.Product.objects.filter(is_offer=False).order_by('-id')[:15]


    # products = models.Product.objects.all().order_by('-id')[:12]
    categorys = models.Category.objects.all().order_by('-created_at')[:4]
    banners = models.HeroBanner.objects.filter(is_active=True)



    contex = {
        'for_you_products':for_you_products,
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

    orders = models.Order.objects.filter(user=user).prefetch_related('order__product')
    total_items = sum(item.quantity for order in orders for item in order.order.all())

    total_spent = sum(order.get_total_cost() for order in orders if order.paid)

    context = {
        'user': user,
        'profile': profile,
        'orders': orders,
        'total_items': total_items,
        'total_spent': total_spent,
    }

    return render(request, 'user/profile.html', context)


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
                    user = request.user,
                    order=order,
                    product=item.product,
                    quantity=item.quantity
                )

            cart.items.all().delete()
            request.session['order_id'] = order.id
            return redirect('payment_process')

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

@csrf_exempt
@login_required(login_url='login')
def payment_process(request):

    order_id = request.session.get('order_id')
    if not order_id:
        messages.error(request,'Order has no id!')
        return redirect('checkout')
    
    order = get_object_or_404(models.Order, id = order_id)
    payment_data = generate_sslcommerz_payment(order,request)

    if payment_data['status'] == 'SUCCESS':
        return redirect(payment_data['GatewayPageURL'])
    else:
        messages.error(request,'Payment Gateway error.')
        return redirect('payment_process')

@csrf_exempt
def payment_success(request,order_id):
    order = get_object_or_404(models.Order, id = order_id)
    order.paid = True
    order.status = 'processing'
    order.transaction_id = order.id
    order.save()

    order_item = order.order.all()
    for item in order_item:
        product = item.product
        product.stock -= item.quantity

        if product.stock < 0:
            product.stock = 0
        product.save()

    try:
        send_order_confirmation_email(order)
    except Exception as e:
        print(f"Email sending failed for order {order.id}: {e}")

    messages.success(request,"payment successfull!")
    return render(request,'payment_success.html', {'order': order})

@csrf_exempt
def payment_fail(request, order_id):
    order = get_object_or_404(models.Order, id=order_id)
    order.status = 'canceled'
    order.save()
    messages.error(request,"payment fail!")
    return render(request,'payment_fail.html', {'order': order})

@csrf_exempt
def payment_cencle(request, order_id):
    order = get_object_or_404(models.Order, id=order_id)
    order.status = 'canceled'
    order.save()
    messages.error(request,"payment cencle!")
    return render(request,'payment_cencle.html', {'order': order})

@login_required(login_url='login')
def rate_product(request, order_id):

    order = get_object_or_404(models.Order, id=order_id)

    if order.user != request.user or not order.paid:
        messages.warning(request,"You can only rate products from your paid orders.")
        return redirect('product_list')

    ordered_item = models.OrderItem.objects.filter(order=order).first()
    if not ordered_item:
        messages.warning(request, "No product found in this order.")
        return redirect('product_list')

    product = ordered_item.product

    try:
        rating = models.Rating.objects.get(product=product,user=request.user)
    except models.Rating.DoesNotExist:
        rating = None

    if request.method == 'POST':
        form = RatingForm(request.POST, instance=rating)

        if form.is_valid():
            rating = form.save(commit=False)
            rating.product = product
            rating.user = request.user
            rating.save()

            return redirect('home')

    else:
        form = RatingForm(instance=rating)

    return render(request, 'rate_product.html', {
        'form': form,
        'product': product
    })
        