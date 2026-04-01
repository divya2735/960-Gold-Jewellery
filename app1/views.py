from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from app1.models import *

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from app1.models import Watchlist
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login as auth_login
import requests
from django.shortcuts import render
from datetime import date, datetime
from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.utils.dateparse import parse_date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import csv
import json

# ═══════════════════════════════════════════════════════════════════════════════
# 🔐 ADMIN PROTECTION DECORATOR
# ═══════════════════════════════════════════════════════════════════════════════

def is_admin_required(view_func):
    """
    Decorator to protect admin views
    Only allows:
    1. Logged-in Django admin/staff users (is_staff=True)
    2. Superusers (is_superuser=True)
    
    Redirects regular users to home page
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "❌ You don't have permission to access admin panel!")
        return redirect('index')
    
    return wrapper

# ═══════════════════════════════════════════════════════════════════════════════
# RAZORPAY CLIENT SETUP
# ═══════════════════════════════════════════════════════════════════════════════

# Using keys from settings.py
razorpay_client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )
client = razorpay_client

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_logged_in_user(request):
    """Get logged-in user from session"""
    email = request.session.get("email")
    if not email:
        return None
    try:
        return UserRegister.objects.get(email=email)
    except UserRegister.DoesNotExist:
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

def login(request):
    if request.method == "POST":
        email1 = request.POST['email']
        password1 = request.POST['password']
        try:
            data = UserRegister.objects.get(email=email1, password=password1)
            request.session['email'] = data.email
            return redirect('index')
        except UserRegister.DoesNotExist:
            return render(request, 'login.html', {'message': 'Invalid email or password'})
    return render(request, 'login.html')


def logout(request):
    request.session.flush()
    return redirect('index')


def register(request):
    if request.method == "POST":
        name1 = request.POST['name']
        email1 = request.POST['email']
        password1 = request.POST['password']
        phone1 = request.POST['phone']
        address1 = request.POST['address']
        
        data = UserRegister(name=name1, email=email1, password=password1, phone=phone1, address=address1)
        a = UserRegister.objects.filter(email=email1)
        if len(a) == 0:
            data.save()
            return redirect('login1')
        else:
            return render(request, 'register.html', {'message': "user already exist"})
    return render(request, 'register.html')

# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

def index(request):
    data = Category.objects.all()
    if 'email' in request.session:
        a = request.session['email']
        return render(request, 'base.html', {'data': data, 'a': a})
    else:
        return render(request, 'base.html', {'data': data})


def productall(request):
    """List all products with filters and watchlist"""
    products = Product.objects.all()
    categories = Category.objects.all()

    # Filters
    category_id = request.GET.get('category')
    brand = request.GET.get('brand')
    color = request.GET.get('color')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if category_id and category_id.isdigit():
        products = products.filter(category_id=category_id)
    if brand:
        products = products.filter(brand__icontains=brand)
    if color:
        products = products.filter(color__icontains=color)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Prepare product data
    product_list = []
    for p in products:
        product_list.append({
            'id': p.id,
            'name': p.name,
            'img': p.img,
            'category': p.category.categoryname,
            'brand': p.brand,
            'price': p.price,
            'discount': p.discount,
            'discounted_price': p.discounted_price(),
            'description': p.description,
        })

    # Get cart info
    cart_dict = {}
    user = get_logged_in_user(request)
    if user:
        cart, created = Cart.objects.get_or_create(user=user)
        cart_items = CartItem.objects.filter(cart=cart)
        for item in cart_items:
            cart_dict[item.product.id] = {
                'item_id': item.id,
                'quantity': item.quantity
            }

    # Get watchlist info
    watchlist_products = []
    if user:
        watchlist_products = Watchlist.objects.filter(
            user=user,
            is_active=True
        ).values_list('product_id', flat=True)

    context = {
        'data': product_list,
        'categories': categories,
        'cart_dict': cart_dict,
        'watchlist_products': list(watchlist_products),
        'watchlist_count': Watchlist.get_watchlist_count(user) if user else 0,
    }

    return render(request, 'productall.html', context)



def productcategorywise(request, id):
    """List products by category with filters (compat with old URL)"""
    category = get_object_or_404(Category, id=id)
    products = Product.objects.filter(category=category)

    # Filtering logic
    brand = request.GET.get('brand')
    color = request.GET.get('color')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if brand:
        products = products.filter(brand__iexact=brand)
    if color:
        products = products.filter(color__iexact=color)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Get filter options
    brands = Product.objects.filter(category=category).values_list('brand', flat=True).distinct()
    colors = Product.objects.filter(category=category).values_list('color', flat=True).distinct()

    # Get cart info
    cart_dict = {}
    user = get_logged_in_user(request)
    if user:
        cart, created = Cart.objects.get_or_create(user=user)
        cart_items = CartItem.objects.filter(cart=cart)
        for item in cart_items:
            # Storing ID and quantity for frontend checks
            cart_dict[item.product.id] = {
                'id': item.id,
                'quantity': item.quantity
            }

    # Get watchlist products for the user
    watchlist_products = []
    if user:
        watchlist_products = Watchlist.objects.filter(
            user=user,
            is_active=True
        ).values_list('product_id', flat=True)

    context = {
        'category': category,
        'products': products,
        'brands': brands,
        'colors': colors,
        'cart_dict': cart_dict,
        'watchlist_products': list(watchlist_products),
        'watchlist_count': Watchlist.get_watchlist_count(user) if user else 0,
    }
    
    if 'email' in request.session:
        context['a'] = request.session['email']

    return render(request, 'category.html', context)


def singleproduct(request, id):
    """Single product detail with watchlist"""
    product = Product.objects.get(pk=id)
    categories = Category.objects.all()

    is_in_watchlist = False
    user = get_logged_in_user(request)
    if user:
        is_in_watchlist = Watchlist.is_in_watchlist(user, product)

    context = {
        'product': product,
        'categories': categories,
        'is_in_watchlist': is_in_watchlist,
        'watchlist_count': Watchlist.get_watchlist_count(user) if user else 0,
    }

    if 'email' in request.session:
        a = request.session['email']
        context['a'] = a

    return render(request, 'singleproduct.html', context)


def about(request):
    return render(request, 'about.html')


def category_products(request, category_id):
    """Categorized product list with full AJAX context"""
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)

    # Filtering logic
    brand = request.GET.get('brand')
    color = request.GET.get('color')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if brand:
        products = products.filter(brand__iexact=brand)
    if color:
        products = products.filter(color__iexact=color)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    # Filter options
    brands = Product.objects.filter(category=category).values_list('brand', flat=True).distinct()
    colors = Product.objects.filter(category=category).values_list('color', flat=True).distinct()

    # Get cart info
    cart_dict = {}
    user = get_logged_in_user(request)
    if user:
        cart, created = Cart.objects.get_or_create(user=user)
        for item in CartItem.objects.filter(cart=cart):
            cart_dict[item.product.id] = {'id': item.id, 'quantity': item.quantity}

    # Get watchlist products
    watchlist_products = []
    if user:
        watchlist_products = Watchlist.objects.filter(user=user, is_active=True).values_list('product_id', flat=True)

    context = {
        'category': category,
        'products': products,
        'brands': brands,
        'colors': colors,
        'cart_dict': cart_dict,
        'watchlist_products': list(watchlist_products),
        'watchlist_count': Watchlist.get_watchlist_count(user) if user else 0,
    }
    
    if 'email' in request.session:
        context['a'] = request.session['email']

    return render(request, 'category.html', context)

# ═══════════════════════════════════════════════════════════════════════════════
# USER PROFILE & ORDERS
# ═══════════════════════════════════════════════════════════════════════════════

def profile(request):
    if 'email' not in request.session:
        return redirect('login1')

    a = request.session['email']
    user_profile = UserRegister.objects.get(email=a)
    user_orders = Ordermodel.objects.filter(userEmail=a).order_by('-orderDate')

    prolist = []
    for order in user_orders:
        product_ids = order.productid.split(',') if order.productid else []
        qty_list = order.productqty.split(',') if order.productqty else []

        for idx, pid in enumerate(product_ids):
            pid = pid.strip()
            if not pid or not pid.isdigit():
                continue

            try:
                productdata = Product.objects.get(id=int(pid))
                prolist.append({
                    'img': productdata.img,
                    'id': productdata.id,
                    'name': productdata.name,
                    'orderDate': order.orderDate,
                    'productqty': qty_list[idx] if idx < len(qty_list) else 1,
                    'transactionId': order.transactionId,
                    'paymentMethod': order.paymentMethod,
                    'orderAmount': order.orderAmount
                })
            except Product.DoesNotExist:
                continue

    context = {
        'profile': user_profile,
        'orders': prolist,
        'addresses': UserAddress.objects.filter(user=user_profile),
        'a': a
    }

    if request.method == 'POST' and 'logout' in request.POST:
        logout(request)
        return redirect('login1')

    return render(request, 'profile.html', context)


def add_address(request):
    if 'email' not in request.session:
        return redirect('login1')
        
    if request.method == 'POST':
        user = UserRegister.objects.get(email=request.session['email'])
        street = request.POST.get('street', '').strip()
        if street: # Only create if there is some data
            UserAddress.objects.create(
                user=user,
                label=request.POST.get('label', 'Home'),
                street=street,
                city=request.POST.get('city', ''),
                state=request.POST.get('state', ''),
                country=request.POST.get('country', ''),
                pincode=request.POST.get('pincode', '')
            )
            messages.success(request, 'Address added successfully!')
        else:
            messages.error(request, 'Street address is required.')
            
    return redirect('profile')

def delete_address(request, address_id):
    if 'email' not in request.session:
        return redirect('login1')
        
    if request.method == 'POST':
        try:
            user = UserRegister.objects.get(email=request.session['email'])
            address = UserAddress.objects.get(id=address_id, user=user)
            address.delete()
            messages.success(request, 'Address deleted successfully!')
        except UserAddress.DoesNotExist:
            messages.error(request, 'Address not found.')
            
    return redirect('profile')


def myorder(request):
    if 'email' not in request.session:
        return redirect('login1')

    a = request.session['email']
    user_orders = Ordermodel.objects.filter(userEmail=a).order_by('-orderDate')

    return render(request, 'myorder.html', {
        'a': a,
        'orders': user_orders
    })


def order_detail(request, order_id):
    try:
        order = Ordermodel.objects.get(id=order_id)
        product_ids = [pid.strip() for pid in order.productid.split(',') if pid.strip().isdigit()]
        qtys = [q.strip() for q in order.productqty.split(',') if q.strip()]

        products = Product.objects.filter(id__in=product_ids)
        products_with_qty = list(zip(products, qtys))
    except Ordermodel.DoesNotExist:
        return redirect('myorder')

    return render(request, 'order_detail.html', {
        'order': order,
        'products_with_qty': products_with_qty,
    })


def changepass(request):
    if 'email' not in request.session:
        return redirect('login1')

    a = request.session['email']
    user = UserRegister.objects.get(email=a)

    if request.method == "POST":
        old = request.POST['oldpass']
        newpass = request.POST['newpass']
        newpass1 = request.POST['newpass1']

        if old == user.password:
            if newpass == newpass1:
                user.password = newpass
                user.save()
                return render(request, 'changepass.html', {'message': "New password updated", 'a': a})
            else:
                return render(request, 'changepass.html', {'message': "New passwords don't match", 'a': a})
        else:
            return render(request, 'changepass.html', {'message': "Old password doesn't match", 'a': a})

    return render(request, 'changepass.html', {'a': a})

# ═══════════════════════════════════════════════════════════════════════════════
# CONTACT & FEEDBACK
# ═══════════════════════════════════════════════════════════════════════════════

def contact(request):
    if request.method == "POST":
        contact_us = Contactus()
        contact_us.name = request.POST['name']
        contact_us.email = request.POST['email']
        contact_us.phone = request.POST['phone']
        contact_us.message = request.POST['message']
        contact_us.save()
        
        if 'email' in request.session:
            a = request.session['email']
            return render(request, 'contactus.html', {'message': "Message Sent Successfully", 'a': a})
        else:
            return render(request, 'contactus.html', {'message': "Message Sent Successfully"})
    
    if 'email' in request.session:
        a = request.session['email']
        data = UserRegister.objects.get(email=a)
        return render(request, 'contactus.html', {'data': data, 'a': a})
    else:
        return render(request, 'contactus.html')


def feedback(request):
    if request.method == "POST":
        fb = Feedback()
        fb.name = request.POST['name']
        fb.email = request.POST['email']
        fb.phone = request.POST['phone']
        fb.feedback = request.POST['feedback']
        fb.save()
        
        if 'email' in request.session:
            a = request.session['email']
            return render(request, 'feedback.html', {'message': "Feedback submitted successfully", 'a': a})
        else:
            return render(request, 'feedback.html', {'message': "Feedback submitted successfully"})
    
    if 'email' in request.session:
        a = request.session['email']
        data = UserRegister.objects.get(email=a)
        return render(request, 'feedback.html', {'data': data, 'a': a})
    else:
        return render(request, 'feedback.html')

# ═══════════════════════════════════════════════════════════════════════════════
# CART MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def add_to_cart_ajax(request):
    if request.method == "POST":
        product_id = int(request.POST.get("product_id"))
        qty = int(request.POST.get("quantity", 1))
        user = get_logged_in_user(request)
        
        if not user:
            return JsonResponse({"status": "error", "msg": "Login required"})

        product = get_object_or_404(Product, id=product_id)
        cart, created = Cart.objects.get_or_create(user=user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

        if not created:
            cart_item.quantity += qty
        else:
            cart_item.quantity = qty
        cart_item.save()

        return JsonResponse({"status": "success", "quantity": cart_item.quantity, "item_id": cart_item.id})
    return JsonResponse({"status": "error", "msg": "Invalid request"})


def update_cart_ajax(request):
    if request.method == "POST":
        item_id = int(request.POST.get("item_id"))
        quantity = int(request.POST.get("quantity"))
        user = get_logged_in_user(request)
        
        if not user:
            return JsonResponse({"status": "error", "msg": "Login required"})

        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=user)
        if quantity <= 0:
            cart_item.delete()
            return JsonResponse({"status": "removed", "item_id": item_id})
        else:
            cart_item.quantity = quantity
            cart_item.save()
            return JsonResponse({"status": "updated", "quantity": cart_item.quantity, "item_id": item_id})
    
    return JsonResponse({"status": "error", "msg": "Invalid request"})


def add_to_cart(request, product_id):
    user = get_logged_in_user(request)
    if not user:
        return redirect("login1")

    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    qty = int(request.POST.get("quantity", 1))
    if not created:
        cart_item.quantity += qty
    else:
        cart_item.quantity = qty
    cart_item.save()

    return redirect("productall")


def update_cart(request, item_id):
    user_email = request.session.get("email")
    if not user_email:
        return redirect("login1")

    user = get_object_or_404(UserRegister, email=user_email)
    cart = get_object_or_404(Cart, user=user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, f"Updated {cart_item.product.name} quantity.")
        else:
            cart_item.delete()
            messages.success(request, f"{cart_item.product.name} removed from cart.")

    return redirect("cart")


def remove_from_cart(request, item_id):
    user_email = request.session.get("email")
    if not user_email:
        return redirect("login1")

    user = get_object_or_404(UserRegister, email=user_email)
    cart = get_object_or_404(Cart, user=user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    messages.success(request, f"{cart_item.product.name} removed from cart.")
    cart_item.delete()
    return redirect("cart")


def cart_view(request):
    user = get_logged_in_user(request)
    if not user:
        return redirect("login1")

    cart, created = Cart.objects.get_or_create(user=user)
    items = cart.cartitem_set.all()
    total = cart.total_price()

    return render(request, "cart.html", {"cart": cart, "items": items, "total": total})


def apply_coupon(request):
    code = request.GET.get("code", "").strip()
    amount = float(request.GET.get("amount", 0))

    try:
        coupon = Coupon.objects.get(code__iexact=code, active=True)
    except Coupon.DoesNotExist:
        return JsonResponse({"valid": False, "message": "Invalid coupon code."})

    if amount < coupon.min_amount:
        return JsonResponse({
            "valid": False,
            "message": f"Minimum order amount ₹{coupon.min_amount} required."
        })

    if coupon.discount_type == "percent":
        discount = round(amount * (coupon.discount_value / 100), 2)
    else:
        discount = min(amount, coupon.discount_value)

    new_total = round(amount - discount, 2)

    return JsonResponse({
        "valid": True,
        "discount": discount,
        "new_total": new_total,
    })

# ═══════════════════════════════════════════════════════════════════════════════
# CHECKOUT & PAYMENT
# ═══════════════════════════════════════════════════════════════════════════════

def buynow(request):
    """Buy single product directly from product page"""
    if 'email' not in request.session:
        messages.error(request, "Please log in to continue.")
        return redirect('login1')

    user = UserRegister.objects.get(email=request.session['email'])

    if request.method == "GET":
        product_id = request.GET.get('id')
        quantity = int(request.GET.get('quantity', 1))
        selected_size = request.GET.get('selected_size')

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            messages.error(request, "Product not found.")
            return redirect('index')

        discounted_price = product.discounted_price() if hasattr(product, 'discounted_price') else product.price
        total = discounted_price * quantity

        return render(request, "checkoutsingle.html", {
            "user": user,
            "product": product,
            "quantity": quantity,
            "selected_size": selected_size,
            "total": total
        })

    elif request.method == "POST":
        product_id = request.POST.get('productid')
        quantity = int(request.POST.get('quantity'))
        selected_size = request.POST.get('selected_size')
        address_option = request.POST.get('address_option')
        payment_method = request.POST.get('payment_method')
        final_total = float(request.POST.get('final_total', 0))

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            messages.error(request, "Product not found.")
            return redirect('index')

        # Determine address
        if address_option == "alternate":
            address = request.POST.get('alternate_address')
        else:
            address = user.address

        # Save session data
        request.session['productid'] = product.id
        request.session['quantity'] = quantity
        request.session['selected_size'] = selected_size
        request.session['orderAmount'] = final_total
        request.session['userid'] = user.id
        request.session['username'] = user.name
        request.session['userEmail'] = user.email
        request.session['userContact'] = user.phone
        request.session['address'] = address
        request.session['paymentMethod'] = payment_method

        # Payment
        if payment_method == "Online":
            order = razorpay_client.order.create({
                'amount': int(final_total * 100),
                'currency': 'INR',
                'payment_capture': '1'
            })
            request.session['razorpay_order_id'] = order['id']
            return redirect('razorpayView')
        else:
            # COD
            Ordermodel.objects.create(
                user=user,
                productid=product.id,
                productqty=quantity,
                selected_size=selected_size,
                userId=user.id,
                userName=user.name,
                userEmail=user.email,
                userContact=user.phone,
                address=address,
                orderAmount=final_total,
                paymentMethod="Cash on Delivery",
                transactionId="COD"
            )
            return render(request, "cashondelivery.html")

    return redirect('index')


def checkout(request):
    email = request.session.get("email")
    if not email:
        return redirect("login1")

    user = get_object_or_404(UserRegister, email=email)
    cart = Cart.objects.filter(user=user).first()
    cart_items = CartItem.objects.filter(cart=cart)
    total = sum(item.subtotal() for item in cart_items)
    addresses = UserAddress.objects.filter(user=user)

    if request.method == "GET":
        coupons = Coupon.objects.filter(active=True)
        return render(request, "checkout.html", {
            "addresses": addresses,
            "cart_items": cart_items,
            "total": total,
            "coupons": coupons,
        })

    payment_method = request.POST.get("payment_method")
    address_option = request.POST.get("address_option")
    saved_id = request.POST.get("saved_address_id")
    final_total = request.POST.get("final_total")
    coupon_code = request.POST.get("coupon_code_hidden")

    if address_option == "saved" and saved_id:
        selected_address = get_object_or_404(UserAddress, id=saved_id, user=user)
    elif address_option == "alternate":
        street = request.POST.get("street", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        country = request.POST.get("country", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        new_label = request.POST.get("new_label", "Home")

        if street: # Basic validation to prevent completely empty addresses
            selected_address = UserAddress.objects.create(
                user=user,
                label=new_label,
                street=street,
                city=city,
                state=state,
                country=country,
                pincode=pincode,
            )
        else:
            # Fallback if somehow submitted empty, to avoid crashing
            # This shouldn't happen with proper frontend validation
            if addresses.exists():
                selected_address = addresses.first()
            else:
                return redirect('checkout') # Or show error
    else:
        # Fallback if no option is somehow provided
        if addresses.exists():
             selected_address = addresses.first()
        else:
             return redirect('checkout')

    request.session["checkout_address"] = (
        f"{selected_address.street}, {selected_address.city}, "
        f"{selected_address.state} - {selected_address.pincode}"
    )
    request.session["checkout_total"] = final_total
    request.session["coupon_code"] = coupon_code

    if payment_method == "Online":
        amount_paise = int(float(final_total) * 100)
        # client is already initialized globally using settings
        razorpay_order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": "1"
        })

        request.session["razorpay_order_id"] = razorpay_order["id"]
        request.session["orderAmount"] = float(final_total)

        return redirect("razorpayView")
    else:
        product_ids = ",".join(str(item.product.id) for item in cart_items)
        product_qty = ",".join(str(item.quantity) for item in cart_items)

        Ordermodel.objects.create(
            user=user,
            productid=product_ids,
            productqty=product_qty,
            selected_size="",
            userId=user.id,
            userName=user.name,
            userEmail=user.email,
            userContact=user.phone,
            address=request.session["checkout_address"],
            orderAmount=final_total,
            paymentMethod="Cash On Delivery",
            transactionId="COD",
            coupon_code=coupon_code
        )

        cart_items.delete()
        return render(request, "order_sucess.html")


def checkout_single(request):
    if 'email' not in request.session:
        return redirect('login1')

    user = UserRegister.objects.get(email=request.session['email'])
    addresses = UserAddress.objects.filter(user=user)

    if request.method == "GET":
        product = get_object_or_404(Product, id=request.GET.get("id"))
        quantity = int(request.GET.get("quantity", 1))
        selected_size = request.GET.get("selected_size")

        price = product.discounted_price()
        total = price * quantity

        return render(request, "checkoutsingle.html", {
            "product": product,
            "quantity": quantity,
            "selected_size": selected_size,
            "total": total,
            "addresses": addresses,
            "coupons": Coupon.objects.filter(active=True)
        })

    product = Product.objects.get(id=request.POST['productid'])
    quantity = int(request.POST['quantity'])
    selected_size = request.POST['selected_size']
    payment_method = request.POST['payment_method']
    final_total = float(request.POST['final_total'])
    coupon_code = request.POST.get("coupon_code")

    address_option = request.POST.get("address_option")
    if address_option == "saved" and request.POST.get("saved_address_id"):
        addr = UserAddress.objects.get(id=request.POST.get("saved_address_id"))
    elif address_option == "alternate":
        street = request.POST.get("street", "").strip()
        if street:
            addr = UserAddress.objects.create(
                user=user,
                label=request.POST.get("new_label", "Home"),
                street=street,
                city=request.POST.get("city", ""),
                state=request.POST.get("state", ""),
                country=request.POST.get("country", ""),
                pincode=request.POST.get("pincode", ""),
            )
        else:
            if addresses.exists():
                addr = addresses.first()
            else:
                return redirect(f"/checkout_single/?id={product.id}&quantity={quantity}")
    else:
        if addresses.exists():
             addr = addresses.first()
        else:
             return redirect(f"/checkout_single/?id={product.id}&quantity={quantity}")


    full_address = f"{addr.street}, {addr.city}, {addr.state}, {addr.country}-{addr.pincode}"

    request.session.update({
        "productid": product.id,
        "quantity": quantity,
        "selected_size": selected_size,
        "orderAmount": final_total,
        "userid": user.id,
        "username": user.name,
        "userEmail": user.email,
        "userContact": user.phone,
        "address": full_address,
        "paymentMethod": payment_method,
        "coupon_code": coupon_code,
    })

    if payment_method == "Online":
        try:
            amount_in_paise = int(final_total * 100)
            order = client.order.create({
                "amount": amount_in_paise,
                "currency": "INR",
                "payment_capture": 1
            })

            request.session["razorpay_order_id"] = order["id"]
            request.session["orderAmount"] = final_total

            return redirect("razorpayView")
        except Exception as e:
            payment_method = "Cash on Delivery"
            request.session["paymentMethod"] = payment_method

    Ordermodel.objects.create(
        user=user,
        productid=product.id,
        productqty=quantity,
        selected_size=selected_size,
        userId=user.id,
        userName=user.name,
        userEmail=user.email,
        userContact=user.phone,
        address=full_address,
        orderAmount=final_total,
        paymentMethod="Cash on Delivery",
        transactionId="COD",
        coupon_code=coupon_code
    )
    return redirect("cod_success_view")


def razorpayView(request):
    if 'razorpay_order_id' not in request.session:
        return redirect('index')

    context = {
        "razorpay_order_id": request.session['razorpay_order_id'],
        "razorpay_merchant_key": settings.RAZORPAY_KEY_ID,
        "razorpay_amount": int(request.session['orderAmount'] * 100),
        "currency": "INR",
        "callback_url": request.build_absolute_uri("/paymenthandler/"),
        "prefill_name": request.session.get('username', ''),
        "prefill_email": request.session.get('userEmail', ''),
        "prefill_contact": request.session.get('userContact', '')
    }
    return render(request, "razorpayDemo.html", context)


@csrf_exempt
def paymenthandler(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            client.utility.verify_payment_signature({
                'razorpay_order_id': data['razorpay_order_id'],
                'razorpay_payment_id': data['razorpay_payment_id'],
                'razorpay_signature': data['razorpay_signature']
            })

            user = UserRegister.objects.get(id=request.session['userid'])
            product = Product.objects.get(id=request.session['productid'])

            Ordermodel.objects.create(
                user=user,
                productid=product.id,
                productqty=request.session['quantity'],
                selected_size=request.session.get('selected_size'),
                userId=user.id,
                userName=user.name,
                userEmail=user.email,
                userContact=user.phone,
                address=request.session['address'],
                orderAmount=request.session['orderAmount'],
                paymentMethod="Online",
                transactionId=data['razorpay_payment_id'],
                coupon_code=request.session.get('coupon_code')
            )

            request.session.flush()
            return JsonResponse({"status": "success"})

        except Exception as e:
            return JsonResponse({"status": "fail", "message": str(e)})


@csrf_exempt
def user_payment(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request")

    try:
        user_email = request.session.get("email")
        user = get_object_or_404(UserRegister, email=user_email)

        cart = Cart.objects.filter(user=user).first()
        cart_items = CartItem.objects.filter(cart=cart)

        payment_id = request.POST.get("razorpay_payment_id")
        razorpay_order_id = request.POST.get("razorpay_order_id")
        signature = request.POST.get("razorpay_signature")

        params = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }

        client.utility.verify_payment_signature(params)

        product_ids = ",".join(str(item.product.id) for item in cart_items)
        product_qty = ",".join(str(item.quantity) for item in cart_items)

        Ordermodel.objects.create(
            user=user,
            productid=product_ids,
            productqty=product_qty,
            selected_size="",
            userId=user.id,
            userName=user.name,
            userEmail=user.email,
            userContact=user.phone,
            address=request.session.get("checkout_address"),
            orderAmount=request.session.get("checkout_total"),
            paymentMethod="Online Payment",
            transactionId=payment_id,
            coupon_code=request.session.get("coupon_code")
        )

        cart_items.delete()

        for k in ["checkout_address", "checkout_total", "coupon_code", "razorpay_order_id"]:
            request.session.pop(k, None)

        return render(request, "payment_success.html")

    except Exception as e:
        print("Payment error:", e)
        return HttpResponseBadRequest("Payment Failed")


def successview(request):
    """Order success view - show latest order details"""
    if 'email' not in request.session:
        return redirect('login1')
    
    a = request.session['email']
    try:
        # Get the latest order for this user
        order = Ordermodel.objects.filter(userEmail=a).order_by('-orderDate').first()
        if order:
            # Get product(s) info
            try:
                product = Product.objects.get(id=order.productid)
                return render(request, 'cashondelivery.html', {
                    'a': a,
                    'order': order,
                    'products': [product]
                })
            except Product.DoesNotExist:
                return render(request, 'cashondelivery.html', {'a': a, 'order': order})
        else:
            return render(request, 'cashondelivery.html', {'a': a})
    except Exception as e:
        return render(request, 'cashondelivery.html', {'a': a, 'error': str(e)})


def cod_success_view(request):
    return render(request, "cashondelivery.html")


def pay_now(request):
    amount = request.session.get("checkout_total")
    if not amount:
        amount = 100

    final_amount = int(amount) * 100
    client_local = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    order = client_local.order.create({
        "amount": final_amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    context = {
        "amount": amount,
        "order_id": order["id"],
        "key": settings.RAZORPAY_KEY_ID
    }

    return render(request, "pay_now.html", context)


def order_sucess(request):
    return render(request, "order_sucess.html")

# ═══════════════════════════════════════════════════════════════════════════════
# GOLD PRICE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_gold_price_from_api():
    try:
        API_URL = "https://api.metals.live/v1/spot/gold"
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        price_usd_per_ounce = float(data.get('price', {}).get('xau', 0))
        
        if price_usd_per_ounce == 0:
            return {
                'success': False,
                'message': 'Could not fetch gold price',
                'price_per_gram': None,
                'price_per_ounce': None
            }
        
        exchange_rate = 83
        price_inr_per_ounce = price_usd_per_ounce * exchange_rate
        price_per_gram = price_inr_per_ounce / 31.1035
        
        return {
            'success': True,
            'message': 'Gold price fetched successfully',
            'price_per_gram': round(Decimal(str(price_per_gram)), 2),
            'price_per_ounce': Decimal(str(price_usd_per_ounce)),
        }
    
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'message': f'API Error: {str(e)}',
            'price_per_gram': None,
            'price_per_ounce': None
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'price_per_gram': None,
            'price_per_ounce': None
        }


def update_gold_price_daily():
    today = date.today()
    existing_price = GoldPrice.objects.filter(date=today).first()
    
    if existing_price:
        return {
            'success': True,
            'message': f'Price already updated for {today}',
            'price': existing_price
        }
    
    api_result = fetch_gold_price_from_api()
    
    if not api_result['success']:
        return {
            'success': False,
            'message': api_result['message']
        }
    
    GoldPrice.objects.filter(is_active=True).update(is_active=False)
    
    try:
        gold_price = GoldPrice.objects.create(
            price_per_gram=api_result['price_per_gram'],
            price_per_ounce=api_result['price_per_ounce'],
            date=today,
            time_updated=datetime.now(),
            source='API',
            is_active=True
        )
        
        return {
            'success': True,
            'message': f'Gold price updated: ₹{gold_price.price_per_gram}/gram',
            'price': gold_price
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error saving price: {str(e)}'
        }


def get_current_gold_price():
    gold_price = GoldPrice.get_today_price()
    
    if not gold_price:
        gold_price = GoldPrice.get_latest_price()
    
    return gold_price


def gold_price_context(request):
    gold_price = get_current_gold_price()
    
    return {
        'gold_price': gold_price,
        'gold_price_per_gram': gold_price.price_per_gram if gold_price else None,
        'gold_price_per_ounce': gold_price.price_per_ounce if gold_price else None,
        'gold_price_date': gold_price.date if gold_price else None,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# WATCHLIST VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

def watchlist_view(request):
    if 'email' not in request.session:
        return redirect('login1')
    
    user = get_logged_in_user(request)
    if not user:
        return redirect('login1')
    
    watchlist_items = Watchlist.get_user_watchlist(user)
    categories = Category.objects.all()
    
    products = []
    for item in watchlist_items:
        products.append({
            'watchlist_id': item.id,
            'product': item.product,
            'added_at': item.added_at,
            'discounted_price': item.product.discounted_price(),
        })
    
    context = {
        'watchlist_items': products,
        'watchlist_count': len(products),
        'categories': categories,
        'email': user.email,
    }
    
    return render(request, 'watchlist.html', context)


@require_POST
def add_to_watchlist_ajax(request):
    if 'email' not in request.session:
        return JsonResponse({
            'status': 'login_required',
            'message': 'Please login to add to watchlist'
        })
    
    user = get_logged_in_user(request)
    if not user:
        return JsonResponse({'status': 'login_required'})
    
    try:
        product_id = request.POST.get('product_id')
        product = Product.objects.get(id=product_id)
        
        already_exists = Watchlist.is_in_watchlist(user, product)
        
        if already_exists:
            return JsonResponse({
                'status': 'already_added',
                'message': f'{product.name} is already in watchlist',
                'watchlist_count': Watchlist.get_watchlist_count(user),
                'is_in_watchlist': True,
            })
        
        watchlist_item = Watchlist.objects.create(
            user=user,
            product=product,
            is_active=True
        )
        
        return JsonResponse({
            'status': 'added',
            'message': f'✓ {product.name} added to watchlist',
            'watchlist_count': Watchlist.get_watchlist_count(user),
            'is_in_watchlist': True,
            'watchlist_id': watchlist_item.id,
            'added_at': watchlist_item.added_at.strftime("%d %b %Y, %H:%M")
        })
    
    except Product.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Product not found'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@require_POST
def remove_from_watchlist_ajax(request):
    if 'email' not in request.session:
        return JsonResponse({'status': 'login_required'})
    
    user = get_logged_in_user(request)
    if not user:
        return JsonResponse({'status': 'login_required'})
    
    try:
        product_id = request.POST.get('product_id')
        product = Product.objects.get(id=product_id)
        
        watchlist_item = Watchlist.objects.filter(
            user=user,
            product=product,
            is_active=True
        ).first()
        
        if watchlist_item:
            watchlist_item.is_active = False
            watchlist_item.save()
            
            return JsonResponse({
                'status': 'removed',
                'message': f'✓ {product.name} removed from watchlist',
                'watchlist_count': Watchlist.get_watchlist_count(user),
                'is_in_watchlist': False,
            })
        else:
            return JsonResponse({
                'status': 'not_found',
                'message': 'Product not in watchlist',
                'watchlist_count': Watchlist.get_watchlist_count(user),
            })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


def check_watchlist_status(request, product_id):
    if 'email' not in request.session:
        return JsonResponse({
            'is_in_watchlist': False,
            'watchlist_count': 0
        })
    
    user = get_logged_in_user(request)
    if not user:
        return JsonResponse({
            'is_in_watchlist': False,
            'watchlist_count': 0
        })
    
    try:
        product = Product.objects.get(id=product_id)
        is_in_watchlist = Watchlist.is_in_watchlist(user, product)
        
        return JsonResponse({
            'status': 'success',
            'is_in_watchlist': is_in_watchlist,
            'watchlist_count': Watchlist.get_watchlist_count(user)
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


def get_watchlist_count(request):
    if 'email' not in request.session:
        return JsonResponse({'watchlist_count': 0})
    
    user = get_logged_in_user(request)
    if not user:
        return JsonResponse({'watchlist_count': 0})
    
    watchlist_count = Watchlist.get_watchlist_count(user)
    
    return JsonResponse({'watchlist_count': watchlist_count})


def context_processor_watchlist(request):
    watchlist_count = 0
    
    if 'email' in request.session:
        user = get_logged_in_user(request)
        if user:
            watchlist_count = Watchlist.get_watchlist_count(user)
    
    return {
        'watchlist_count': watchlist_count,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN LOGIN & DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(username=username, password=password)

        if user is not None and user.is_staff:
            auth_login(request, user)
            return redirect("admin_dashboard")
        else:
            messages.error(request, "Invalid admin credentials")
            return redirect("admin_login")

    return render(request, "adminlogin.html")


def admin_dashboard(request):
    query = request.GET.get("q", "")

    products = Product.objects.all()
    categories = Category.objects.all()
    users = UserRegister.objects.all()
    user_count = users.count()
    orders = Ordermodel.objects.all()
    contacts = Contactus.objects.all().order_by('-id')
    feedbacks = Feedback.objects.all().order_by('-id')

    category_labels = [cat.categoryname for cat in categories]
    category_counts = [cat.product_set.count() for cat in categories]

    user_labels = ["Registered Users"]
    user_counts = [user_count]

    total_orders = orders.count()
    delivered_orders = orders.filter(status="Delivered").count()
    pending_orders = orders.filter(status="Pending").count()
    top_products = products.order_by('-quantity')[:5]

    recent_users = users.order_by('-id')[:5]

    context = {
        "products": products,
        "categories": categories,
        "user_count": user_count,
        "orders": orders,
        "contacts": contacts,
        "feedbacks": feedbacks,
        "query": query,
        "category_labels": category_labels,
        "category_counts": category_counts,
        "user_labels": user_labels,
        "user_counts": user_counts,
        "total_orders": total_orders,
        "delivered_orders": delivered_orders,
        "pending_orders": pending_orders,
        "top_products": top_products,
        "recent_users": recent_users,
    }
    return render(request, "admindashboard.html", context)

# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN PROTECTED VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def admin_profile(request):
    admin_user = request.user
    return render(request, 'aprofile.html', {'admin_user': admin_user})


@login_required
def edit_admin_profile(request):
    from django.contrib.auth.models import User
    from django import forms

    class AdminProfileForm(forms.ModelForm):
        class Meta:
            model = User
            fields = ['username', 'email', 'first_name', 'last_name']

    admin_user = request.user
    if request.method == 'POST':
        form = AdminProfileForm(request.POST, instance=admin_user)
        if form.is_valid():
            form.save()
            return redirect('admin_profile')
    else:
        form = AdminProfileForm(instance=admin_user)
    return render(request, 'edit_admin_profile.html', {'form': form})


def product_list(request):
    products = Product.objects.all()
    return render(request, 'aproduct.html', {'products': products})


def product_edit(request, pk):
    from .forms import ProductForm
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'product_edit.html', {'form': form, 'product': product})


def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        return redirect('product_list')
    return render(request, 'product_confirm_delete.html', {'product': product})


def add_product(request):
    from .forms import ProductForm
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'add_product.html', {'form': form})


def category_list(request):
    categories = Category.objects.all()
    return render(request, "acategory.html", {"categories": categories})


def add_category(request):
    from .forms import CategoryForm
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully.")
            return redirect("category_list")
    else:
        form = CategoryForm()
    return render(request, "category_form.html", {"form": form, "title": "Add Category"})


def edit_category(request, id):
    from .forms import CategoryForm
    category = get_object_or_404(Category, id=id)
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect("category_list")
    else:
        form = CategoryForm(instance=category)
    return render(request, "category_form.html", {"form": form, "title": "Edit Category"})


def delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    category.delete()
    messages.success(request, "Category deleted successfully.")
    return redirect("category_list")


def user_list(request):
    users = UserRegister.objects.all()
    return render(request, "ausers.html", {"users": users})


def order_list(request):
    orders = Ordermodel.objects.all().order_by('-orderDate')

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        try:
            start = parse_date(start_date)
            end = parse_date(end_date)

            if start and end:
                orders = orders.filter(orderDate__date__range=(start, end))
        except Exception as e:
            print("Date filter error:", e)

    return render(request, 'order_list.html', {'orders': orders})


def feedback_list(request):
    feedbacks = Feedback.objects.all()
    return render(request, "feedback_list.html", {"feedbacks": feedbacks})


def user_orders(request, user_id):
    user = get_object_or_404(UserRegister, id=user_id)
    orders = Ordermodel.objects.filter(userId=str(user.id))

    return render(request, 'userorder.html', {
        'user': user,
        'orders': orders
    })


def toggle_delivered(request, order_id):
    order = get_object_or_404(Ordermodel, id=order_id)
    order.delivered = not order.delivered
    order.save()
    messages.success(request, f"Order {order.id} marked as {'Delivered' if order.delivered else 'Not Delivered'}.")
    return redirect('order_list')


def update_order_status(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Ordermodel, id=order_id)
        new_status = request.POST.get("status")

        valid_transitions = {
            "Pending": ["Shipped", "Cancelled"],
            "Shipped": ["Out for Delivery", "Cancelled"],
            "Out for Delivery": ["Delivered", "Cancelled"],
            "Delivered": [],
            "Cancelled": []
        }

        if new_status not in valid_transitions.get(order.status, []):
            messages.error(request, f"Invalid status change from {order.status} to {new_status}")
            return redirect("order_list")

        old_status = order.status
        order.status = new_status
        order.save()

        subject = f"Order Status Update - Order #{order.id}"
        message = f"""
Hello {order.userName},

Your order status has been updated.

Previous Status: {old_status}
New Status: {new_status}

You can log in to track your order.

Thank you for shopping with us!
- 960 Gold Jewellery Team
"""
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [order.userEmail],
                fail_silently=False,
            )
            messages.success(request, f"Status updated to {new_status} and email sent.")
        except Exception as e:
            messages.warning(request, f"Status updated to {new_status}, but email could not be sent. ({e})")

    return redirect("order_list")


def export_orders_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "User ID", "User Name", "Contact", "Product", "Size",
        "Quantity", "Order Amount", "Payment Method",
        "Transaction ID", "Order Date", "Status"
    ])

    orders = Ordermodel.objects.all()
    for order in orders:
        writer.writerow([
            order.userId,
            order.userName,
            order.userContact,
            order.productid,
            order.selected_size,
            order.productqty,
            order.orderAmount,
            order.paymentMethod,
            order.transactionId,
            order.orderDate.strftime("%Y-%m-%d %H:%M"),
            order.status
        ])

    return response


def download_invoice(request, order_id):
    """Generate professional invoice PDF - 960 Gold Jewellery themed"""
    order = get_object_or_404(Ordermodel, id=order_id)

    try:
        product = Product.objects.get(id=order.productid)
        product_name = product.name
    except Product.DoesNotExist:
        product_name = "[Deleted Product]"

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    
    # Gold background bar at top
    p.setFillColor(colors.HexColor('#d4af37'))
    p.rect(0, height - 80, width, 80, fill=1)
    
    # Company name in white
    p.setFont("Helvetica-Bold", 28)
    p.setFillColor(colors.white)
    p.drawString(50, height - 50, "960 Gold Jewellery")
    
    # Tagline
    p.setFont("Helvetica-Oblique", 11)
    p.setFillColor(colors.HexColor('#f2e6c7'))
    p.drawString(50, height - 70, "Premium Handcrafted Luxury")
    
    # Invoice title on right
    p.setFont("Helvetica-Bold", 18)
    p.setFillColor(colors.HexColor('#d4af37'))
    p.drawString(width - 150, height - 50, "INVOICE")
    
    y_pos = height - 120
    p.setFont("Helvetica", 11)
    p.setFillColor(colors.HexColor('#6d4e00'))
    
    # Left side - Invoice info
    p.drawString(50, y_pos, f"Invoice No:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(130, y_pos, f"{order.id}")
    
    p.setFont("Helvetica", 11)
    p.drawString(50, y_pos - 20, f"Order Date:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(130, y_pos - 20, f"{order.orderDate.strftime('%d-%m-%Y %H:%M')}")
    
    p.setFont("Helvetica", 11)
    p.drawString(50, y_pos - 40, f"Payment Method:")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(130, y_pos - 40, f"{order.paymentMethod}")
    
    # Right side - Status
    p.setFont("Helvetica", 11)
    p.drawString(width - 200, y_pos, f"Status:")
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(colors.HexColor('#28a745'))
    p.drawString(width - 120, y_pos, f"✓ {order.status}")
    
    p.setFillColor(colors.HexColor('#6d4e00'))
    p.setFont("Helvetica", 11)
    p.drawString(width - 200, y_pos - 20, f"Transaction ID:")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(width - 120, y_pos - 20, f"{order.transactionId}")
    
    y_pos -= 80
    
    # Divider line
    p.setStrokeColor(colors.HexColor('#d4af37'))
    p.setLineWidth(2)
    p.line(50, y_pos, width - 50, y_pos)
    
    y_pos -= 30
    
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(colors.HexColor('#d4af37'))
    p.drawString(50, y_pos, "BILL TO:")
    
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.HexColor('#6d4e00'))
    y_pos -= 20
    p.drawString(50, y_pos, f"Customer Name: {order.userName}")
    y_pos -= 15
    p.drawString(50, y_pos, f"Email: {order.userEmail}")
    y_pos -= 15
    p.drawString(50, y_pos, f"Phone: {order.userContact}")
    y_pos -= 15
    p.drawString(50, y_pos, f"Address: {order.address}")
    
    y_pos -= 40
    
    # Table header
    p.setFillColor(colors.HexColor('#f9f4e8'))
    p.rect(50, y_pos - 25, width - 100, 25, fill=1)
    
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(colors.HexColor('#6d4e00'))
    p.drawString(60, y_pos - 18, "Description")
    p.drawString(280, y_pos - 18, "Qty")
    p.drawString(330, y_pos - 18, "Size")
    p.drawString(400, y_pos - 18, "Amount")
    
    y_pos -= 30
    
    # Product details
    p.setFont("Helvetica", 10)
    p.drawString(60, y_pos, f"💍 {product_name}")
    p.drawString(280, y_pos, f"{order.productqty}")
    p.drawString(330, y_pos, f"{order.selected_size if order.selected_size else '-'}")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(400, y_pos, f"₹{order.orderAmount}")
    
    y_pos -= 60
    
    # Divider
    p.setStrokeColor(colors.HexColor('#d4af37'))
    p.setLineWidth(1)
    p.line(50, y_pos, width - 50, y_pos)
    
    y_pos -= 30
    
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.HexColor('#6d4e00'))
    p.drawString(width - 200, y_pos, "Subtotal:")
    p.setFont("Helvetica-Bold", 10)
    p.drawString(width - 80, y_pos, f"₹{order.orderAmount}")
    
    y_pos -= 20
    p.setFont("Helvetica", 10)
    p.drawString(width - 200, y_pos, "Discount:")
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(colors.HexColor('#28a745'))
    p.drawString(width - 80, y_pos, "₹0")
    
    y_pos -= 25
    
    # Total amount box
    p.setFillColor(colors.HexColor('#f9f4e8'))
    p.rect(width - 210, y_pos - 20, 160, 30, fill=1)
    
    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(colors.HexColor('#d4af37'))
    p.drawString(width - 200, y_pos - 5, "TOTAL AMOUNT:")
    p.drawString(width - 80, y_pos - 5, f"₹{order.orderAmount}")
    
    y_pos -= 80
    
    p.setFont("Helvetica-Oblique", 10)
    p.setFillColor(colors.HexColor('#8a6f4d'))
    footer_text = "Thank you for shopping with 960 Gold Jewellery! ✨"
    p.drawString(50, y_pos, footer_text)
    
    y_pos -= 20
    p.setFont("Helvetica", 9)
    p.drawString(50, y_pos, "For inquiries, visit: 960goldjewellery.com")
    y_pos -= 15
    p.drawString(50, y_pos, "Premium Handcrafted Jewelry Made with Love, Purity & Elegance")
    
    y_pos -= 30
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.grey)
    p.drawString(50, y_pos, "• Payment Method: " + order.paymentMethod)
    y_pos -= 12
    if order.paymentMethod == "Cash on Delivery":
        p.drawString(50, y_pos, "• COD - Please arrange payment upon delivery")
    else:
        p.drawString(50, y_pos, f"• Online Payment - Transaction ID: {order.transactionId}")
    
    y_pos -= 12
    p.drawString(50, y_pos, "• Please verify the items upon delivery")
    y_pos -= 12
    p.drawString(50, y_pos, "• 7-day return policy applicable")
    
    # Bottom gold line
    p.setStrokeColor(colors.HexColor('#d4af37'))
    p.setLineWidth(2)
    p.line(0, 30, width, 30)
    
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColor(colors.HexColor('#8a6f4d'))
    p.drawString(width/2 - 100, 15, "© 2025 960 Gold Jewellery - All Rights Reserved")
    
    p.showPage()
    p.save()
    
    return response


def product_report(request):
    report_dict = {}

    user_orders = Ordermodel.objects.all()

    for order in user_orders:
        product_ids = order.productid.split(',') if order.productid else []
        qty_list = order.productqty.split(',') if order.productqty else []

        clean_quantities = []
        for q in qty_list:
            try:
                clean_quantities.append(int(q.strip()))
            except:
                clean_quantities.append(1)

        for idx, pid in enumerate(product_ids):
            pid_clean = pid.strip()

            if not pid_clean.isdigit():
                continue

            pid_int = int(pid_clean)

            qty = clean_quantities[idx] if idx < len(clean_quantities) else 1

            total_products = len([x for x in product_ids if x.strip().isdigit()])
            revenue_per_product = order.orderAmount // total_products if total_products > 0 else 0

            try:
                product_obj = Product.objects.get(id=pid_int)
                product_name = product_obj.name
            except Product.DoesNotExist:
                product_name = f"(ID {pid_int})"

            if pid_int not in report_dict:
                report_dict[pid_int] = {
                    "product_name": product_name,
                    "total_orders": 1,
                    "total_quantity": qty,
                    "total_revenue": revenue_per_product,
                }
            else:
                report_dict[pid_int]["total_orders"] += 1
                report_dict[pid_int]["total_quantity"] += qty
                report_dict[pid_int]["total_revenue"] += revenue_per_product

    report = list(report_dict.values())
    return render(request, "productreport.html", {"report": report})

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

from django.shortcuts import get_object_or_404