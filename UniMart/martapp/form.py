from .models import Rating,Order
from django import forms

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = '__all__'

class CheckOutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'first_name',
            'last_name',
            'email',            
            'address',
            'city',
            'note',
        ]
