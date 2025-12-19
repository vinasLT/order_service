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
    def get_default_info(cls) -> BaseInvoice:
        script_dir = Path(__file__).resolve().parent
        logo_path = script_dir / "images" / "vinaslt_logo.png"
        delivery_terms = (
            ""
        )

        return BaseInvoice(
            company_name='VINAS',
            logo_path=str(logo_path),
            header_subtitle=None,
            company_info_lines=[
                'UAB "HVJ LOGISTIC"',
                "Įm. kodas 306661666",
                "PVM mokėtojo kodas LT100016791816",
                "V. Nagevičiaus g. 3, Vilnius, Lietuva",
                "SEB — LT88704409010848345",
            ],
            payment_details_usd=[
                # No USD account provided
            ],
            payment_details_eur=[
                "Bank: SEB",
                "IBAN: LT88704409010848345",
            ],
            delivery_terms=delivery_terms,
        )
