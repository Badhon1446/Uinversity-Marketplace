from django.contrib import admin
from .models import Product,Category,Register,HeroBanner,Profile,Order,Cart,CartItem,OrderItem
# Register your models here.
admin.site.register(Product)
admin.site.register(Category)
# admin.site.register(User)
admin.site.register(HeroBanner)
admin.site.register(Profile)
admin.site.register(Order)
admin.site.register(OrderItem)