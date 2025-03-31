from django.db import models
from decimal import Decimal
from django.contrib.auth.models import User

def get_default_user():
    return User.objects.get(username='admin')


class Inventory(models.Model):
    productId = models.AutoField(primary_key=True)
    productName = models.CharField(max_length=255)
    barcode = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    createdBy = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updatedBy = models.CharField(max_length=255, blank=True, null=True)
    updated = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # When saving, we set the current user's username for createdBy and updatedBy fields
        if not self.createdBy:  # Ensure createdBy is set only once, not overwritten
            self.createdBy = str(self.createdBy or 'admin')
        self.updatedBy = str(self.updatedBy or 'admin')
        super().save(*args, **kwargs)
        
    def update_stock(barcode, quantity):
        product = Inventory.objects.get(barcode=barcode)
        product.stock -= quantity
        product.save()

    def __str__(self):
        return f"{self.productId}, Name: {self.productName}, Barcode: {self.barcode}, Price: {self.price}"
    
class Barcodes(models.Model):
    barcodes = models.CharField(max_length=255, unique=True)
    product = models.CharField(max_length=255, null=True, blank=True)
    is_assigned = models.BooleanField()
    barcode_svg = models.TextField(max_length=1000, null=True, blank=True)
    def __str__(self):
        return f"{self.barcodes} - {self.product} - {self.is_assigned}"

class Customer(models.Model):
    PLAN_CHOICES = (
        ('R', 'Regular'),
        ('S', 'Silver'),
        ('G', 'Gold'),
        ('D', 'Diamond')        
    )    
    customerPhone = models.BigIntegerField(primary_key=True)  
    customerName = models.CharField(max_length=100, default="N/A")     
    membershipPlan = models.CharField( 
        max_length = 20, 
        choices = PLAN_CHOICES, 
        default = 'R'
        )
    purchase_count = models.IntegerField(default=0)
    total_purchase_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Customer: {self.customerName} | Phone: {self.customerPhone} | Membership: {self.membershipPlan} | Purchases: {self.purchase_count} | Total Value: {self.total_purchase_value}"

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
    user = models.ForeignKey(User, on_delete=models.SET_DEFAULT, default=User.objects.get(username='admin').id) # Link to user
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vatAmmount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discountAmmount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    netTotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Total for all items
    sale_date = models.DateTimeField(auto_now_add=True)
    paymentMethod = models.CharField(max_length=10, default='Cash')

    def update_totals(self, net_total=None):
        """Updates net total based on the provided value, avoiding redundant calculations."""
        if net_total is not None:
            self.netTotal = net_total  # Use the netTotal computed in the view
        self.save()

    def __str__(self):
        return f"Sale ID: {self.salesId} | Customer: {self.customer.customerPhone} | Total: {self.netTotal} | User: {self.user.username} | Date: {self.sale_date.strftime('%Y-%m-%d %H:%M:%S')}"


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
