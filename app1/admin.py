from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import *
import requests
from datetime import date

# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('categoryname', 'brand', 'product_count')
    search_fields = ('categoryname', 'brand')
    list_filter = ('categoryname',)
    
    def product_count(self, obj):
        count = Product.objects.filter(category=obj).count()
        return format_html(
            '<span style="background-color: #d4af37; color: #000; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            count
        )
    product_count.short_description = 'Products'


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCT ADMIN - ✅ WITH DYNAMIC PRICING
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'gold_weight_display',
        'final_price_display',
        'discount',
        'stock_display'
    )
    
    list_filter = ('category', 'brand', 'material', 'color')
    search_fields = ('name', 'brand', 'description')
    readonly_fields = ('final_price_display', 'breakdown_display')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'brand', 'description', 'img')
        }),
        ('Gold & Pricing - DYNAMIC', {
            'fields': (
                'gold_weight_grams',
                'labor_cost',
                'other_cost',
                'discount',
                'price',
                'final_price_display',
                'breakdown_display'
            ),
            'classes': ('wide',),
            'description': '💎 Fill gold_weight_grams, labor_cost, and other_cost. Price calculates automatically!'
        }),
        ('Product Details', {
            'fields': ('quantity', 'size', 'size_stock', 'color', 'material')
        }),
    )
    
    def gold_weight_display(self, obj):
        return format_html(
            '<span style="background-color: #FFD700; color: #000; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}g</span>',
            obj.gold_weight_grams
        )
    gold_weight_display.short_description = 'Gold (grams)'
    
    def final_price_display(self, obj):
        price = obj.calculate_final_price()
        return format_html(
            '<div style="background-color: #fff3cd; padding: 10px; border-radius: 5px;">'
            '<strong>Final Price (with discount):</strong><br>'
            '<span style="color: #d4af37; font-weight: bold; font-size: 18px;">₹{:.2f}</span>'
            '</div>',
            price
        )
    final_price_display.short_description = 'Final Price'
    
    def breakdown_display(self, obj):
        breakdown = obj.get_price_breakdown()
        
        if not breakdown:
            return "Price calculation error"
        
        discount_row = ""
        if breakdown.get('discount_percent', 0) > 0:
            discount_row = '<tr style="border-bottom: 1px solid #ddd; background-color: #fff9e6;"><td style="padding: 8px;"><strong>Discount ({}%):</strong></td><td style="padding: 8px; text-align: right; color: green;">-₹{:.2f}</td></tr>'.format(
                breakdown['discount_percent'],
                breakdown['discount_amount']
            )
        
        return format_html(
            '<div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; border: 2px solid #d4af37;">'
            '<h4 style="color: #d4af37; margin-top: 0;">💎 PRICE BREAKDOWN</h4>'
            '<table style="width: 100%; border-collapse: collapse; margin: 10px 0;">'
            '<tr style="border-bottom: 1px solid #ddd;">'
            '<td style="padding: 8px;"><strong>Gold Weight:</strong></td>'
            '<td style="padding: 8px; text-align: right;"><strong>{} grams</strong></td>'
            '</tr>'
            '<tr style="border-bottom: 1px solid #ddd;">'
            '<td style="padding: 8px;"><strong>Current Gold Price:</strong></td>'
            '<td style="padding: 8px; text-align: right;"><strong>₹{:.2f}/gram</strong></td>'
            '</tr>'
            '<tr style="border-bottom: 1px solid #ddd; background-color: #fff9e6;">'
            '<td style="padding: 8px;"><strong style="color: #d4af37;">Gold Cost:</strong></td>'
            '<td style="padding: 8px; text-align: right;"><strong style="color: #d4af37;">₹{:.2f}</strong></td>'
            '</tr>'
            '<tr style="border-bottom: 1px solid #ddd;">'
            '<td style="padding: 8px;"><strong>Labor Cost:</strong></td>'
            '<td style="padding: 8px; text-align: right;">₹{:.2f}</td>'
            '</tr>'
            '<tr style="border-bottom: 1px solid #ddd;">'
            '<td style="padding: 8px;"><strong>Other Costs:</strong></td>'
            '<td style="padding: 8px; text-align: right;">₹{:.2f}</td>'
            '</tr>'
            '<tr style="border-bottom: 2px solid #333; background-color: #e8f5e9;">'
            '<td style="padding: 8px;"><strong>Base Price:</strong></td>'
            '<td style="padding: 8px; text-align: right;"><strong style="font-size: 16px;">₹{:.2f}</strong></td>'
            '</tr>'
            '{}'
            '<tr style="background-color: #fff3cd; border-top: 2px solid #333;">'
            '<td style="padding: 10px;"><strong style="font-size: 16px;">FINAL PRICE:</strong></td>'
            '<td style="padding: 10px; text-align: right;"><strong style="color: #d4af37; font-size: 18px;">₹{:.2f}</strong></td>'
            '</tr>'
            '</table>'
            '<p style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #666;">'
            '✅ <strong>Price updates automatically when gold price changes daily!</strong>'
            '</p>'
            '</div>',
            breakdown['gold_weight'],
            breakdown['gold_price_per_gram'],
            breakdown['gold_cost'],
            breakdown['labor_cost'],
            breakdown['other_cost'],
            breakdown['base_price'],
            discount_row,
            breakdown['final_price']
        )
    breakdown_display.short_description = '💎 PRICE CALCULATION'
    
    def stock_display(self, obj):
        stock = obj.quantity if hasattr(obj, 'quantity') else 0
        color = 'green' if stock > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} units</span>',
            color,
            stock
        )
    stock_display.short_description = 'Stock'


# ═══════════════════════════════════════════════════════════════════════════════
# USER ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(UserRegister)
class UserRegisterAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'order_count', 'watchlist_count_display')
    list_filter = ('email',)
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('email', 'phone')
    
    fieldsets = (
        ('User Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Contact Details', {
            'fields': ('address',)
        }),
    )
    
    def order_count(self, obj):
        count = Ordermodel.objects.filter(user=obj).count()
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            count
        )
    order_count.short_description = 'Total Orders'
    
    def watchlist_count_display(self, obj):
        count = Watchlist.get_watchlist_count(obj)
        return format_html(
            '<span style="background-color: #d4af37; color: #000; padding: 3px 8px; border-radius: 3px; font-weight: bold;">❤️ {}</span>',
            count
        )
    watchlist_count_display.short_description = 'Watchlist Items'


# ═══════════════════════════════════════════════════════════════════════════════
# CONTACT US ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Contactus)
class ContactusAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'message_preview', 'status_badge')
    list_filter = ('email',)
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('name', 'email', 'phone', 'message')
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Message', {
            'fields': ('message',)
        }),
    )
    
    def message_preview(self, obj):
        preview = obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
        return preview
    message_preview.short_description = 'Message Preview'
    
    def status_badge(self, obj):
        return format_html(
            '<span style="background-color: #ffc107; color: #000; padding: 3px 8px; border-radius: 3px;">📧 New</span>'
        )
    status_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ═══════════════════════════════════════════════════════════════════════════════
# FEEDBACK ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'feedback_preview', 'status_badge')
    list_filter = ('email',)
    search_fields = ('name', 'email', 'feedback')
    readonly_fields = ('name', 'email', 'phone', 'feedback', 'submitted_time')
    
    fieldsets = (
        ('Feedback Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Feedback Message', {
            'fields': ('feedback',)
        }),
        ('System Info', {
            'fields': ('submitted_time',),
            'classes': ('collapse',)
        }),
    )
    
    def feedback_preview(self, obj):
        preview = obj.feedback[:60] + '...' if len(obj.feedback) > 60 else obj.feedback
        return preview
    feedback_preview.short_description = 'Feedback'
    
    def status_badge(self, obj):
        return format_html(
            '<span style="background-color: #17a2b8; color: white; padding: 3px 8px; border-radius: 3px;">⭐ Received</span>'
        )
    status_badge.short_description = 'Status'
    
    def submitted_time(self, obj):
        return timezone.now()
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# ═══════════════════════════════════════════════════════════════════════════════
# WATCHLIST ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'product_name', 'added_on', 'price_display', 'is_active_badge')
    list_filter = ('added_at', 'is_active', 'user')
    search_fields = ('user__email', 'product__name')
    readonly_fields = ('user', 'product', 'added_at')
    
    fieldsets = (
        ('Watchlist Item', {
            'fields': ('user', 'product')
        }),
        ('Metadata', {
            'fields': ('added_at', 'is_active'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return format_html(
            '<strong>{}</strong>',
            obj.user.email
        )
    user_email.short_description = 'User Email'
    
    def product_name(self, obj):
        return format_html(
            '💍 {}',
            obj.product.name
        )
    product_name.short_description = 'Product Name'
    
    def added_on(self, obj):
        return obj.added_at.strftime('%d %b %Y, %H:%M')
    added_on.short_description = 'Added On'
    
    def price_display(self, obj):
        price = obj.product.calculate_final_price()
        return format_html(
            '<span style="color: #d4af37; font-weight: bold;">₹{:.2f}</span>',
            price
        )
    price_display.short_description = 'Price'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 3px;">✗ Removed</span>'
            )
    is_active_badge.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# ORDER ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Ordermodel)
class OrdermodelAdmin(admin.ModelAdmin):
    list_display = ('id', 'userName', 'userEmail', 'orderAmount', 'status_badge', 'orderDate')
    list_filter = ('status', 'paymentMethod', 'orderDate')
    search_fields = ('userName', 'userEmail', 'productid')
    readonly_fields = ('orderDate', 'transactionId')
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'userId', 'userName', 'userEmail', 'userContact', 'address')
        }),
        ('Order Details', {
            'fields': ('productid', 'productqty', 'selected_size', 'orderAmount')
        }),
        ('Payment Information', {
            'fields': ('paymentMethod', 'transactionId', 'coupon_code')
        }),
        ('Order Status', {
            'fields': ('status', 'orderDate')
        }),
    )
    
    def status_badge(self, obj):
        status_colors = {
            'Pending': '#ffc107',
            'Shipped': '#17a2b8',
            'Out for Delivery': '#0dcaf0',
            'Delivered': '#28a745',
            'Cancelled': '#dc3545',
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.status
        )
    status_badge.short_description = 'Status'


# ═══════════════════════════════════════════════════════════════════════════════
# CART ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'item_count', 'total_price_display', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__email',)
    readonly_fields = ('created_at',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    
    def item_count(self, obj):
        count = obj.cartitem_set.count()
        return format_html('<strong>{}</strong>', count)
    item_count.short_description = 'Items'
    
    def total_price_display(self, obj):
        total = obj.total_price()
        return format_html(
            '<span style="color: #d4af37; font-weight: bold;">₹{:.2f}</span>',
            total
        )
    total_price_display.short_description = 'Total Price'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'user_email', 'quantity', 'subtotal_display')
    list_filter = ('product', 'user')
    search_fields = ('product__name', 'user__email')
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = 'Product'
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Anonymous'
    user_email.short_description = 'User'
    
    def subtotal_display(self, obj):
        return format_html(
            '<span style="color: green; font-weight: bold;">₹{:.2f}</span>',
            obj.subtotal()
        )
    subtotal_display.short_description = 'Subtotal'


# ═══════════════════════════════════════════════════════════════════════════════
# COUPON ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_display', 'min_amount', 'active_badge')
    list_filter = ('active', 'discount_type')
    search_fields = ('code', 'name')
    
    fieldsets = (
        ('Coupon Information', {
            'fields': ('code', 'name')
        }),
        ('Discount Details', {
            'fields': ('discount_type', 'discount_value', 'min_amount')
        }),
        ('Status', {
            'fields': ('active',)
        }),
    )
    
    def discount_display(self, obj):
        if obj.discount_type == 'percent':
            return format_html('<strong>{}%</strong>', obj.discount_value)
        else:
            return format_html('<strong>₹{}</strong>', obj.discount_value)
    discount_display.short_description = 'Discount'
    
    def active_badge(self, obj):
        if obj.active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">✗ Inactive</span>'
            )
    active_badge.short_description = 'Status'


# ═══════════════════════════════════════════════════════════════════════════════
# USER ADDRESS ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'label', 'city', 'state', 'country')
    list_filter = ('label', 'country', 'user')
    search_fields = ('user__email', 'city', 'state')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'label')
        }),
        ('Address Details', {
            'fields': ('street', 'city', 'state', 'country', 'pincode')
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'


# ═══════════════════════════════════════════════════════════════════════════════
# GOLD PRICE ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(GoldPrice)
class GoldPriceAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'price_per_gram',
        'price_per_ounce',
        'time_updated',
        'source',
        'is_active_badge',
    )
    
    list_filter = (
        'date',
        'source',
        'is_active',
    )
    
    search_fields = ('source',)
    readonly_fields = ('time_updated', 'source')
    
    fieldsets = (
        ('Price Information', {
            'fields': (
                'price_per_gram',
                'price_per_ounce',
                'date',
                'time_updated',
                'source',
                'is_active',
            )
        }),
    )
    
    actions = ['mark_as_active', 'deactivate_all_others']
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">Active</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">Inactive</span>'
            )
    is_active_badge.short_description = 'Status'
    
    def mark_as_active(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, '❌ Select only one price to activate')
            return
        
        selected = queryset.first()
        GoldPrice.objects.filter(is_active=True).update(is_active=False)
        selected.is_active = True
        selected.save()
        
        self.message_user(request, f'✅ Price marked as active')
    mark_as_active.short_description = 'Mark selected as active'
    
    def deactivate_all_others(self, request, queryset):
        GoldPrice.objects.exclude(pk__in=queryset).update(is_active=False)
        self.message_user(request, '✅ All other prices deactivated')
    deactivate_all_others.short_description = 'Deactivate all other prices'
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser