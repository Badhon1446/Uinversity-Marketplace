from django.db import models
from django.contrib.auth.models import User
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
    
class Category(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

