"""Research routes for company research functionality."""

import threading
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Company
from app.scraper import scrape_company, auto_assign_categories

research_bp = Blueprint("research", __name__)


def _company_payload(company):
    """Serialize company state for polling responses."""
    return {
        "id": company.id,
        "status": company.status,
        "company_name": company.company_name or "",
        "website": company.website or "",
        "generic_email": company.generic_email or "",
        "brands": company.brands or "",
        "email_source_url": company.email_source_url or "",
        "brands_source_url": company.brands_source_url or "",
        "brand_categories": company.brand_categories or "",
        "duplicate": company.duplicate or "No",
        "marketplace": company.marketplace or "No",
        "notes": company.notes or "",
        "needs_manual": company.status == "needs_review",
    }


@research_bp.route("/dashboard")
@login_required
def dashboard():
    companies = Company.query.filter_by(user_id=current_user.id).order_by(Company.created_at.desc()).all()
    return render_template("dashboard.html", companies=companies)


@research_bp.route("/research", methods=["GET", "POST"])
@login_required
def research():
    if request.method == "POST":
        website = request.form.get("website", "").strip()

        if not website:
            flash("Please enter a website URL.", "warning")
            return redirect(url_for("research.dashboard"))

        if not website.startswith(("http://", "https://")):
            website = "https://" + website

        company = Company(user_id=current_user.id, website=website, status="pending")
        db.session.add(company)
        db.session.commit()

        return redirect(url_for("research.run_research", company_id=company.id))

    return redirect(url_for("research.dashboard"))


@research_bp.route("/research/<int:company_id>")
@login_required
def run_research(company_id):
    company = Company.query.get_or_404(company_id)
    if company.user_id != current_user.id:
        flash("Unauthorized access", "danger")
        return redirect(url_for("research.dashboard"))
    return render_template("research_result.html", company=company)


def _run_scrape_in_background(company_id, app):
    """Background thread to run scraping without blocking Flask."""
    with app.app_context():
        company = Company.query.get(company_id)
        if not company:
            return

        result = scrape_company(company.website, company.company_name or "")

        if result["needs_manual"]:
            company.status = "needs_review"
            company.notes = result.get("error", "Manual review needed")
            company.generic_email = result.get("generic_email", "")
            company.email_source_url = result.get("email_source_url", "")
            company.brands = result.get("brands", "")
            company.brands_source_url = result.get("brands_source_url", "")
            if company.brands:
                company.brand_categories = auto_assign_categories(company.brands)
        else:
            company.company_name = result.get("company_name", company.company_name)
            company.generic_email = result.get("generic_email", "")
            company.email_source_url = result.get("email_source_url", "")
            company.brands = result.get("brands", "")
            company.brands_source_url = result.get("brands_source_url", "")
            if company.brands:
                company.brand_categories = auto_assign_categories(company.brands)
            company.status = "completed"
            company.notes = "Research completed successfully"

        db.session.commit()


@research_bp.route("/api/research/<int:company_id>", methods=["POST"])
@login_required
def api_research(company_id):
    company = Company.query.get_or_404(company_id)
    if company.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    if company.status == "completed":
        return jsonify({"started": False, "company": _company_payload(company)})

    if company.status == "in_progress":
        return jsonify({"started": False, "company": _company_payload(company)})

    company.status = "in_progress"
    company.notes = "Research in progress..."
    db.session.commit()

    # Run scraping in background thread so Flask doesn't block
    app = current_app._get_current_object()
    thread = threading.Thread(target=_run_scrape_in_background, args=(company.id, app))
    thread.daemon = True
    thread.start()

    return jsonify({"started": True, "company": _company_payload(company)})


@research_bp.route("/api/research/<int:company_id>/status")
@login_required
def api_research_status(company_id):
    company = Company.query.get_or_404(company_id)
    if company.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify(_company_payload(company))


@research_bp.route("/company/<int:company_id>/delete", methods=["POST"])
@login_required
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)
    if company.user_id != current_user.id:
        flash("Unauthorized access", "danger")
        return redirect(url_for("research.dashboard"))

    db.session.delete(company)
    db.session.commit()
    flash("Company deleted successfully", "success")
    return redirect(url_for("research.dashboard"))


@research_bp.route("/company/<int:company_id>/edit", methods=["GET", "POST"])
@login_required
def edit_company(company_id):
    company = Company.query.get_or_404(company_id)
    if company.user_id != current_user.id:
        flash("Unauthorized access", "danger")
        return redirect(url_for("research.dashboard"))

    if request.method == "POST":
        company.company_name = request.form.get("company_name", "")
        company.website = request.form.get("website", "")
        company.generic_email = request.form.get("generic_email", "")
        company.email_source_url = request.form.get("email_source_url", "")
        company.brands = request.form.get("brands", "")
        company.brands_source_url = request.form.get("brands_source_url", "")
        company.brand_categories = request.form.get("brand_categories", "")
        company.duplicate = request.form.get("duplicate", "No")
        company.marketplace = request.form.get("marketplace", "No")
        company.notes = request.form.get("notes", "")
        company.status = "completed"  # Mark as completed after manual edit
        db.session.commit()
        flash("Company updated successfully", "success")
        return redirect(url_for("research.dashboard"))

    return render_template("edit_company.html", company=company)
