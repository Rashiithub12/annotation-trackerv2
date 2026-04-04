"""CSV export functionality."""
import csv
import io

from flask import Blueprint, Response, request
from flask_login import current_user, login_required

from app.models import Company

export_bp = Blueprint("export", __name__)


@export_bp.route("/export/csv")
@login_required
def export_csv():
    """Export researched companies in exact SOP order."""
    company_ids = request.args.getlist("ids", type=int)

    if company_ids:
        companies = Company.query.filter(
            Company.id.in_(company_ids),
            Company.user_id == current_user.id,
        ).all()
    else:
        companies = Company.query.filter_by(user_id=current_user.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Company Name",
        "Website",
        "Generic Email",
        "Brands/Products",
        "Email Source URL",
        "Brands/Products Source URL",
        "Brand Categories",
        "Duplicate",
        "Marketplace",
    ])

    for company in companies:
        writer.writerow([
            company.company_name or "",
            company.website or "",
            company.generic_email or "",
            company.brands or "",
            company.email_source_url or "",
            company.brands_source_url or "",
            company.brand_categories or "",
            company.duplicate or "No",
            company.marketplace or "No",
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=supplier_research_export.csv"},
    )
