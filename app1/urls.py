from django.urls import path
from app1.views import *
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('login/',login,name='login1'),
    path('logout/',logout,name="logout1"),
    path('register/',register,name='register1'),
    path("",index,name='index'),
    path('poduct-all/',productall,name='productall'),
    path('poduct-filter/<int:id>/',productcategorywise,name='productfilter1'),
    path('poduct-get/<int:id>/',singleproduct,name='productget1'),
    path('change-password/',changepass,name='change'),
    path('contact-us/',contact,name='contact'),
    path('profile/',profile,name='profile'),
    path('add-address/', add_address, name='add_address'),
    path('delete-address/<int:address_id>/', delete_address, name='delete_address'),
    path('myorder/',myorder,name='myorder'),
    path('feedback',feedback,name='feedback'),
    path('buy-now/',buynow,name='buy'),
    path('razorpayView/',razorpayView,name='razorpayView'),
    path('paymenthandler/',paymenthandler,name='paymenthandler'),
    path('successview/',successview,name="orderSuccessView"),
    path('about/', about, name='about'),
    path("category/<int:category_id>/", category_products, name="category_products"),
    
    # ════════════════════════════════════════════════════════════════════════════════
    # ✅ CUSTOMER ROUTES - PUBLIC (NO PROTECTION)
    # ════════════════════════════════════════════════════════════════════════════════
    
    path("categories/", category_products, name="categories"),
    
    # ════════════════════════════════════════════════════════════════════════════════
    # 🔐 ADMIN ROUTES - PROTECTED (MUST BE LOGGED IN AS ADMIN/STAFF)
    # ════════════════════════════════════════════════════════════════════════════════
    
    path('admin-login/', admin_login, name='admin_login'),
    path('admin-dashboard/', is_admin_required(admin_dashboard), name='admin_dashboard'),
    
    # ════════════════════════════════════════════════════════════════════════════════
    # CATEGORY MANAGEMENT (ADMIN ONLY) - /dashboard/ prefix
    # ════════════════════════════════════════════════════════════════════════════════
    
    path("dashboard/categories/", is_admin_required(category_list), name="category_list"),
    path('dashboard/categories/add/', is_admin_required(add_category), name='add_category'),
    path('dashboard/categories/edit/<int:id>/', is_admin_required(edit_category), name='edit_category'),
    path('dashboard/categories/delete/<int:id>/', is_admin_required(delete_category), name='delete_category'),
    
    # ════════════════════════════════════════════════════════════════════════════════
    # PRODUCT MANAGEMENT (ADMIN ONLY) - /dashboard/ prefix
    # ════════════════════════════════════════════════════════════════════════════════
    
    path('dashboard/products/add/', is_admin_required(add_product), name='add_product'),
    path("dashboard/products/", is_admin_required(product_list), name="product_list"),
    path('dashboard/products/edit/<int:pk>/', is_admin_required(product_edit), name='product_edit'),
    path('dashboard/products/delete/<int:pk>/', is_admin_required(product_delete), name='product_delete'),
    
    # ════════════════════════════════════════════════════════════════════════════════
    # USER MANAGEMENT (ADMIN ONLY) - /dashboard/ prefix
    # ════════════════════════════════════════════════════════════════════════════════
    
    path("dashboard/users/", is_admin_required(user_list), name="user_list"),
    path("dashboard/users/<int:user_id>/orders/", is_admin_required(user_orders), name="user_orders"),
    
    # ════════════════════════════════════════════════════════════════════════════════
    # ORDER MANAGEMENT (ADMIN ONLY) - /dashboard/ prefix
    # ════════════════════════════════════════════════════════════════════════════════
    
    path("dashboard/orders/", is_admin_required(order_list), name="order_list"),
    path('dashboard/toggle-delivered/<int:order_id>/', is_admin_required(toggle_delivered), name='toggle_delivered'),
    path("dashboard/orders/update/<int:order_id>/", is_admin_required(update_order_status), name="update_order_status"),
    path("dashboard/orders/export/", is_admin_required(export_orders_csv), name="export_orders_csv"),
    path('dashboard/download-invoice/<int:order_id>/', is_admin_required(download_invoice), name='download_invoice'),
    
    # ════════════════════════════════════════════════════════════════════════════════
    # FEEDBACK & REPORTS (ADMIN ONLY) - /dashboard/ prefix
    # ════════════════════════════════════════════════════════════════════════════════
    
    path("dashboard/feedback/", is_admin_required(feedback_list), name="feedback_list"),
    path("dashboard/reports/", is_admin_required(product_report), name="product_report"),
    
    # ════════════════════════════════════════════════════════════════════════════════
    # ADMIN PROFILE (ADMIN ONLY) - /dashboard/ prefix
    # ════════════════════════════════════════════════════════════════════════════════
    
    path('dashboard/profile/', is_admin_required(admin_profile), name='admin_profile'),
    path('dashboard/profile/edit/', is_admin_required(edit_admin_profile), name='edit_admin_profile'),
    
    # ════════════════════════════════════════════════════════════════════════════════
    # CUSTOMER/USER ROUTES (NO PROTECTION)
    # ════════════════════════════════════════════════════════════════════════════════
    
    path("cart/", cart_view, name="cart"),
    path("cart/update/<int:item_id>/", update_cart, name="update_cart"),
    path("cart/remove/<int:item_id>/", remove_from_cart, name="remove_from_cart"),
    path("add-to-cart/<int:product_id>/", add_to_cart, name="add_to_cart"),
    path('checkout/', checkout, name='checkout'),
    path("user_payment/", user_payment, name="user_payment"),
    path("myorder/<int:order_id>/", order_detail, name="order_detail"),
    path('checkout_single/', checkout_single, name='checkout_single'),
    path('cash-on-delivery/', cod_success_view, name='cod_success_view'),
    path("apply-coupon/", apply_coupon, name="apply_coupon"),
    path('add-to-cart-ajax/', add_to_cart_ajax, name='add_to_cart_ajax'),
    path('update-cart-ajax/', update_cart_ajax, name='update_cart_ajax'),
    
    # ════════════════════════════════════════════════════════════════════════════════
    # WATCHLIST ROUTES
    # ════════════════════════════════════════════════════════════════════════════════
    
    path('watchlist/', watchlist_view, name='watchlist'),
    path('watchlist/add-ajax/', add_to_watchlist_ajax, name='add_to_watchlist_ajax'),
    path('watchlist/remove-ajax/', remove_from_watchlist_ajax, name='remove_from_watchlist_ajax'),
    path('watchlist/check/<int:product_id>/', check_watchlist_status, name='check_watchlist_status'),
    path('watchlist/count/', get_watchlist_count, name='get_watchlist_count'),
    
    # ════════════════════════════════════════════════════════════════════════════════
    # CHECKOUT PAGES
    # ════════════════════════════════════════════════════════════════════════════════
    
    path('pay-now/', pay_now, name='pay_now'),
    path("order-sucess/", order_sucess, name="order_sucess"),
]