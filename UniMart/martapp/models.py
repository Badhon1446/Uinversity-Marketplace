from django.db import models
from django.contrib.auth.models import User
import os
from django.core.validators import MinValueValidator,MaxValueValidator
# Create your models here.

class Register(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    username = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    # phone = models.IntegerField(max_length=11)
    password = models.CharField(max_length=150)
    is_active = models.BooleanField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    create_by = models.ForeignKey(User,on_delete=models.CASCADE)

    class Meta:
        db_table = 'Register'

    def __str__(self):
        return self.username
def category_image_path(instance,filename):
    return os.path.join('category',instance.slug,filename)
class Category(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to=category_image_path,blank=True,null=True)

    class Meta:
        db_table = 'category'
    def __str__(self):
        return self.name
    
class Product(models.Model):

    CONDITION_CHOICE = [
        ('new','New'),
        ('used','Used'),
    ]

    name = models.CharField(max_length=150)
    description = models.CharField(max_length=300)
    category = models.ForeignKey(Category,on_delete=models.CASCADE)
    condition = models.CharField(max_length=150,choices=CONDITION_CHOICE,default='used')
    price = models.IntegerField()
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='media/image')
    stock = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'Product'

    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='profile')
    image = models.ImageField(upload_to='media/profile_image',blank=True,null=True)
    phone = models.CharField(max_length=11,blank=True,null=True)
    bio = models.TextField(blank=True,null=True)
    university = models.CharField(max_length=150,blank=True)
    department = models.CharField(max_length=150,blank=True)
    gender = models.CharField(max_length=20,choices=[
        ('Male','male'),
        ('Female','female'),
        ('Other','other'),
    ],blank=True)

    def __str__(self):
        return self.user.username

class HeroBanner(models.Model):
    title = models.CharField(max_length=120)
    subtitle = models.CharField(max_length=250, blank=True)
    image = models.ImageField(upload_to="hero_banners/")
    button_text = models.CharField(max_length=50, default="Browse Products")
    button_link = models.CharField(max_length=200, default="#products")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title

class Rating(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='rating')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.SmallIntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together =('product','user')

    def __str__(self):
        return f"{self.user.username} - {self.rating}"



class Cart(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Cart'

    def __str__(self):
        return self.user.username
    def get_total_price(self):
        return sum(item.get_cost() for item in self.items.all())
    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart,on_delete=models.CASCADE,related_name='items')
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='cart_item')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'CartItem'
    def __str__(self):
        return self.cart.user.username
    def get_cost(self):
        return self.product.price*self.quantity

class Order(models.Model):
    STATUS_CHOICE = (
        ('pending','Pending'),
        ('processing','Processing'),
        ('shipped','Shipped'),
        ('deliverd','Deliverd'),
        ('cancled', 'Cancled')
    )
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name='orders')
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250,blank=True)
    email = models.EmailField()
    address = models.TextField()
    city = models.CharField(max_length=250)
    note = models.TextField(blank=True)
    paid = models.BooleanField(default=False)
    status = models.CharField(max_length=15,choices=STATUS_CHOICE)
    transaction_id = models.CharField(max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering =[ '-created_at']

    def __str__(self):
        return f"Order #{self.id}"
    def get_total_cost(self):
        return sum(item.get_cost() for item in self.order.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name='order')
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='items')
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name='order_item')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'OrderItem'
    def __str__(self):
            return self.user.username
    def get_cost(self):
            return self.product.price*self.quantity
