from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime
from decimal import Decimal

class Category(models.Model):
    categoryname = models.CharField(max_length=200)
    brand = models.CharField(max_length=100, blank=True, null=True)  # ✅ Moved brand here
    img=models.ImageField(upload_to='category')

    def __str__(self):
        return self.categoryname


class Product(models.Model):
    category=models.ForeignKey(Category,on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    img=models.ImageField(upload_to='product')
    discount = models.IntegerField(default=0)
    price = models.IntegerField()
    description = models.TextField()
    quantity=models.IntegerField()

    brand = models.CharField(max_length=100, blank=True, null=True)
    size = models.JSONField(default=list, blank=True, null=True)
    size_stock = models.JSONField(default=dict, blank=True, null=True)

    color = models.CharField(max_length=50, blank=True, null=True)
    material = models.CharField(max_length=100, blank=True, null=True)

    # ═══════════════════════════════════════════════════════════════════════════════
    # ✅ NEW FIELDS FOR DYNAMIC PRICING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    gold_weight_grams = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Gold weight in grams (e.g., 2.5, 5, 10)"
    )
    
    labor_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500.00,
        help_text="Making/labor charges"
    )
    
    other_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Other costs like diamonds, stones"
    )

    def __str__(self):
        return f"{self.name} ({self.brand})"

    def total_stock(self):
        if isinstance(self.size_stock, dict) and self.size_stock:
            return sum(self.size_stock.values())
        return self.quantity

    def discounted_price(self):
        if self.discount and self.discount < self.price:
            return self.price - self.discount
        return self.price

    # ═══════════════════════════════════════════════════════════════════════════════
    # ✅ NEW METHODS FOR DYNAMIC PRICING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_current_gold_price(self):
        """Get current active gold price per gram"""
        try:
            gold_price_obj = GoldPrice.objects.filter(is_active=True).first()
            if gold_price_obj:
                return gold_price_obj.price_per_gram
        except:
            pass
        return Decimal('5000.00')  # Fallback price
    
    def calculate_base_price(self):
        """Calculate price WITHOUT discount"""
        try:
            gold_cost = Decimal(str(self.gold_weight_grams)) * self.get_current_gold_price()
            total_cost = gold_cost + Decimal(str(self.labor_cost)) + Decimal(str(self.other_cost))
            return round(total_cost, 2)
        except:
            return Decimal(str(self.price))
    
    def calculate_final_price(self):
        """Calculate price WITH discount"""
        try:
            base_price = self.calculate_base_price()
            
            if self.discount:
                discount_amount = (base_price * Decimal(str(self.discount))) / 100
                final_price = base_price - discount_amount
                return round(final_price, 2)
            
            return base_price
        except:
            return Decimal(str(self.discounted_price()))
    
    def get_price_breakdown(self):
        """Return detailed price breakdown dictionary"""
        try:
            gold_cost = Decimal(str(self.gold_weight_grams)) * self.get_current_gold_price()
            base_price = self.calculate_base_price()
            
            return {
                'gold_weight': float(self.gold_weight_grams),
                'gold_price_per_gram': float(self.get_current_gold_price()),
                'gold_cost': float(round(gold_cost, 2)),
                'labor_cost': float(self.labor_cost),
                'other_cost': float(self.other_cost),
                'base_price': float(base_price),
                'discount_percent': float(self.discount) if self.discount else 0,
                'discount_amount': float((base_price * Decimal(str(self.discount)) / 100)) if self.discount else 0,
                'final_price': float(self.calculate_final_price()),
            }
        except:
            return {}


class UserRegister(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    password = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    phone = models.IntegerField()



class Contactus(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.IntegerField()
    message=models.TextField()

class Feedback(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.IntegerField()
    feedback=models.TextField()



class Ordermodel(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Shipped", "Shipped"),
        ("Out for Delivery", "Out for Delivery"),
        ("Delivered", "Delivered"),
        ("Cancelled", "Cancelled"),
    ]
    user = models.ForeignKey(UserRegister, on_delete=models.CASCADE, related_name='orders', null=True,blank=True)
    productid=models.CharField(max_length=200)
    productqty=models.CharField(max_length=200)
    selected_size = models.CharField(max_length=50, blank=True, null=True)
    userId = models.CharField(max_length=200)
    userName = models.CharField(max_length=200)
    userEmail = models.EmailField()
    userContact = models.IntegerField()
    address = models.CharField(max_length=200, null=True,blank = True)
    orderAmount = models.IntegerField()
    paymentMethod = models.CharField(max_length=200)
    transactionId = models.CharField(max_length=200)
    orderDate = models.DateTimeField(auto_created=True,auto_now=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Pending")
    coupon_code = models.CharField(max_length=50, null=True, blank=True)


from django.db import models
from .models import UserRegister, Product  # make sure paths are correct

class Cart(models.Model):
    user = models.ForeignKey(UserRegister, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        return sum(item.subtotal() for item in self.cartitem_set.all())

    def __str__(self):
        return f"Cart of {self.user.email}"


class CartItem(models.Model):
    user = models.ForeignKey(UserRegister, on_delete=models.CASCADE, null =True, blank = True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.product.discounted_price() * self.quantity

    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"



class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    # ✅ FIXED: Changed max_digits to max_length for CharField
    discount_type = models.CharField(
        max_length=10,
        choices=[("percent", "Percentage"), ("amount", "Fixed Amount")],
        default="percent",
    )
    discount_value = models.FloatField()
    min_amount = models.FloatField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

# models.py
class UserAddress(models.Model):
    LABEL_CHOICES = [
        ('Home', 'Home'),
        ('Office', 'Office'),
        ('Other', 'Other'),
    ]
    user = models.ForeignKey(UserRegister, on_delete=models.CASCADE)
    label = models.CharField(max_length=20, choices=LABEL_CHOICES, default='Home')
    street = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.label} - {self.street}, {self.city}, {self.state}"
    
class GoldPrice(models.Model):
    """
    Store daily gold prices from API
    Prices are fetched once per day in the morning
    """
    
    price_per_gram = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Gold price per gram in INR"
    )
    
    price_per_ounce = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Gold price per ounce in USD"
    )
    
    date = models.DateField(
        auto_now=False,
        help_text="Date of the gold price"
    )
    
    time_updated = models.DateTimeField(
        auto_now=False,
        help_text="Time when price was last updated"
    )
    
    source = models.CharField(
        max_length=50,
        default="API",
        choices=[
            ('API', 'From Gold API'),
            ('MANUAL', 'Manual Entry'),
        ],
        help_text="Source of the gold price"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Is this the current price?"
    )
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Gold Prices"
        unique_together = ('date',)  # One price per day
    
    def __str__(self):
        return f"Gold Price - {self.date} - ₹{self.price_per_gram}/gram"
    
    @classmethod
    def get_today_price(cls):
        """Get today's gold price"""
        from datetime import date
        try:
            return cls.objects.filter(
                date=date.today(),
                is_active=True
            ).first()
        except:
            return None
    
    @classmethod
    def get_latest_price(cls):
        """Get latest available gold price"""
        try:
            return cls.objects.filter(is_active=True).first()
        except:
            return None
        
class Watchlist(models.Model):
    """
    User's watchlist - Save favorite products for later
    
    Track what: 
    - Which user (user field)
    - Which product (product field)
    - When added (added_at field) ← TIMESTAMP
    """
    
    user = models.ForeignKey(
        UserRegister,
        on_delete=models.CASCADE,
        related_name='watchlist_items'
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='watchlist_users'
    )
    
    # TIMESTAMP - Saves exact time when added
    added_at = models.DateTimeField(auto_now_add=True)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        # One user can't add same product twice
        unique_together = ('user', 'product')
        ordering = ['-added_at']  # Newest first
        verbose_name_plural = "Watchlist Items"
    
    def __str__(self):
        return f"{self.user.email} - {self.product.name}"
    
    @classmethod
    def get_user_watchlist(cls, user):
        """Get all watchlist items for user"""
        return cls.objects.filter(user=user, is_active=True)
    
    @classmethod
    def get_watchlist_count(cls, user):
        """Get count of items in user's watchlist"""
        return cls.objects.filter(user=user, is_active=True).count()
    
    @classmethod
    def is_in_watchlist(cls, user, product):
        """Check if product is in user's watchlist"""
        return cls.objects.filter(
            user=user, 
            product=product, 
            is_active=True
        ).exists()
# -------------------------------------------------------------------------------
# AUTOMATIC STOCK DEDUCTION SIGNAL
# -------------------------------------------------------------------------------

@receiver(post_save, sender=Ordermodel)
def reduce_stock_on_order(sender, instance, created, **kwargs):
    """
    Automatically reduces Product quantity when a new order is created.
    Handles both single product orders and multiple products (comma-separated).
    """
    if created:
        try:
            # productid and productqty can be single values ("1") 
            # or comma-separated lists ("1,2,3") for cart orders.
            product_ids = str(instance.productid).split(',')
            product_qtys = str(instance.productqty).split(',')

            for i, p_id_str in enumerate(product_ids):
                p_id_str = p_id_str.strip()
                if not p_id_str:
                    continue

                # Parse Quantity
                qty_str = product_qtys[i].strip() if i < len(product_qtys) else "1"
                try:
                    qty = int(qty_str)
                except (ValueError, TypeError):
                    qty = 1

                # Update Product Stock
                try:
                    product = Product.objects.get(id=int(p_id_str))
                    # Reduce stock but don't go below 0
                    product.quantity = max(0, product.quantity - qty)
                    product.save()
                except (Product.DoesNotExist, ValueError):
                    # If product not found, skip it
                    continue
                    
        except Exception as e:
            # Log error (or print for debugging in dev)
            print(f"Error updating stock for Order #$(instance.id): $e")
