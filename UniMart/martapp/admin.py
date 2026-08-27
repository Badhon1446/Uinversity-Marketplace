from django.contrib import admin
from .models import Product,Category,Register,HeroBanner,Profile,Order,Cart,CartItem,OrderItem,Rating
from django.contrib.auth.models import User
# Register your models here.
# admin.site.register(Product)
# admin.site.register(Category)
# admin.site.register(User)
# admin.site.register(HeroBanner)
# admin.site.register(Profile)
# admin.site.register(Order)
# admin.site.register(OrderItem)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name','slug','created_at']
    prepopulated_fields = {'slug':('name',)}

@admin.register(HeroBanner)
class HeroBannerAdmin(admin.ModelAdmin):
    list_display = ['title','subtitle','image']

class RatingInline(admin.TabularInline):
    model = Rating
    extra = 0
    readonly_fields = ['user','rating','comment','created_at']



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name','price','category','condition','is_offer','stock','image','created_at']
    list_filter = ['price','category','condition','is_offer','created_at']
    list_editable = ['price','stock',]

    prepopulated_fields = {'slug':('name',)}
    inlines = [RatingInline]

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id','user','first_name','email','paid','status','transaction_id','created_at']
    list_filter = ['paid','status','created_at']
    search_fields = ['first_name','email']
    inlines = [OrderItemInline]

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user','created_at','updated_at']
    inlines = [CartItemInline]

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['user','product','rating','created_at']
    list_filter = ['rating','product']

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user','phone','image']