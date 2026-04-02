"""Research routes for company research functionality."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.ai_researcher import submit_research_request
from app.models import Company

research_bp = Blueprint("research", __name__)


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


@research_bp.route("/api/research/<int:company_id>", methods=["POST"])
@login_required
def api_research(company_id):
    print(f"[DEBUG] api_research called. User: {current_user.username if current_user.is_authenticated else 'NOT AUTHENTICATED'}")
    company = Company.query.get_or_404(company_id)
    if company.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    existing_companies = [
        {"company_name": item.company_name or "", "website": item.website or ""}
        for item in Company.query.filter(
            Company.user_id == current_user.id,
            Company.id != company.id,
        ).all()
    ] 

    print(f"[DEBUG] Starting research for {company.website}")
    try:
        result = submit_research_request(
            company.website,
            existing_companies=existing_companies,
        ).result()
        print(f"[DEBUG] Research completed: {result}")
    except Exception as exc:
        print(f"[DEBUG] Exception in api_research: {exc}")
        import traceback
        traceback.print_exc()
        company.status = "failed"
        company.notes = f"Research queue error: {exc}"
        db.session.commit()
        return jsonify({"error": f"Research queue error: {exc}"}), 500

    if "error" in result:
        company.status = "failed"
        company.notes = result["error"]
        db.session.commit()
        return jsonify(result)

    company.company_name = result.get("company_name", "")
    company.website = result.get("website", company.website)
    company.generic_email = result.get("generic_email", "")
    company.email_source_url = result.get("email_source_url", "")
    company.brands = result.get("brands", "")
    company.brands_source_url = result.get("brands_source_url", "")
    company.brand_categories = result.get("brand_categories", "")
    company.duplicate = result.get("duplicate", "No")
    company.marketplace = result.get("marketplace", "No")
    company.notes = result.get("notes", "")
    company.status = "completed"
    db.session.commit()

    return jsonify(result)


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
        db.session.commit()
        flash("Company updated successfully", "success")
        return redirect(url_for("research.dashboard"))

    return render_template("edit_company.html", company=company)
