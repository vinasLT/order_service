import os
from datetime import datetime, timezone

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from rest_framework.generics import get_object_or_404

from api.settings import MEDIA_ROOT, BASE_DIR
from orders.models import Container, Order
from orders.validators import extra_fee_validator
from utils.util import transliterate_text
from reportlab.platypus import Image


def generate_invoice_pdf(pdf_path, invoice_to, invoice_details, auction_details, items, subtotal, tax, total,
                         invoice_type):
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'dejavu-sans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'dejavu-sans-bold.ttf'))
        font_name = 'DejaVuSans'
        font_bold = 'DejaVuSans-Bold'
    except:
        font_name = 'Helvetica'
        font_bold = 'Helvetica-Bold'

    pdf = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=40,
        bottomMargin=40
    )

    elements = []


    invoice_title_style = ParagraphStyle(
        'InvoiceTitle',
        fontName=font_bold,
        fontSize=18,
        alignment=1,  # центр
        textColor=colors.black,
        spaceBefore=10,
        spaceAfter=20
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        fontName=font_name,
        fontSize=8,
        textColor=colors.black,
        leftIndent=0
    )

    ten_style = ParagraphStyle(
        'CustomNormal',
        fontName=font_name,
        fontSize=10,
        textColor=colors.black,
        leftIndent=0
    )

    bold_style = ParagraphStyle(
        'CustomBold',
        fontName=font_bold,
        fontSize=10,
        textColor=colors.black
    )

    bold_descriptions_stype = ParagraphStyle(
        'CustomBold',
        fontName=font_bold,
        fontSize=8,
        textColor=colors.black
    )
    delivery_terms_style = ParagraphStyle(
        'DeliveryTerms',
        fontName=font_name,
        fontSize=7,
        textColor=colors.black,
        leftIndent=0
    )
    script_dir = os.path.dirname(os.path.abspath(__file__))
    invoice_configs = {
        'T_AUTOLOGISTICS_INVOICE': {
            'company_name': 'T - Auto Logistics LLC',
            'logo_path': None,
            'header_subtitle': "Operated by Navi Grupe LLC-FZ",
            'payment_details_usd': [
                "Account holder: T-auto Logistics LLC",
                "BIC (SWIFT): TRWIBEB1XXX",
                "IBAN: BE70 9678 6244 2625",
                "Wise's address: Rue du Trône 100, 3rd floor Brussels 1050 Belgium"
            ],
            'payment_details_eur': [],
            'delivery_terms': "CIF KLAIPEDA. All vehicles are sold AS IS. No warranties."
        },
        'T_AUTOLOGISTICS_USA_INVOICE': {
            'company_name': 'T-Auto Logistics LLC',
            'logo_path': os.path.join(script_dir, 'images', 'bidauto_logo.png'),
            'header_subtitle': "Operated by T-Auto Logistics LLC",
            'company_info_lines': [
                'T-Auto Logistics LLC',
                '1648 Victoria pointe cir',
                'Weston, FL 33327-1334',
                'USA'
            ],
            'payment_details_usd': [
                "Account Title: T-Auto Logistics LLC",
                "IBAN: AE540030014111047920001",
                "Account Number: 14111047920001",
                "BIC / SWIFT: ADCBAEAAXXX",
                "Bank: ABU DHABI COMMERCIAL BANK",
                "Branch Code / Branch Name: 265 / BUSINESS BAY BRANCH"
            ],
            'payment_details_eur': [
                "Account Title: T-Auto Logistics LLC",
                "IBAN: BE08905106448413",
                "SWIFT: TRWIBEB1XXX",
                "Bank: Wise, Rue du Trône 100, 3rd floor, Brussels, 1050, Belgium"
            ],
            'delivery_terms': "CIF KLAIPEDA. All vehicles are sold AS IS. No warranties."
        },
        'NAVI_GRUPE_INVOICE': {
            'company_name': 'NAVI GRUPE L.L.C-FZ',
            'logo_path': os.path.join(script_dir, 'images', 'bidauto_logo.png'),
            'header_subtitle': "Operated by Navi Grupe LLC-FZ",
            'payment_details_usd': [
                "Account Title: NAVI GRUPE LLC FZ",
                "IBAN: AE540030014111047920001",
                "Account Number: 14111047920001",
                "BIC / SWIFT: ADCBAEAAXXX",
                "Bank: ABU DHABI COMMERCIAL BANK",
                "Branch Code / Branch Name: 265 / BUSINESS BAY BRANCH"
            ],
            'payment_details_eur': [
                "Account Title: Navi Grupe UAB LLC",
                "IBAN: BE08905106448413",
                "SWIFT: TRWIBEB1XXX",
                "Bank: Wise, Rue du Trône 100, 3rd floor, Brussels, 1050, Belgium"
            ],
            'delivery_terms': "CIF KLAIPEDA, by ocean. Buyer is responsible for any port, "
                              "customs procedures at the destination port Klaipeda, Lithuania."
                              " All items sold AS IS, no warranty. "
                              "Per the IAAI Auction Rules (Section 6) and Copart Member Terms and Conditions, buyers acknowledge that:\n"
                            "Vehicles may contain hidden or undisclosed damages not visible in photos or condition reports.\n\n"

"Vehicles purchased through auctions are generally insurance total-loss or salvage write-offs."
"As such, BidAuto.online and its logistics partners assume no liability for:"
"Damage, loss, or deterioration during inland or maritime transport"
        }
    }

    print(invoice_type.upper())
    config = invoice_configs.get(invoice_type.upper())
    if not config:
        raise ValueError(f'Wrong invoice_type: {invoice_type}')

    header_subtitle = config.get('header_subtitle', "Operated by Navi Grape LLC-FZ")

    # 1. Логотип и название компании - точно как на скриншоте
    logo_path = config.get('logo_path')

    # Стили для заголовка
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=getSampleStyleSheet()['Heading1'],
        fontSize=36,
        textColor=colors.black,
        fontName='Helvetica-Bold',
        leading=40,
        spaceAfter=0,
        spaceBefore=0,
        leftIndent=10,
    )

    # Стиль для подписи с отступами
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=getSampleStyleSheet()['Normal'],
        fontSize=9,
        textColor=colors.black,
        fontName='Helvetica',
        leading=10,
        spaceAfter=0,
        spaceBefore=0,
        leftIndent=10,
        rightIndent=10,
    )

    if logo_path and os.path.isfile(logo_path):
        try:
            # Создаем логотип
            logo = Image(logo_path, width=80, height=80)

            # Создаем текстовую часть
            title_text = Paragraph("BIDAUTO.ONLINE", title_style)
            subtitle_text = Paragraph(header_subtitle, subtitle_style)

            # Создаем таблицу для размещения логотипа и текста
            header_data = [
                [logo, title_text],
                ['', subtitle_text]
            ]

            header_table = Table(header_data, colWidths=[90, 400])
            header_table.setStyle(TableStyle([
                # Логотип
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                ('SPAN', (0, 0), (0, 1)),  # Объединяем логотип на 2 строки
                # Заголовок
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                ('VALIGN', (1, 0), (1, 0), 'BOTTOM'),
                # Подпись
                ('ALIGN', (1, 1), (1, 1), 'LEFT'),
                ('VALIGN', (1, 1), (1, 1), 'TOP'),
                # Отступы
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                # Центрирование всей таблицы
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))

            # Центрируем таблицу на странице
            centered_table = Table([[header_table]], colWidths=[500])
            centered_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), -70),
                ('TOPPADDING', (0, 0), (-1, -1), -30),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))

            elements.append(centered_table)

        except Exception as e:
            print(f"Ошибка загрузки логотипа: {e}")
            # Если логотип не загрузился, показываем только текст по центру
            title_center_style = ParagraphStyle(
                'TitleCenterStyle',
                parent=title_style,
                alignment=TA_CENTER,
                leftIndent=0,
            )
            subtitle_center_style = ParagraphStyle(
                'SubtitleCenterStyle',
                parent=subtitle_style,
                alignment=TA_CENTER,
                leftIndent=0,
            )
            elements.append(Paragraph("BIDAUTO.ONLINE", title_center_style))
            elements.append(Paragraph(header_subtitle, subtitle_center_style))
    else:
        # Если логотип не найден, показываем только текст по центру
        title_center_style = ParagraphStyle(
            'TitleCenterStyle',
            parent=title_style,
            alignment=TA_CENTER,
            leftIndent=0,
        )
        subtitle_center_style = ParagraphStyle(
            'SubtitleCenterStyle',
            parent=subtitle_style,
            alignment=TA_CENTER,
            leftIndent=0,
        )
        elements.append(Paragraph("BIDAUTO.ONLINE", title_center_style))
        elements.append(Paragraph(header_subtitle, subtitle_center_style))

    # 2. Заголовок INVOICE
    elements.append(Paragraph("INVOICE", invoice_title_style))
    elements.append(Spacer(1, -5))

    # 3. Invoice Number и Date с подчеркиваниями
    invoice_info_data = [
        [Paragraph("Invoice Number:", ten_style), Paragraph("_" * 20, ten_style)],
        [Paragraph("Invoice Date:", ten_style), Paragraph("_" * 20, ten_style)]
    ]

    # Извлекаем номер инвойса и дату из invoice_details если они есть
    if invoice_details and len(invoice_details) >= 2:
        try:
            # Предполагаем что первые две строки содержат номер и дату
            invoice_number = invoice_details[0].replace("Invoice #:", "").strip() if "Invoice #:" in invoice_details[
                0] else invoice_details[0]
            invoice_date = invoice_details[1].replace("Invoice Date:", "").strip() if "Date:" in invoice_details[1] else \
            invoice_details[1]

            invoice_info_data = [
                [Paragraph("Invoice Number:", ten_style), Paragraph(invoice_number, ten_style)],
                [Paragraph("Invoice Date:", ten_style), Paragraph(invoice_date, ten_style)]
            ]
        except:
            pass

    invoice_info_table = Table(invoice_info_data, colWidths=[120, 150])
    invoice_info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    elements.append(invoice_info_table)
    elements.append(Spacer(1, 0))

    # 4. Invoice by и Invoice to в две колонки
    invoice_by_data = [[Paragraph("<b>Invoice by:</b>", bold_style)]]
    # Используем данные компании из конфига
    company_info = config.get('company_info_lines', [
        f"{config['company_name']}",
        "Business License: 2526348.01",
        "Meydan Grandstand, 6th floor, Meydan Road, Nad Al Sheba, Dubai, U.A.E."
    ])
    for line in company_info:
        invoice_by_data.append([Paragraph(line, ten_style)])

    invoice_to_data = [[Paragraph("<b>Invoice to:</b>", bold_style)]]

    # Объединяем все строки через запятую
    invoice_to_text = ", ".join(invoice_to)

    # Создаем один параграф со всем текстом
    invoice_to_data.append([Paragraph(invoice_to_text, ten_style)])

    invoice_by_table = Table(invoice_by_data, colWidths=[230])
    invoice_to_table = Table(invoice_to_data, colWidths=[230])

    # Верхняя таблица с invoice_by и invoice_to
    top_table = Table([[invoice_by_table, invoice_to_table]], colWidths=[250, 250])
    top_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -10),
    ]))

    # Создаем auction details в одну строку
    auction_details_text = " | ".join(auction_details)
    auction_details_text += " | " + " | ".join(invoice_details[2:])
    auction_details_data = [
        [Paragraph("<b>Auction details:</b>", bold_style), Paragraph(auction_details_text, ten_style)],
    ]

    auction_details_table = Table(auction_details_data, colWidths=[87, 310])
    auction_details_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),  # Выравниваем заголовок по центру
    ]))

    # Основная таблица с двумя строками
    main_info_table = Table([
        [top_table],
        [auction_details_table]
    ], colWidths=[500])
    main_info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    elements.append(main_info_table)
    elements.append(Spacer(1, 0))

    # 5. Таблица товаров с новой структурой (Description, Quantity, Unit Price, Total)
    table_headers = [
        Paragraph("<b>Description</b>", bold_style),
        Paragraph("<b>Quantity</b>", bold_style),
        Paragraph("<b>Unit Price</b>", bold_style),
        Paragraph("<b>Total</b>", bold_style)
    ]

    # Преобразуем items для новой структуры таблицы
    # Предполагаем, что items содержит данные в формате [номер, описание, количество, общая_сумма]
    table_data = [table_headers]

    for item in items:
        if len(item) >= 4:
            # Вычисляем unit price как total/quantity
            try:
                quantity = float(str(item[2]).replace(',', '.')) if item[2] else 1
                total_price = float(str(item[3]).replace('$', '').replace(',', '.')) if item[3] else 0
                unit_price = total_price / quantity if quantity != 0 else 0

                row = [
                    item[1],  # описание
                    str(int(quantity)) if quantity == int(quantity) else str(quantity),  # количество
                    f"${unit_price:.2f}",  # цена за единицу
                    f"${total_price:.2f}"  # общая сумма
                ]
            except:
                row = [item[1], str(item[2]), "$0.00", str(item[3])]
        else:
            # Если формат данных не соответствует ожидаемому
            row = [str(item[1]) if len(item) > 1 else "---",
                   str(item[2]) if len(item) > 2 else "1",
                   "$0.00",
                   str(item[3]) if len(item) > 3 else "$0.00"]

        table_data.append(row)


    # Добавляем строку с итогом
    table_data.append(["", "", Paragraph("<b>Total:</b>", bold_style), f"${total:.2f}"])

    items_table = Table(table_data, colWidths=[240, 60, 100, 100])
    items_table.setStyle(TableStyle([
        # Заголовок
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), font_bold),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('TOPPADDING', (0, 0), (-1, 0), 5),

        # Все остальные ячейки
        ('FONTNAME', (0, 1), (-1, -1), font_name),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Quantity по центру
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Unit Price по центру
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Total по центру
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Description слева

        # Рамки
        ('GRID', (0, 0), (-1, -1), 0.1, colors.black),

        # Отступы
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 0),
    ]))

    elements.append(items_table)
    elements.append(Spacer(1, 10))

    # 6. Delivery Terms
    elements.append(Paragraph("<b>Delivery Terms:</b>", bold_descriptions_stype))
    elements.append(Spacer(1, -1))
    elements.append(Paragraph(config['delivery_terms'], delivery_terms_style))
    elements.append(Spacer(1, 5))

    # 7. Bank Details
    elements.append(Paragraph("<b>Bank Details (USD Currency):</b>", bold_descriptions_stype))
    elements.append(Spacer(1, 5))

    for detail in config['payment_details_usd']:
        elements.append(Paragraph(detail, normal_style))

    if config['payment_details_eur']:
        elements.append(Spacer(1, 5))
        elements.append(Paragraph("<b>EUR Currency:</b>", bold_descriptions_stype))
        elements.append(Spacer(1, 5))

        for detail in config['payment_details_eur']:
            elements.append(Paragraph(detail, normal_style))

    elements.append(Spacer(1, 5))

    # 8. Thank you message
    thank_you_style = ParagraphStyle(
        'ThankYou',
        fontName=font_name,
        fontSize=8,
        alignment=1,  # по центру
        textColor=colors.black
    )
    elements.append(Paragraph("<i>Thank you for your business.</i>", thank_you_style))

    # Собираем PDF
    pdf.build(elements)
    return pdf_path



def generate_invoice_path(vin):
    file_name = f'{vin}.pdf'
    file_path = os.path.join(MEDIA_ROOT, 'invoices', file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    return file_path


def generate_invoice_to(user):
    first_name = transliterate_text(user.first_name)
    last_name = transliterate_text(user.last_name)
    address = transliterate_text(user.delivery_info.address)
    city = transliterate_text(user.delivery_info.city)
    state = transliterate_text(user.delivery_info.state)
    country = transliterate_text(user.delivery_info.country)

    invoice_to = [
        f"{first_name} {last_name}",
        f"{address}",
        f"{city}, {state}",
        f"{country} - {user.delivery_info.zip_code}",
        f"{user.phone_number}",
        f"{user.email}"
    ]
    return invoice_to


def generate_invoice_details(obj):
    formatted_date = obj.created_at.strftime("%B %d, %Y")
    invoice_details = [
        f"Invoice #: {obj.vin}",
        f"Invoice Date: {formatted_date}",
    ]

    if obj.__class__.__name__ == 'Order':
        vehicle_type = obj.vehicle_type
        if vehicle_type == 'MOTO':
            vehicle_type = 'MOTORCYCLE'
        invoice_details.append(f"Vehicle Type: {vehicle_type}")
        invoice_details.append(f"Lot No.: {obj.lot_id}")
    return invoice_details


def generate_auction_details(order):
    if not order.container:
        destination = Container.KLAIPEDA
    else:
        destination = order.container.destination

    specific_date = datetime(2024, 8, 25, 1, 0, 0, 0, tzinfo=timezone.utc)
    if order.created_at >= specific_date:
        if destination == Container.ROTTERDAM:
            destination = f'{destination} (3 car load)'

    auction_details = [
        f"Auction: {order.location.location}",
        f"Type: {order.auction_name}",
        f"Terminal: {order.terminal}",
        f"Destination: {destination}"
    ]
    return auction_details


def generate_invoice_items(items, additional_fees=None):
    invoice_items = []
    item_number = 1
    for item_name, item_amount in items.items():
        invoice_items.append([str(item_number), item_name, "1", f"${item_amount:.2f}"])
        item_number += 1

    if additional_fees:

        extra_fee_validator(additional_fees)
        for fees in additional_fees:
            if len(fees['name']) == 0:
                continue
            invoice_items.append([str(item_number), fees["name"], "1", f"${fees['amount']:.2f}"])

    return invoice_items


def generate_custom_invoice(invoice_to, invoice_details, auction_details, items):
    invoice_to = [
        f'{invoice_to.get('full_name', '')}',
        f'{invoice_to.get('address', '')}',
        f'{invoice_to.get('state', '')}',
        f'{invoice_to.get('city', '')}',
        f'{invoice_to.get('country', '')}',
        f'{invoice_to.get('zip_code', '')}',
        f'{invoice_to.get('phone', '')}',
        f'{invoice_to.get('email', '')}',
    ]
    file_path = generate_invoice_path('custom_invoice')

    invoice_details = [
        f"Invoice #: {invoice_details.get('invoice_number', '')}",
        f"Invoice Date: {invoice_details.get('invoice_date', '')}",
        f"Lot No.: {invoice_details.get('lot_number', '')}"
    ]
    auction_details = [
        f"Auction: {auction_details.get('auction_city', '')}",
        f"Type: {auction_details.get('auction_name', '')}",
        f"Terminal: {auction_details.get('terminal', '')}",
        f"Destination: {auction_details.get('destination', '')}"
    ]

    total = 0
    for key, value in items.items():
        total += value
    items = generate_invoice_items(items)

    return {'file_path': file_path, 'invoice_to': invoice_to, 'invoice_details': invoice_details,
            'auction_details':auction_details, 'items': items, 'total': total}

def get_depth_video_invoice(order_id):
    order = get_object_or_404(Order, pk=order_id)
    depth_video_price = 100
    invoice_to = generate_invoice_to(order.user)
    invoice_details = generate_invoice_details(order)
    auction_details = generate_auction_details(order)
    items = generate_invoice_items({"Video in depth review": depth_video_price})
    file_path = generate_invoice_path(f'{order.vin}_depth_video')

    generate_invoice_pdf(file_path, invoice_to, invoice_details,
                         auction_details, items, depth_video_price, 0,
                         depth_video_price, Order.T_AUTOLOGISTIC_INVOICE)
    return file_path

class Invoice:
    def __init__(self, order: Order):
        self.order = order

    def generate_invoice(self):
