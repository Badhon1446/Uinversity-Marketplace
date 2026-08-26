from django.urls import path,include
from . import views
from django.views.generic import TemplateView

urlpatterns=[
    path('', views.home, name = 'home'),
    path('login/', views.user_login, name = 'login'),
    path('register/', views.register, name = 'register'),
    path('logout/', views.user_logout, name = 'logout'),

    path('products_list/', views.productList, name = 'product_list'),
    path('product_details/<slug:slug>/', views.product_details, name='product_details'),
    path('services/', TemplateView.as_view(template_name='service.html'),name='services'),
    
    path('cart/', views.cart_details, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),


    path('checkout/', views.checkout, name='checkout'),
    path('payment/process/', views.payment_process, name = 'payment_process'),
    path('payment/success/<int:order_id>/', views.payment_success, name = 'payment_success'),
    path('payment/fail/<int:order_id>', views.payment_fail, name = 'payment_fail'),
    path('payment/cencel/<int:order_id>', views.payment_cencle, name = 'payment_cencel'),

    # path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),    
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),

    path('profile/', views.profile, name='profile'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('rate/<int:product_id>/', views.rate_product, name= 'rate_product')

    
]