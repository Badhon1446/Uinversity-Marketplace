from django.contrib import admin
from .models import Product,Category,Register
# Register your models here.
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(Register)
# admin.site.register(User)