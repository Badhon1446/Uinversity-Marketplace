from .models import Rating
from django.forms import ModelForm

class RatingForm(ModelForm):
    class Meta:
        model = Rating
        fields = '__all__'