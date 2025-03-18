from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.CustomLoginView.as_view(), name='home'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path("set_timezone/", views.set_timezone, name="set_timezone"),

    path('dashboard/', views.dashboard, name="dashboard"),
    path("billing/", views.billing, name="billing"),
    path("sales/invoice/<int:sales_id>/", views.invoice, name="invoice"),
    path("sales/", views.sales_record, name="sales"),
    path("customers/", views.customers, name="customers"),
    path("sales_report/", views.sales_report, name="sales_report"),

    path("faq/", views.faq, name="faq"),
    path("featues/", views.features, name="features"),
    path("about/", views.about, name="about"),

    path('products/', views.products, name="products"),
    path("delete/<int:productId>/", views.delete_item, name="delete_item"),
    path("products/edit/<int:productId>/", views.edit_item, name="edit_item"),
    path("products/custom_barcodes/", views.custom_barcodes, name="custom_barcodes"),

    
]
