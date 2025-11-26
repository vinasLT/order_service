from pathlib import Path

from pydantic import BaseModel, Field


class BaseInvoice(BaseModel):
    company_name: str
    logo_path: str | None = None
    header_subtitle: str | None = None
    payment_details_usd: list[str] = Field(default_factory=list)
    payment_details_eur: list[str] = Field(default_factory=list)
    delivery_terms: str | None = None
    company_info_lines: list[str] = Field(default_factory=list)


class InvoiceTypes:
    @classmethod
    def get_navi_grupe_info(cls) -> BaseInvoice:
        script_dir = Path(__file__).resolve().parent
        logo_path = script_dir / "images" / "bidauto_logo.png"
        delivery_terms = (
            "CIF KLAIPEDA, by ocean. Buyer is responsible for any port, customs procedures at the destination port "
            "Klaipeda, Lithuania. All items sold AS IS, no warranty. Per the IAAI Auction Rules (Section 6) and Copart "
            "Member Terms and Conditions, buyers acknowledge that:\n"
            "Vehicles may contain hidden or undisclosed damages not visible in photos or condition reports.\n\n"
            "Vehicles purchased through auctions are generally insurance total-loss or salvage write-offs. "
            "As such, BidAuto.online and its logistics partners assume no liability for: "
            "Damage, loss, or deterioration during inland or maritime transport"
        )

        return BaseInvoice(
            company_name="NAVI GRUPE L.L.C-FZ",
            logo_path=str(logo_path),
            header_subtitle="Operated by Navi Grupe LLC-FZ",
            company_info_lines=[
                "NAVI GRUPE L.L.C-FZ",
                "Business License: 2526348.01",
                "Meydan Grandstand, 6th floor, Meydan Road, Nad Al Sheba, Dubai, U.A.E.",
            ],
            payment_details_usd=[
                "Account Title: NAVI GRUPE LLC FZ",
                "IBAN: AE540030014111047920001",
                "Account Number: 14111047920001",
                "BIC / SWIFT: ADCBAEAAXXX",
                "Bank: ABU DHABI COMMERCIAL BANK",
                "Branch Code / Branch Name: 265 / BUSINESS BAY BRANCH",
            ],
            payment_details_eur=[
                "Account Title: Navi Grupe UAB LLC",
                "IBAN: BE08905106448413",
                "SWIFT: TRWIBEB1XXX",
                "Bank: Wise, Rue du Trône 100, 3rd floor, Brussels, 1050, Belgium",
            ],
            delivery_terms=delivery_terms,
        )

    @classmethod
    def get_t_auto_logistics_info(cls) -> BaseInvoice:
        return BaseInvoice(
            company_name="T - Auto Logistics LLC",
            logo_path=None,
            header_subtitle="Operated by Navi Grupe LLC-FZ",
            payment_details_usd=[
                "Account holder: T-auto Logistics LLC",
                "BIC (SWIFT): TRWIBEB1XXX",
                "IBAN: BE70 9678 6244 2625",
                "Wise's address: Rue du Trône 100, 3rd floor Brussels 1050 Belgium",
            ],
            payment_details_eur=[],
            delivery_terms="CIF KLAIPEDA. All vehicles are sold AS IS. No warranties.",
            company_info_lines=[],
        )
    @classmethod
    def get_t_auto_logistics_usa_info(cls) -> BaseInvoice:
        script_dir = Path(__file__).resolve().parent
        logo_path = script_dir / "images" / "bidauto_logo.png"
        return BaseInvoice(
            company_name="T-Auto Logistics LLC",
            logo_path=str(logo_path),
            header_subtitle="Operated by T-Auto Logistics LLC",
            company_info_lines=[
                "T-Auto Logistics LLC",
                "1648 Victoria pointe cir",
                "Weston, FL 33327-1334",
                "USA",
            ],
            payment_details_usd=[
                "Account Title: T-Auto Logistics LLC",
                "IBAN: AE540030014111047920001",
                "Account Number: 14111047920001",
                "BIC / SWIFT: ADCBAEAAXXX",
                "Bank: ABU DHABI COMMERCIAL BANK",
                "Branch Code / Branch Name: 265 / BUSINESS BAY BRANCH",
            ],
            payment_details_eur=[
                "Account Title: T-Auto Logistics LLC",
                "IBAN: BE08905106448413",
                "SWIFT: TRWIBEB1XXX",
                "Bank: Wise, Rue du Trône 100, 3rd floor, Brussels, 1050, Belgium",
            ],
            delivery_terms="CIF KLAIPEDA. All vehicles are sold AS IS. No warranties.",
        )
