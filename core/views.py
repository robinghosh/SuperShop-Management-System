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
from datetime import date, datetime, timedelta
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
    logged_in_user = request.user
    
    
    
    if logged_in_user.is_superuser:
        sales_record = SalesRecord.objects.all()
        today = datetime.today()
        last_seven_days = []
        total_last_seven_days = []
        
       
        for day in range(7):
            days = today - timedelta(day)
            last_seven_days.append(days.strftime('%Y-%m-%d'))
            
        for days in range(len(last_seven_days)):            
            filtered_record = sales_record.filter(sale_date__date=last_seven_days[days])
            sales_value_of_day = float(filtered_record.aggregate(total=Sum("netTotal"))["total"] or 0)
            total_last_seven_days.append(sales_value_of_day)
            
        sum_last_seven_days_value = sum(total_last_seven_days)
        
        context = {
            'last_seven_days': last_seven_days,
            'total_last_seven_days': total_last_seven_days,
            'sum_last_seven_days_value': sum_last_seven_days_value,
        }
        return render(request, "dashboard.html", context)
    return render(request, "dashboard.html",)


#products View
@login_required
def products(request):
    logged_in_user = request.user
    products = Inventory.objects.all()
    paginator = Paginator(products, 10)
    # print(products.filter(productName="pran mama wafer biscuit".upper()))
    if request.method == 'GET':
        form_type = request.GET.get('form_type')
        if form_type == "search_product":
            query_name = request.GET.get('query_name').strip()
            query_barcode = request.GET.get('query_barcode')
            if query_name:
                products = Inventory.objects.filter(productName__icontains=query_name)
                paginator = Paginator(products, 10)
            elif query_barcode:
                products = Inventory.objects.filter(barcode=query_barcode)
                paginator = Paginator(products, 10)
            elif query_barcode and query_name:
                products = Inventory.objects.filter(barcode=query_barcode)
                paginator = Paginator(products, 10)
            else:
                messages.error(request, f"Product Name or Barcode is empty!!")
    elif request.method == 'POST':

        form_type = request.POST.get('form_type')
        if form_type == "add_product":        
            product_name = request.POST.get('name')
            barcode = request.POST.get('barcode')
            price = request.POST.get('price')
            stock = request.POST.get('stock')
            form_type = request.POST.get('form_type')    
            # Validate and save data
            if product_name and barcode and price and stock:
                try:
                    barcode = str(barcode)
                    price = float(price)
                    stock = int(stock)
                    if Inventory.objects.filter(barcode=barcode).exists():
                        messages.error(request, "Product already exists!")
                    else:
                        Inventory.objects.create(productName=product_name, barcode=barcode, price=price, stock=stock, createdBy=logged_in_user, updatedBy=logged_in_user) #This is the line 
                        messages.success(request, f"Product: {product_name} added successfully!")
                except ValueError:
                    messages.error(request, "Invalid price or barcode!")
            else:
                messages.error(request, "Fill every details of the product")
            return redirect('products')
             
    # Show 10 records per page
    page_number = request.GET.get('page')  # Get the current page number from query params
    page_obj = paginator.get_page(page_number)  # Get the specific page of records

   
    storage = messages.get_messages(request)
    storage.used = True 
    
    #New product_data entry form


    
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
    logged_in_user = request.user
    
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
                products.updatedBy = logged_in_user
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
    user = request.user #get_logged_in_user
    
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
                messages.error(request, "Can not remove item")

        elif form_type == 'form2':  # Checkout processing
            vatPercent = request.POST.get('vatPercent')
            discountPercent = request.POST.get('discountPercent')
            customerPhone = request.POST.get('customerPhone')
            paymentMethod = request.POST.get('paymentMethod')
            if scanned_items and vatPercent and customerPhone and paymentMethod:
                try:
                    vatPercent = Decimal(vatPercent)
                    discountPercent = Decimal(discountPercent)
                    customerPhone = int(customerPhone)
                    total = sum(Decimal(item['price']) * item['quantity'] for item in scanned_items)
                    vat = (total * vatPercent) / 100
                    discount = (total * discountPercent) / 100
                    netTotal = total + vat - discount

                    # Get or create customer
                    customer, _ = Customer.objects.get_or_create(customerPhone=customerPhone)
                    
                    # Create a single sales record for the transaction
                    sale = SalesRecord.objects.create(
                        customer=customer,
                        user=user,
                        vat=vatPercent,
                        vatAmmount=vat,
                        discount=discountPercent,
                        discountAmmount=discount,
                        netTotal=netTotal,
                        paymentMethod=paymentMethod,
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

                    
                    
                    calculated_data = {'total': total, 'vat': vat, 'netTotal': netTotal}
                    
                    messages.success(request, f'Billing Success! <br>Total ammount to pay: <b>{calculated_data['netTotal']}TK</b><br><br><a class="btn btn-warning btn-md" id="invoiceBtn" btn-sm" target="_blank" href="/sales/invoice/{sales_id}">Check Invoice</a> for details.')
                    
                    
                    

                except ValueError:
                    messages.error(request, "Invalid Informations!")
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
    # different records for different user
    logged_in_user = request.user
    if logged_in_user.is_superuser:
        sales_records = (SalesRecord.objects.prefetch_related("items").order_by("-sale_date"))        
    else:
        sales_records = (SalesRecord.objects.prefetch_related("items").filter(user__id=logged_in_user.id).order_by("-sale_date"))
    
   
    paginator = Paginator(sales_records,10)

    sales_details_from_date = None
    sales_count_from_date = None
    today = date.today()
   
    total_sales_value = (
        sales_records.aggregate(total=Sum("netTotal"))["total"] or 0
    ) #total value of sales
    total_sales_count = sales_records.count() #total number of sales
    
    todays_total_sales_value = (sales_records.filter(sale_date__date=today).aggregate(total=Sum("netTotal"))["total"]or 0)
    #todays_total_sales_value = "{:.2f}".format(todays_total_sales_value)
    
    todays_sales_count = sales_records.filter(sale_date__date=today).count()

    filtered_records_by_date = None
    filtered_records_for_customer = None
    messages_storage = messages.get_messages(request)
    messages_storage.used = True  # Clear previous messages

        # Query Parameters
    query_date = request.GET.get("query_date")
    query_invoice = request.GET.get("query_invoice")
    query_customer_phone = request.GET.get("query_customer_phone")

    filtered_records = None  # Store the result of the selected search

    if query_date:
        filtered_records = sales_records.filter(sale_date__date=query_date)
        sales_count_from_date = filtered_records.count()
        total_sales_value_for_query_date = filtered_records.aggregate(total=Sum("netTotal"))["total"] or 0

        if sales_count_from_date > 0:
            messages.success(
                request,
                f"Sales Record for Date: {query_date} <br> Total sales: <b>{sales_count_from_date}</b> and Total value: <b>{total_sales_value_for_query_date:.2f} TK.</b>"
            )
        else:
            messages.error(request, f"No sales records exist for Date: <b> {query_date}</b>.")
            filtered_records = None  # Reset to prevent display issues later
    elif query_invoice:
        if sales_records.filter(salesId=query_invoice):
            filtered_records = sales_records.filter(salesId=query_invoice)
            messages.success(request, f"Invoice Number: {query_invoice}</b>")
        else:
            messages.error(request, f"No record found for Invoice Number: <b>{query_invoice}</b>")

    

    elif query_customer_phone:
        filtered_records = sales_records.filter(customer__customerPhone=query_customer_phone)
        sales_count_for_customer = filtered_records.count()
        total_sales_value_for_customer = filtered_records.aggregate(total=Sum("netTotal"))["total"] or 0

        if sales_count_for_customer > 0:
            messages.success(
                request,
                f"Sales Record for Customer: {query_customer_phone} <br> Total Purchases: <b>{sales_count_for_customer}</b> and Total Value: <b>{total_sales_value_for_customer:.2f} TK.</b>"
            )
        else:
            messages.error(request, f"No sales records exist for {query_customer_phone}.")
            filtered_records = None  # Reset to prevent display issues later

    else:
        messages.error(request, "Fill at least one of the three fields to search.")

    # Paginate only filtered records if search applied, else show all records
    paginator = Paginator(filtered_records if filtered_records is not None else sales_records, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)


    

    context = {
            "page_obj": page_obj,  # Unified sales records with items
            "total_sales_value": round(total_sales_value, 2),
            "total_sales_count": total_sales_count,           
            "sales_count_from_date": sales_count_from_date,
            "todays_total_sales_value": "{:.2f}".format(todays_total_sales_value),
            "todays_sales_count": todays_sales_count,
            "today": today,
            
          
    }
    return render(
        request,
        "sales.html",         
        context,)

@login_required
def customers(request):
    customer = Customer.objects.all().order_by("-total_purchase_value") # Get all records ordered by date (latest first)
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