import asyncio
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from app.database.models import Order
from app.enums.order import InvoiceTypeEnum
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from app.rpc_client.auth import AuthRpcClient
from app.services.invoice_generator.invoice_types import InvoiceTypes, BaseInvoice


class InvoiceGenerator:
    def __init__(self, order: Order):
        self.order = order

    def _load_user_via_rpc(self):
        if not getattr(self.order, "user_uuid", None):
            return None

        async def _fetch():
            async with AuthRpcClient() as client:
                return await client.get_user(user_uuid=self.order.user_uuid)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Avoid nesting event loops; skip RPC in this edge case.
            return None

        try:
            return asyncio.run(_fetch())
        except Exception:
            return None

    def _build_invoice_to_lines(self) -> list[str]:
        lines: list[str] = []
        user = self._load_user_via_rpc()
        if user:
            full_name = f"{user.first_name} {user.last_name}".strip()
            if full_name:
                lines.append(full_name)
            if user.email:
                lines.append(user.email)
            if user.phone_number:
                lines.append('+' + user.phone_number)
            if user.address:
                user_address = user.address
                lines.extend([user_address.address, user_address.city, user_address.state, user_address.country, str(user_address.zip_code)])

        elif getattr(self.order, "user_uuid", None):
            lines.append(f"User UUID: {self.order.user_uuid}")

        return [line for line in lines if line]

    def generate_invoice_based_on_invoice_type(
        self,
        invoice_type: InvoiceTypeEnum | None = None,
        save_path: str | Path | None = None,
    ) -> bytes:
        info_mapping = {
            InvoiceTypeEnum.DEFAULT: InvoiceTypes.get_default_info,
        }
        if not invoice_type:
            invoice_type = self.order.invoice_type

        info_getter = info_mapping.get(invoice_type)
        if not info_getter:
            raise ValueError(f"Unsupported invoice type: {invoice_type}")

        info = info_getter()
        pdf_bytes = self.generate_pdf(info)

        if save_path:
            output_path = Path(save_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(pdf_bytes)

        return pdf_bytes

    def generate_pdf(self, info: BaseInvoice) -> bytes:
        """
        Build invoice PDF bytes using BaseInvoice metadata and the current order data.
        """
        buffer = BytesIO()

        # Fonts: attempt to load DejaVu, fallback to Helvetica
        font_name = "Helvetica"
        font_bold = "Helvetica-Bold"
        try:
            font_dir = Path(__file__).resolve().parent
            regular_font = font_dir / "fonts" / "dejavu-sans.ttf"
            bold_font = font_dir / "fonts" / "dejavu-sans-bold.ttf"
            if regular_font.exists() and bold_font.exists():
                pdfmetrics.registerFont(TTFont("DejaVuSans", str(regular_font)))
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(bold_font)))
                font_name = "DejaVuSans"
                font_bold = "DejaVuSans-Bold"
        except Exception:
            # fall back silently to Helvetica
            font_name = "Helvetica"
            font_bold = "Helvetica-Bold"

        pdf = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        header_title_style = ParagraphStyle(
            "HeaderTitleStyle",
            parent=styles["Heading1"],
            fontSize=36,
            textColor=colors.black,
            fontName=font_bold,
            leading=40,
            spaceAfter=0,
            spaceBefore=0,
            leftIndent=10,
        )
        header_subtitle_style = ParagraphStyle(
            "HeaderSubtitleStyle",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.black,
            fontName=font_name,
            leading=10,
            spaceAfter=0,
            spaceBefore=0,
            leftIndent=10,
            rightIndent=10,
        )
        title_center_style = ParagraphStyle(
            "HeaderTitleCenterStyle",
            parent=header_title_style,
            alignment=TA_CENTER,
            leftIndent=0,
        )
        subtitle_center_style = ParagraphStyle(
            "HeaderSubtitleCenterStyle",
            parent=header_subtitle_style,
            alignment=TA_CENTER,
            leftIndent=0,
        )
        invoice_title_style = ParagraphStyle(
            "InvoiceTitleStyle",
            parent=styles["Heading1"],
            fontSize=18,
            alignment=1,
            spaceBefore=1,
            spaceAfter=1,
            fontName=font_bold,
            textColor=colors.black,
        )
        bold_style = ParagraphStyle(
            "BoldStyle",
            parent=styles["Heading4"],
            fontSize=10,
            fontName=font_bold,
            textColor=colors.black,
        )
        ten_style = ParagraphStyle(
            "TenStyle",
            parent=styles["Normal"],
            fontSize=10,
            fontName=font_name,
            textColor=colors.black,
        )
        ten_style_center = ParagraphStyle(
            "TenStyleCenter",
            parent=ten_style,
            alignment=1,
        )
        normal_style = ParagraphStyle(
            "NormalStyle",
            parent=styles["Normal"],
            fontSize=8,
            fontName=font_name,
            textColor=colors.black,
        )
        bold_descriptions_style = ParagraphStyle(
            "BoldDescriptionsStyle",
            parent=styles["Normal"],
            fontSize=8,
            fontName=font_bold,
            textColor=colors.black,
        )
        delivery_terms_style = ParagraphStyle(
            "DeliveryTerms",
            fontName=font_name,
            fontSize=7,
            textColor=colors.black,
            leftIndent=0,
        )
        item_text_style = ParagraphStyle(
            "ItemTextStyle",
            parent=styles["Normal"],
            fontSize=9,
            fontName=font_name,
            textColor=colors.black,
        )
        thank_you_style = ParagraphStyle(
            "ThankYouStyle",
            parent=styles["Normal"],
            fontSize=8,
            fontName=font_name,
            alignment=1,
            textColor=colors.black,
        )

        elements = []

        # Header with optional logo, mirrored from legacy template proportions
        subtitle = info.header_subtitle or ""
        logo_path = Path(info.logo_path) if info.logo_path else None
        if logo_path and logo_path.exists():
            try:
                logo = Image(str(logo_path), width=80, height=80)
                title_text = Paragraph("VINAS.LT", header_title_style)
                subtitle_text = Paragraph(str(subtitle), header_subtitle_style) if subtitle else Spacer(1, 0)
                header_data = [
                    [logo, title_text],
                    ["", subtitle_text],
                ]
                header_table = Table(header_data, colWidths=[90, 400])
                header_table.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (0, 0), "CENTER"),
                            ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
                            ("SPAN", (0, 0), (0, 1)),
                            ("ALIGN", (1, 0), (1, 0), "LEFT"),
                            ("VALIGN", (1, 0), (1, 0), "BOTTOM"),
                            ("ALIGN", (1, 1), (1, 1), "LEFT"),
                            ("VALIGN", (1, 1), (1, 1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 5),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ]
                    )
                )
                centered_table = Table([[header_table]], colWidths=[500])
                centered_table.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (0, 0), "CENTER"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), -70),
                            ("TOPPADDING", (0, 0), (-1, -1), -30),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                        ]
            )
                )
                elements.append(centered_table)
            except Exception:
                elements.append(Paragraph("VINAS.LT", title_center_style))
                if subtitle:
                    elements.append(Paragraph(str(subtitle), subtitle_center_style))
        else:
            elements.append(Paragraph("VINAS.LT", title_center_style))
            if subtitle:
                elements.append(Paragraph(str(subtitle), subtitle_center_style))

        elements.append(Paragraph("INVOICE", invoice_title_style))
        elements.append(Spacer(1, 2))

        invoice_number = f"{self.order.vin}"
        invoice_date = (
            self.order.created_at if isinstance(self.order.created_at, datetime) else datetime.now(timezone.utc)
        )
        invoice_info = Table(
            [
                [Paragraph("<b>Invoice Number:</b>", ten_style_center), Paragraph(invoice_number, ten_style_center)],
                [Paragraph("<b>Invoice Date:</b>", ten_style_center), Paragraph(invoice_date.strftime("%B %d, %Y"), ten_style_center)],
            ],
            colWidths=[180, 180],
        )
        invoice_info.hAlign = "CENTER"
        invoice_info.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(invoice_info)
        elements.append(Spacer(1, 6))

        # Invoice by / to
        company_lines = info.company_info_lines or [info.company_name]
        invoice_by_rows = [[Paragraph("<b>Invoice by:</b>", bold_style)]] + [
            [Paragraph(str(line), ten_style)] for line in company_lines
        ]
        invoice_by_table = Table(invoice_by_rows, colWidths=[250])

        invoice_to_lines = self._build_invoice_to_lines()
        invoice_to_rows = [[Paragraph("<b>Invoice to:</b>", bold_style)]]
        if invoice_to_lines:
            invoice_to_rows.append([Paragraph(", ".join(invoice_to_lines), ten_style)])
        invoice_to_table = Table(invoice_to_rows, colWidths=[250])

        parties_table = Table([[invoice_by_table, invoice_to_table]], colWidths=[260, 260])
        parties_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        elements.append(parties_table)
        elements.append(Spacer(1, -6))

        auction_details = " | ".join(
            [
                f"Auction: {self.order.auction}",
                f"Lot: {self.order.lot_id}",
                f"VIN: {self.order.vin}",
                f"Vehicle: {self.order.vehicle_name}",
                f"Location: {self.order.location_name}",
            ]
        )
        auction_details_table = Table(
            [
                [Paragraph("<b>Auction details:</b>", bold_style), Paragraph(auction_details, ten_style)],
            ],
            colWidths=[120, 360],
        )
        auction_details_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        elements.append(auction_details_table)
        elements.append(Spacer(1, 8))

        # Items
        items_table_data = [
            [
                Paragraph("<b>Description</b>", bold_style),
                Paragraph("<b>Quantity</b>", bold_style),
                Paragraph("<b>Unit Price</b>", bold_style),
                Paragraph("<b>Total</b>", bold_style),
            ]
        ]

        total_amount = 0.0
        for item in self.order.invoice_items or []:
            quantity = 1
            amount = float(item.amount)
            total_amount += amount
            items_table_data.append(
                [
                    Paragraph(item.name, item_text_style),
                    Paragraph(str(quantity), item_text_style),
                    Paragraph(f"${amount:.2f}", item_text_style),
                    Paragraph(f"${amount:.2f}", item_text_style),
                ]
            )

        items_table_data.append(
            [
                "",
                "",
                Paragraph("<b>Total:</b>", bold_style),
                Paragraph(f"${total_amount:.2f}", bold_style),
            ]
        )

        items_table = Table(items_table_data, colWidths=[240, 60, 100, 100])
        items_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), font_bold),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("FONTNAME", (0, 1), (-1, -1), font_name),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.75, colors.black),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("BACKGROUND", (0, 1), (-1, -2), colors.whitesmoke),
                    ("TOPPADDING", (0, 0), (-1, 0), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                    ("TOPPADDING", (0, 1), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 1),
                ]
            )
        )
        elements.append(items_table)
        elements.append(Spacer(1, 6))

        if info.delivery_terms:
            elements.append(Paragraph("<b>Delivery Terms:</b>", bold_descriptions_style))
            elements.append(Spacer(1, 2))
            elements.append(Paragraph(info.delivery_terms, delivery_terms_style))
            elements.append(Spacer(1, 8))

        if info.payment_details_usd:
            elements.append(Paragraph("<b>Bank Details (USD):</b>", bold_descriptions_style))
            for line in info.payment_details_usd:
                elements.append(Paragraph(str(line), normal_style))
            elements.append(Spacer(1, 6))

        if info.payment_details_eur:
            elements.append(Paragraph("<b>Bank Details (EUR):</b>", bold_descriptions_style))
            for line in info.payment_details_eur:
                elements.append(Paragraph(str(line), normal_style))
            elements.append(Spacer(1, 6))

        elements.append(Paragraph("<i>Thank you for your business.</i>", thank_you_style))

        pdf.build(elements)
        buffer.seek(0)
        return buffer.read()


if __name__ == "__main__":
    class _DummyItem:
        def __init__(self, name: str, amount: int):
            self.name = name
            self.amount = amount
            self.is_extra_fee = False

    class _DummyOrder:
        def __init__(self):
            self.invoice_type = InvoiceTypeEnum.DEFAULT
            self.vin = "TESTVIN1234567890"
            self.created_at = datetime.now(timezone.utc)
            self.auction = "COPART"
            self.lot_id = 123456
            self.vehicle_name = "Test Vehicle"
            self.location_name = "Test Location"
            self.user_uuid = "c2ead8a4-36b5-49ba-b884-4ee818ec8ce9"
            self.invoice_items = [
                _DummyItem("Vehicle Price", 10000),
                _DummyItem("Broker Fee", 500),
                _DummyItem("Insurance", 1000),
                _DummyItem("Shipping", 100),
                _DummyItem("Taxes", 100),
                _DummyItem("Extra Fee", 100),
                _DummyItem("Total", 12000),
                _DummyItem('test', 324),
                _DummyItem('test2', 324),
                _DummyItem('test3', 324),
                _DummyItem('test4', 324),
                _DummyItem('test5', 324),
            ]

    dummy_order = _DummyOrder()
    generator = InvoiceGenerator(dummy_order)  # type: ignore[arg-type]
    output_file = Path(__file__).resolve().parent / "test_invoice.pdf"
    generator.generate_invoice_based_on_invoice_type(save_path=output_file)
    print(f"Invoice generated at {output_file}")
