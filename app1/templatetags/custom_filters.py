# templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def split(value, key):
    return value.split(key)

# ═══════════════════════════════════════════════════════════════════════════════
# ✅ NEW FILTERS FOR DYNAMIC PRICING
# ═══════════════════════════════════════════════════════════════════════════════

@register.filter
def calc_gold_cost(product):
    """
    Calculate gold cost for a product
    Formula: gold_weight_grams × current_gold_price_per_gram
    """
    try:
        gold_cost = product.gold_weight_grams * product.get_current_gold_price()
        return round(float(gold_cost), 2)
    except:
        return 0


@register.filter
def calc_discount(product):
    """
    Calculate discount amount from base price
    Formula: (base_price × discount_percent) / 100
    """
    try:
        if not product.discount:
            return 0
        
        base_price = product.calculate_base_price()
        discount_amount = (base_price * product.discount) / 100
        return round(float(discount_amount), 2)
    except:
        return 0


@register.filter
def calc_final_price(product):
    """
    Calculate final price with discount
    Formula: base_price - discount_amount
    """
    try:
        return round(float(product.calculate_final_price()), 2)
    except:
        return 0


@register.filter
def calc_base_price(product):
    """
    Calculate base price (gold cost + labor + other costs)
    Formula: (gold_weight × gold_price) + labor_cost + other_cost
    """
    try:
        return round(float(product.calculate_base_price()), 2)
    except:
        return 0

@register.filter
def get_item(dictionary, key):
    """Get value from dictionary using variable key"""
    if dictionary is None:
        return None
    return dictionary.get(key)