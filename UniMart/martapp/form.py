from .models import Rating,Order
from django import forms

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[
                    (5, '★★★★★ Excellent'),
                    (4, '★★★★☆ Very Good'),
                    (3, '★★★☆☆ Good'),
                    (2, '★★☆☆☆ Poor'),
                    (1, '★☆☆☆☆ Very Poor'),
                ],
                attrs={
                    'class': 'w-full rounded-xl border border-gray-300 px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none'
                }
            ),
            'comment': forms.Textarea(
                attrs={
                    'class': 'w-full rounded-xl border border-gray-300 px-4 py-3 focus:ring-2 focus:ring-indigo-500 focus:outline-none',
                    'rows': 5,
                    'placeholder': 'Write your experience about this product...'
                }
            ),
        }

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
