import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import activate

from django.contrib.auth.views import LoginView
from django.contrib.auth.views import LogoutView
from .models import Inventory, SalesRecord, Customer, SalesItem

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Sum
from datetime import date
import uuid
from decimal import Decimal




#Index/Home/Login View
class CustomLoginView(LoginView):
    template_name = 'home.html' 

    def get(self, request, *args, **kwargs):
        # Redirect authenticated users to the dashboard
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)
    
#Dashboard View
@login_required
def dashboard(request):
    username = request.user.username
    return render(request, "dashboard.html", {"username":username})


#products View
@login_required
def products(request):
    products = Inventory.objects.all()
    paginator = Paginator(products, 10)  # Show 10 records per page

    page_number = request.GET.get('page')  # Get the current page number from query params
    page_obj = paginator.get_page(page_number)  # Get the specific page of records

   
    storage = messages.get_messages(request)
    storage.used = True 
    
    #New product_data entry form
    if request.method == 'POST':
        # Handle form submission
        product_name = request.POST.get('name')
        barcode = request.POST.get('barcode')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        

        # Validate and save data
        if product_name and barcode and price and stock:
            try:
                barcode = str(barcode)
                price = float(price)
                stock = int(stock)
                if Inventory.objects.filter(barcode=barcode).exists():
                    messages.error(request, "Product already exists!")
                else:
                    Inventory.objects.create(productName=product_name, barcode=barcode, price=price, stock=stock) #This is the line 
                    messages.success(request, f"Product: {product_name} added successfully!")
            except ValueError:
                messages.error(request, "Invalid price or barcode!")
        else:
            messages.error(request, "Fill every details of the product")
        return redirect('products')

    
    return render(request, "products.html", {'page_obj': page_obj})

@login_required
def delete_item(request, productId):
   
    if request.method == "POST":
        item = get_object_or_404(Inventory, productId=productId)
        item.delete()
        messages.success(request, "Product deleted successfully!")
    return redirect("products")  


@login_required
def edit_item(request, productId):
    products = get_object_or_404(Inventory, productId=productId)
    if request.method == "POST":
        updated_name = request.POST.get('updated_name')
        updated_barcode = request.POST.get('updated_barcode')
        updated_price = request.POST.get('updated_price')
        updated_stock = request.POST.get('updated_stock')
        if updated_name and updated_barcode and updated_price and updated_stock:
            try:
                barcode = str(updated_barcode)
                price = float(updated_price)
                stock = int(updated_stock)

                products.productName = updated_name
                products.barcode = barcode
                products.price = price
                products.stock = stock
                products.save()
                messages.success(request, "Product updated successfully!")                    
            except ValueError:
                messages.error(request, "Invalid price or barcode!")
        else:
            messages.error(request, "All fields are required!")
        return redirect('products')

    return render(request, "product_edit.html", {'products':products})



@login_required
def billing(request):
    products = Inventory.objects.all()
    scanned_items = request.session.get('scanned_items', [])  # Retrieve stored items
    calculated_data = None
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'form1':  # Barcode entry
            barcode = request.POST.get('barcode')
            if barcode:
                try:
                    product = Inventory.objects.get(barcode=barcode)
                    
                    #check if product is in stock
                    if product.stock <= 0:
                        messages.error(request, f"Product {product.productName} is out of stock")
                    else:
                        found = False                  
                        # Check if product is already in the session, update quantity
                        for item in scanned_items:
                            if item['barcode'] == barcode:
                                found = True
                                if item['quantity'] < product.stock:
                                    item['quantity'] += 1  # Increase quantity
                                    
                                else:
                                    messages.error(request, "Can't add this product more. Stock limit reached")
                                break
                        if not found and product.stock > 0:
                            # Add product details to session storage
                            scanned_items.append({
                                'barcode': barcode,
                                'productName': product.productName,
                                'price': float(product.price),
                                'quantity': 1,  # Default to 1
                            })
                        
                        request.session['scanned_items'] = scanned_items  # Save session
                        request.session.modified = True 
                except Inventory.DoesNotExist:
                    messages.error(request, "Product with the given barcode does not exist!")
            else:
                messages.error(request, "Enter a Barcode first")
        elif form_type == "form3":
            removeBarcode = request.POST.get('removeBarcode')   
            try:
                for i in scanned_items:
                    if i["barcode"] == removeBarcode:
                        scanned_items.remove(i)
                        request.session['scanned_items'] = scanned_items               
            except:
                pass

        elif form_type == 'form2':  # Checkout processing
            vatPercent = request.POST.get('vatPercent')
            discountPercent = request.POST.get('discountPercent')
            customerPhone = request.POST.get('customerPhone')
           
            if scanned_items and vatPercent and customerPhone:
                try:
                    vatPercent = Decimal(vatPercent)
                    discountPercent = Decimal(discountPercent)
                    total = sum(Decimal(item['price']) * item['quantity'] for item in scanned_items)
                    vat = (total * vatPercent) / 100
                    discount = (total * discountPercent) / 100
                    netTotal = total + vat - discount

                    # Get or create customer
                    customer, _ = Customer.objects.get_or_create(customerPhone=customerPhone)

                    # Create a single sales record for the transaction
                    sale = SalesRecord.objects.create(
                        customer=customer,
                        vat=vatPercent,
                        vatAmmount=vat,
                        discount=discountPercent,
                        discountAmmount=discount,
                        netTotal=netTotal
                    )
                    sale.update_totals(net_total=netTotal) #finalizing

                    #getting saleId
                    sales_id = sale.salesId
                   
                    # Save each scanned product as a SalesItem
                    for item in scanned_items:
                        SalesItem.objects.create(
                            sale=sale,
                            barcode=item['barcode'],
                            productName=item['productName'],
                            price=Decimal(item['price']),
                            quantity=item['quantity']
                        )

                    # Clear session after successful checkout
                    request.session['scanned_items'] = []

                    #Update stock of products after every sale
                    sales_item_for_sale = SalesItem.objects.filter(sale=sale)
                    
                    for items in sales_item_for_sale:
                        quantity = int(items.quantity)
                        barcode = items.barcode
                        Inventory.update_stock(barcode, quantity)                  
                     
                    
                    # Update customer purchase history
                    customer.update_customer_data(customerPhone, netTotal)

                    
                    

                    
                    messages.success(request, f'Transaction completed successfully! <a class="btn btn-success id="invoiceBtn" btn-sm" target="_blank" href="/sales/invoice/{sales_id}">Invoice#{sales_id}</a>')
                    
                    calculated_data = {'total': total, 'vat': vat, 'netTotal': netTotal}
                    

                except ValueError:
                    messages.error(request, "Invalid VAT percentage!")
            else:
                messages.error(request, "All billing details are required")
        
    return render(request, 'billing.html', {
        "products": products,
        "scanned_items": scanned_items,
        "calculated_data": calculated_data,
    })
@login_required
def invoice(request, sales_id):
    if request.method == "GET":
        total = 0
        invoice_data = get_object_or_404(SalesRecord, salesId=sales_id)
        for item in invoice_data.items.all():
            total += item.subtotal
        print(total)  
    return render(request, 'invoices.html', {"invoice_data": invoice_data, "total":total,})


@login_required
def sales_record(request):
    # Fetch sales records with related sales items (avoiding multiple DB queries)
    sales_records = (
        SalesRecord.objects.prefetch_related("items")
        .order_by("-sale_date")  # Latest sales first
    )

    paginator = Paginator(sales_records,10)

    sales_details_from_date = None
    sales_count_from_date = None
    today = date.today()
   
    total_sales_value = (
        SalesRecord.objects.aggregate(total=Sum("netTotal"))["total"] or 0
    )
    total_sales_count = SalesRecord.objects.count()
    todays_total_sales_value = (SalesRecord.objects.filter(sale_date__date=today).aggregate(total=Sum("netTotal"))["total"]or 0)
    #todays_total_sales_value = "{:.2f}".format(todays_total_sales_value)
    
    todays_sales_count = SalesRecord.objects.filter(sale_date__date=today).count()

    filtered_records = None
    messages_storage = messages.get_messages(request)
    messages_storage.used = True  # Clear previous messages

    if request.method == "GET":
        form_type = request.GET.get('form_type')
        if form_type == "query_by_sales_date_form":
            query_date = request.GET.get("query_date")
            if query_date:
                filtered_records = SalesRecord.objects.filter(sale_date__date=query_date)
                if filtered_records.exists():
                    sales_count_from_date = filtered_records.count()
                    sales_details_from_date = filtered_records
                    total_sales_value_for_query_date = (SalesRecord.objects.filter(sale_date__date=query_date).aggregate(total=Sum("netTotal"))["total"]or 0)
                    paginator = Paginator(filtered_records, 10)
                    messages.success(
                        request, f"Total sales: <b>{sales_count_from_date}</b> and Total value: <b>{(total_sales_value_for_query_date):.2f} TK.</b>"
                    )
                else:
                    messages.error(request, f"No sales records exist for {query_date}.")
                    filtered_records = None

        elif form_type == "query_by_id_form":
            query_id = request.GET.get("query_id")
            if query_id:
                if SalesRecord.objects.filter(salesId=query_id).exists():
                    return redirect(invoice, query_id)
                messages.error(request, f"No record found for ID: {query_id}")
            else:
                messages.error(request, "Enter an ID first")
        else:
            pass

        
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)


    

    context = {
            "page_obj": page_obj,  # Unified sales records with items
            "total_sales_value": round(total_sales_value, 2),
            "total_sales_count": total_sales_count,
            "sales_details_from_date": sales_details_from_date,
            "sales_count_from_date": sales_count_from_date,
            "todays_total_sales_value": "{:.2f}".format(todays_total_sales_value),
            "todays_sales_count": todays_sales_count,
            "today": today,
            "filtered_records": filtered_records,
          
    }
    return render(
        request,
        "sales.html",         
        context,
    )

@login_required
def customers(request):
    customer = Customer.objects.all() # Get all records ordered by date (latest first)
    paginator = Paginator(customer, 10)  # Show 10 records per page

    page_number = request.GET.get('page')  # Get the current page number from query params
    page_obj = paginator.get_page(page_number)  # Get the specific page of records

    return render(request, 'customers.html', {'page_obj': page_obj})


def faq(request):
    return render(request, 'faq.html')

def features(request):
    return render(request, 'features.html')

def about(request):
    return render(request, 'about.html')
#getting timezone

@csrf_exempt
@login_required
def set_timezone(request):
    if request.method == "POST":
        data = json.loads(request.body)
        timezone = data.get("timezone", "UTC")  # Default to UTC
        request.user.timezone = timezone
        request.user.save()
        activate(timezone)  # Apply the new timezone
        return JsonResponse({"status": "success", "timezone": timezone})
    return JsonResponse({"status": "failed"}, status=400)