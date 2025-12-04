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
            "Some delivery terms here"
        )

        return BaseInvoice(
            company_name="VINAS",
            logo_path=str(logo_path),
            header_subtitle="Additional info",
            company_info_lines=[
                "Some info about company",
            ],
            payment_details_usd=[
                "Bank details in usd",
            ],
            payment_details_eur=[
                "bank details in eur",
            ],
            delivery_terms=delivery_terms,
        )

