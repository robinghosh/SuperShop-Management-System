from django.contrib import admin
from .models import Inventory, Barcodes, Customer, SalesRecord, SalesItem
# Register your models here.
admin.site.register(Inventory)
admin.site.register(Customer)
admin.site.register(SalesRecord)
admin.site.register(SalesItem)
admin.site.register(Barcodes)