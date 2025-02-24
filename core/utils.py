from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
import os
from django.conf import settings

#Creating POS paper size
pos = (76*mm, 203*mm)

def generate_invoice(salesId, customer_phone, items, total_amount):
    """Generates a PDF invoice and saves it to a folder."""
    #invoice_path = os.path.join(settings.INVOICE_DIR, f"invoice_{salesId}.pdf")
    invoice_path = os.path.join('',f"invoice_{salesId}.pdf")
    
    pdf = canvas.Canvas(invoice_path, pagesize=pos)
    
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(30, 550, f"Super Shop Management System")
    pdf.drawString(1, 545, "_"*50)
    # Invoice Title
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(30, 530, f"Invoice #{salesId}")
    
    
    # Customer Info
    pdf.setFont("Helvetica", 9)
    pdf.drawString(30, 500, f"Customer Phone: {customer_phone}")
    
    # Table Headers
    pdf.drawString(100, 690, "Product")
    pdf.drawString(300, 690, "Quantity")
    pdf.drawString(400, 690, "Price")
    
    # Add Items
    y_position = 670
    for item in items:
        pdf.drawString(100, y_position, item['productName'])
        pdf.drawString(300, y_position, str(item['quantity']))
        pdf.drawString(400, y_position, f"${item['price']}")
        y_position -= 20
    
    # Total Amount
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(400, y_position - 20, f"Total: ${total_amount}")

    pdf.save()
    
    return invoice_path  # Return the saved invoice path

dictt = [{
    'productName': 'Hello',
    "quantity": 4,
    "price": 400
}]
generate_invoice(100, 1784410438, dictt, 500)