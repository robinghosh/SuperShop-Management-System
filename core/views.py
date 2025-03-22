import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import activate

from django.contrib.auth.views import LoginView
from .models import Inventory, Barcodes, SalesRecord, Customer, SalesItem

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Sum
from datetime import date, datetime, timedelta

from decimal import Decimal
from io import BytesIO
from barcode import Code39
from barcode.writer import SVGWriter
from collections import defaultdict
import logging

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
        last_thirty_days = []
        total_last_seven_days = []
        total_last_thirty_days = []
        
       
        for day in range(7):
            days = today - timedelta(day)
            last_seven_days.append(days.strftime('%Y-%m-%d'))
            
        for day in range(30):
            days = today - timedelta(day)
            last_thirty_days.append(days.strftime('%Y-%m-%d'))
            
        for days in range(len(last_seven_days)):            
            filtered_record = sales_record.filter(sale_date__date=last_seven_days[days])
            sales_value_of_day = float(filtered_record.aggregate(total=Sum("netTotal"))["total"] or 0)
            total_last_seven_days.append(sales_value_of_day)
            
        for days in range(len(last_thirty_days)):            
            filtered_record = sales_record.filter(sale_date__date=last_thirty_days[days])
            sales_value_of_day = float(filtered_record.aggregate(total=Sum("netTotal"))["total"] or 0)
            total_last_thirty_days.append(sales_value_of_day)
            
        sum_last_seven_days_value = sum(total_last_seven_days)
        sum_last_thirty_days_value = sum(total_last_thirty_days)
        
        
        context = {
            'last_seven_days': last_seven_days,
            'total_last_seven_days': total_last_seven_days,
            'sum_last_seven_days_value': sum_last_seven_days_value,
            'last_thirty_days' : last_thirty_days,
            'total_last_thirty_days': total_last_thirty_days,
            'sum_last_thirty_days_value': sum_last_thirty_days_value,
        }
        return render(request, "dashboard.html", context)
    return render(request, "dashboard.html",)



logger = logging.getLogger(__name__)

@login_required
def sales_report(request):
    start_date = request.GET.get("startDate")
    end_date = request.GET.get("endDate")

    product_wise_sales = defaultdict(lambda: {"quantity": 0, "price": 0, "subtotal": 0})
    sale_by_dates = {}
    filtered_records = SalesRecord.objects.none()
    total_value = total_vat = total_discount = sum_subtotal = 0
    
    if end_date and start_date > end_date:
            messages.error(request, f"Start Date can't be greater than End Date")
            return redirect('dashboard')
    if start_date:
        
        try:
            filter_kwargs = {"sale_date__date": start_date} if not end_date else {"sale_date__date__range": (start_date, end_date)}
            filtered_records = SalesRecord.objects.filter(**filter_kwargs)
            dates = filtered_records.values_list("sale_date__date", flat=True).distinct()                
            
            if filtered_records.exists():
                aggregates = filtered_records.aggregate(
                    total=Sum("netTotal"), 
                    vat=Sum("vatAmmount"), 
                    discount=Sum("discountAmmount")
                ) # 
                sale_by_dates = {
                    str(entry["sale_date__date"]): {
                        "total_value_by_date": "{0:.2f}".format(entry["total_value_by_date"] or 0),
                        "total_vat_by_date": "{0:.2f}".format(entry["total_vat_by_date"] or 0),
                        "total_discount_by_date": "{0:.2f}".format(entry["total_discount_by_date"] or 0)
                        }
                for entry in (
                filtered_records
                .values("sale_date__date")
                .annotate(total_value_by_date=Sum("netTotal"),
                          total_vat_by_date=Sum("vatAmmount"),
                          total_discount_by_date=Sum("discountAmmount")
                          )
                .order_by("sale_date__date"))
                }
                
                total_value = "{0:.2f}".format(aggregates["total"] or 0)
                total_vat = "{0:.2f}".format(aggregates["vat"] or 0)
                total_discount = "{0:.2f}".format(aggregates["discount"] or 0)

                for record in filtered_records:
                    for item in record.items.all():
                        product = product_wise_sales[item.productName]
                        product["quantity"] += item.quantity
                        product["subtotal"] += item.subtotal
                        product["price"] = item.price  # Assuming price remains constant per product

                sum_subtotal = sum(item["subtotal"] for item in product_wise_sales.values())

        except Exception as e:
            logger.error(f"Error fetching sales report: {e}")
            return redirect("dashboard")

    else:
        return redirect("dashboard")
    

    storage = messages.get_messages(request)
    storage.used = True 
    context = {
        "start_date": start_date,
        "end_date": end_date,
        "filtered_records": filtered_records,
        "product_wise_sales": dict(product_wise_sales),
        "sale_by_dates": sale_by_dates,       
        "sum_subtotal": sum_subtotal,
        "total_vat": total_vat,
        "total_discount": total_discount,
        "total_value": total_value,
    }
    return render(request, "sales_report.html", context)
#products View
@login_required
def products(request):
    logged_in_user = request.user
    products = Inventory.objects.all()
    empty_barcodes = Barcodes.objects.filter(is_assigned = False).first()
    paginator = Paginator(products, 10)
    # print(products.filter(productName="pran mama wafer biscuit".upper()))
    #product searching logic
    if request.method == 'GET':
        form_type = request.GET.get('form_type')
        if form_type == "search_product":
            query_name = request.GET.get('query_name')
            query_barcode = request.GET.get('query_barcode')
            if query_name:
                query_name = query_name.strip()
                products = Inventory.objects.filter(productName__icontains=query_name)
                paginator = Paginator(products, 10)
                messages.info(request, f"Found {products.count()} products by the keyword '{query_name}'")
            elif query_barcode:
                products = Inventory.objects.filter(barcode=query_barcode)
                paginator = Paginator(products, 10)
                if products.exists():
                    product_names = ", ".join([product.productName for product in products])
                    messages.info(request, f"Found product: '{product_names}' for Barcode: '{query_barcode}'")
                else:
                    messages.info(request, f"No product found for Barcode: '{query_barcode}'")
            elif query_barcode and query_name:
                products = Inventory.objects.filter(barcode=query_barcode)
                paginator = Paginator(products, 10)
            else:
                messages.error(request, f"Product Name or Barcode is empty!!")
    #product adding logic
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
                        custom_barcodes = Barcodes.objects.filter(barcodes=barcode).first() #check if barcode exists
                        Inventory.objects.create(productName=product_name, barcode=barcode, price=price, stock=stock, createdBy=logged_in_user, updatedBy=logged_in_user) #This is the line 
                        messages.success(request, f"Product: {product_name} added successfully!")
                        if custom_barcodes:
                            rv = BytesIO()
                            Code39(barcode, writer=SVGWriter(), add_checksum=False).write(rv)
                            svg_data = rv.getvalue().decode("utf-8")
                            
                            cleaned_barcode = svg_data.replace("\r\n", "")
                            custom_barcodes.product = product_name
                            custom_barcodes.is_assigned = True
                            custom_barcodes.barcode_svg = cleaned_barcode
                            custom_barcodes.save()
    
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


    context = {
        'page_obj': page_obj,
        'empty_barcodes': empty_barcodes,
    }
    return render(request, "products.html", context)

@login_required
def custom_barcodes(request):
    custom_barcodes = Barcodes.objects.filter(is_assigned=True) 
    paginator = Paginator(custom_barcodes, 10)
    page_number = request.GET.get('page')  # Get the current page number from query params
    barcode_page_obj = paginator.get_page(page_number)  # Get the specific page of records
    return render(request, 'custom_barcodes.html', {'barcode_page_obj':barcode_page_obj})

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
            try:
                del request.session['scanned_items']  
            except KeyError:
                pass
            return redirect('billing')
            

        elif form_type == 'form2':  # Update quantities and process order
            barcodes = request.POST.getlist('barcodes')
            quantities = request.POST.getlist('quantities')
            vatPercent = request.POST.get('vatPercent')
            discountPercent = request.POST.get('discountPercent')
            customerPhone = request.POST.get('customerPhone')
            paymentMethod = request.POST.get('paymentMethod')

            if vatPercent and discountPercent and customerPhone and paymentMethod:
                # Ensure barcodes and quantities lists are of the same length
                if len(barcodes) != len(quantities):
                    messages.error(request, "Invalid form submission: barcodes and quantities do not match.")
                    return redirect('billing')

                # Update quantities in the session
                for i, barcode in enumerate(barcodes):
                    for item in scanned_items:
                        if item['barcode'] == barcode:
                            if int(quantities[i]) == 0:
                                scanned_items.remove(item)
                                request.session['scanned_items'] = scanned_items
                            else:
                                item['quantity'] = int(quantities[i])
                                break
                if scanned_items:
                    request.session['scanned_items'] = scanned_items
                    request.session.modified = True
                    # Validate quantities against stock
                    for item in scanned_items:
                        product = Inventory.objects.get(barcode=item['barcode'])
                        if item['quantity'] > product.stock:
                            messages.error(request, f"Cannot set quantity of {item['productName']} more than available stock ({product.stock})")
                            return redirect('billing')

                    # Process the order
                    total = sum(Decimal(item['price']) * item['quantity'] for item in scanned_items)
                    vat = (total * Decimal(vatPercent)) / 100
                    discount = (total * Decimal(discountPercent)) / 100
                    netTotal = total + vat - discount

                    # Create customer and sales record
                    customer, _ = Customer.objects.get_or_create(customerPhone=customerPhone)
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

                    # Create sales items
                    for item in scanned_items:
                        SalesItem.objects.create(
                            sale=sale,
                            barcode=item['barcode'],
                            productName=item['productName'],
                            price=Decimal(item['price']),
                            quantity=item['quantity']
                        )

                    # Update stock
                    for item in scanned_items:
                        product = Inventory.objects.get(barcode=item['barcode'])
                        product.stock -= item['quantity']
                        product.save()

                    # Clear session
                    request.session['scanned_items'] = []
                    request.session.modified = True
                    invoice_url = reverse('invoice', args=[sale.salesId])  # Get invoice URL
                    message_html = f"""Billing Success! <br>Total amount to pay: <b>{netTotal} TK</b><br><br><button type="button" class="btn btn-success btn-sm invoice-btn" id="invoiceBtn" data-bs-toggle="modal" data-bs-target="#invoiceModal" data-url="{invoice_url}" title="Invoice">Invoice</button> for details."""
                    messages.success(request, message_html)
                 
                else:
                    messages.error(request, "Quantity can't be zero!!")
            else:
                messages.error(request, f"Fill all data correctly!!")
            
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
    if query_customer_phone and query_date:
        filtered_records = sales_records.filter(customer__customerPhone=query_customer_phone, sale_date__date=query_date)
        sales_count_for_customer = filtered_records.count()
        total_sales_value_for_customer = filtered_records.aggregate(total=Sum("netTotal"))["total"] or 0

        if sales_count_for_customer > 0:
            messages.success(
                request,
                f"Sales Record for Customer: <b>{query_customer_phone}</b> On: <b>{query_date}</b> <br> Total Purchases: <b>{sales_count_for_customer}</b> and Total Value: <b>{total_sales_value_for_customer:.2f} TK.</b>"
            )
        else:
            messages.error(request, f"No sales records exist for <b>{query_customer_phone}</b>.")
            filtered_records = None  # Reset to prevent display issues later
    elif query_date:
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
            messages.success(request, f"Found record for Invoice Number: {query_invoice}!</b>")
        else:
            messages.error(request, f"No record found for Invoice #<b>{query_invoice}</b>")    

    elif query_customer_phone:
        filtered_records = sales_records.filter(customer__customerPhone=query_customer_phone)
        sales_count_for_customer = filtered_records.count()
        total_sales_value_for_customer = filtered_records.aggregate(total=Sum("netTotal"))["total"] or 0

        if sales_count_for_customer > 0:
            messages.success(
                request,
                f"Sales Record for Customer: <b>{query_customer_phone}</b> <br> Total Purchases: <b>{sales_count_for_customer}</b> and Total Value: <b>{total_sales_value_for_customer:.2f} TK.</b>"
            )
        else:
            messages.error(request, f"No sales records exist for <b>{query_customer_phone}</b>.")
            filtered_records = None  # Reset to prevent display issues later
    

    
        
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


    


# Write to a file-like object:
