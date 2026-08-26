from .models import Cart

def get_total_items(request):
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return {'cart_items_count': cart.get_total_items()}
        except Cart.DoesNotExist:
            return {'cart_items_count': 0}
    return {'cart_items_count':0}