from django.db import models
from decimal import Decimal

# Create your models here.
class Inventory(models.Model):
    productId = models.AutoField(primary_key=True)
    productName = models.CharField(max_length=255)
    barcode = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    def update_stock(barcode, quantity):
        product = Inventory.objects.get(barcode=barcode)
        product.stock -= quantity
        product.save()

    def __str__(self):
        return f"{self.productId}, Name: {self.productName}, Barcode: {self.barcode}, Price: {self.price}"
class Customer(models.Model):
    customerPhone = models.BigIntegerField(primary_key=True)  # Unique customer identifier
    purchase_count = models.IntegerField(default=0)
    total_purchase_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Customer: {self.customerPhone} | Purchases: {self.purchase_count} | Total Value: {self.total_purchase_value}"

    @staticmethod
    def update_customer_data(customer_phone, purchase_value):
        """
        Updates the customer's data (purchase count and total purchase value).
        Creates a new customer entry if it doesn't exist.
        """
        customer, created = Customer.objects.get_or_create(customerPhone=customer_phone, defaults={'total_purchase_value': Decimal('0.00')})
        customer.purchase_count += 1
        if not isinstance(purchase_value, Decimal):
            purchase_value = Decimal(str(purchase_value))  # Convert safely
        customer.total_purchase_value += purchase_value
        customer.save()


class SalesRecord(models.Model):
    salesId = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)  # Link to Customer
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vatAmmount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discountAmmount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    netTotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Total for all items
    sale_date = models.DateTimeField(auto_now_add=True)

    def update_totals(self, net_total=None):
        """Updates net total based on the provided value, avoiding redundant calculations."""
        if net_total is not None:
            self.netTotal = net_total  # Use the netTotal computed in the view
        self.save()

    def __str__(self):
        return f"Sale ID: {self.salesId} | Customer: {self.customer.customerPhone} | Total: {self.netTotal} | Date: {self.sale_date.strftime('%Y-%m-%d %H:%M:%S')}"


class SalesItem(models.Model):
    sale = models.ForeignKey(SalesRecord, on_delete=models.CASCADE, related_name="items")
    barcode = models.CharField(max_length=255)
    productName = models.CharField(max_length=255)    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    @property
    def subtotal(self):
        return self.price * self.quantity  # Item-wise total

    def __str__(self):
        return f"{self.productName} ({self.quantity} pcs) - Sale {self.sale.salesId}"
