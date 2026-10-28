from flask import Blueprint, render_template, session, redirect, request, url_for, current_app, abort, flash
from extensions import db
from models import (
    Opportunity, OpportunitySignups, ServiceRecord,
    User, Organization, OrganizationMember, OrganizationAdminRequest
)
import os
from werkzeug.utils import secure_filename
from uuid import uuid4
from decimal import Decimal
from datetime import datetime
from sqlalchemy import or_


organizations_bp = Blueprint("organizations", __name__)


@organizations_bp.route("/organization-details/<int:organization_id>")
def organization_details(organization_id):
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)

    if user is None:
        session.pop("user_id", None)
        return redirect(url_for("auth.login"))

    organization = db.get_or_404(Organization, organization_id)

    membership = OrganizationMember.query.filter_by(
        organization_id=organization.id,
        user_id=user.id
    ).first()

    if membership is None or membership.role not in ("owner", "admin"):
        abort(403)

    is_owner = membership.role == "owner"

    opportunities = list(organization.opportunities)

    open_count = Opportunity.query.filter_by(
        organization_id=organization.id,
        status="open"
    ).count()

    members_count = OrganizationMember.query.filter_by(
        organization_id=organization.id
    ).count()

    service_hours = ServiceRecord.query.filter_by(
        organization_name=organization.name
    ).all()

    verified_hours = sum(
        (
            record.hours
            for record in service_hours
            if record.status == "verified"
        ),
        Decimal("0.00")
    )

    approved_counts = {
        opportunity.id: sum(
            signup.status == "approved"
            for signup in opportunity.signups
        )
        for opportunity in opportunities
    }

    pending_admin_requests = (
        OrganizationAdminRequest.query.filter_by(
            organization_id=organization.id,
            status="pending"
        ).all()
        if is_owner else []
    )

    volunteers = (
        OpportunitySignups.query
        .join(OpportunitySignups.opportunity)
        .filter(Opportunity.organization_id == organization.id)
        .all()
    )

    return render_template(
        "organization_details.html",
        user=user,
        organization=organization,
        membership=membership,
        is_owner=is_owner,
        opportunities=opportunities,
        open_count=open_count,
        members_count=members_count,
        service_hours=service_hours,
        verified_hours=verified_hours,
        approved_counts=approved_counts,
        pending_admin_requests=pending_admin_requests,
        volunteers=volunteers
    )


@organizations_bp.route("/manage-organizations", methods=["GET", "POST"])
def manage_organizations():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)
    if user is None:
        session.pop("user_id", None)
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name = request.form.get("name")
        location = request.form.get("location")
        contact_email = request.form.get("contact_email")
        cause = request.form.get("primary_cause")
        description = request.form.get("description")
        image = request.files.get("image")

        image_filename = None

        if image and image.filename:
            safe_name = secure_filename(image.filename)
            extension = os.path.splitext(safe_name)[1].lower()

            if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
                return "Please upload a PNG, JPG, or WEBP image.", 400

            image_filename = f"{uuid4().hex}{extension}"
            os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
            image.save(
                os.path.join(
                    current_app.config["UPLOAD_FOLDER"],
                    image_filename
                )
            )

        organization = Organization(
            name, cause, contact_email, location,
            description, image_filename
        )
        db.session.add(organization)
        db.session.flush()

        membership = OrganizationMember(
            user.id, organization.id, "owner"
        )
        db.session.add(membership)
        db.session.commit()

        flash("Organization created.", "success")
        return redirect(url_for("organizations.manage_organizations"))

    memberships = OrganizationMember.query.filter_by(
        user_id=user.id
    ).all()
    organizations_dict = {}

    for membership in memberships:
        organization = membership.organization

        member_count = OrganizationMember.query.filter_by(
            organization_id=organization.id
        ).count()

        opportunity_count = Opportunity.query.filter_by(
            organization_id=organization.id
        ).count()

        organizations_dict[organization] = [
            membership.role,
            member_count,
            opportunity_count
        ]

    return render_template(
        "organizations.html",
        user=user,
        organizations_dict=organizations_dict
    )


@organizations_bp.route("/signups/<int:signup_id>/remove", methods=["POST"])
def remove_volunteer(signup_id):
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("auth.login"))

    signup = db.get_or_404(OpportunitySignups, signup_id)

    membership = OrganizationMember.query.filter_by(
        user_id=user_id,
        organization_id=signup.organization_id
    ).first()

    if membership is None or membership.role not in ("owner", "admin"):
        abort(403)

    signup.status = "removed"
    db.session.commit()

    flash("Volunteer removed.", "info")

    return redirect(url_for(
        "organizations.organization_details",
        organization_id=signup.organization.id
    ))


@organizations_bp.route("/service-hours/<int:record_id>/review", methods=["POST"])
def review_service_hour(record_id):
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("auth.login"))

    record = db.session.get(ServiceRecord, record_id)
    if record is None:
        abort(404)

    organization = Organization.query.filter_by(
        name=record.organization_name
    ).first()

    if organization is None:
        abort(404)

    membership = OrganizationMember.query.filter_by(
        user_id=user_id,
        organization_id=organization.id
    ).first()

    if membership is None or membership.role not in ("owner", "admin"):
        abort(403)

    decision = request.form.get("decision")

    if decision == "approve":
        record.status = "verified"
        flash("Hours approved", "info")
    elif decision == "deny":
        record.status = "denied"
        flash("Hours denied", "info")
    else:
        abort(400)

    db.session.commit()

    return redirect(url_for(
        "organizations.organization_details",
        organization_id=organization.id
    ))


@organizations_bp.route("/organizations/<int:organization_id>/profile/edit", methods=["POST"])
def edit_organization_profile(organization_id):
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("auth.login"))

    organization = db.get_or_404(Organization, organization_id)

    owner = OrganizationMember.query.filter_by(
        user_id=user_id,
        organization_id=organization.id,
        role="owner"
    ).first()

    if owner is None:
        abort(403)

    name = request.form.get("name", "").strip()
    cause = request.form.get("cause", "").strip()
    location = request.form.get("location", "").strip()
    contact_email = request.form.get("contact_email", "").strip()
    description = request.form.get("description", "").strip()
    image = request.files.get("image")

    if not all((name, cause, location, contact_email, description)):
        return "Please complete all required fields.", 400

    if (
        len(name) > 70
        or len(cause) > 500
        or len(location) > 150
        or len(contact_email) > 50
        or len(description) > 1000
    ):
        return "One or more fields are too long.", 400

    name_taken = Organization.query.filter(
        Organization.name == name,
        Organization.id != organization.id
    ).first()

    if name_taken:
        return "An organization with that name already exists.", 400

    email_taken = Organization.query.filter(
        Organization.email == contact_email,
        Organization.id != organization.id
    ).first()

    if email_taken:
        return "That contact email is already in use.", 400

    new_image_filename = None

    if image and image.filename:
        safe_name = secure_filename(image.filename)
        extension = os.path.splitext(safe_name)[1].lower()

        if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
            return "Please upload a PNG, JPG, or WEBP image.", 400

        new_image_filename = f"{uuid4().hex}{extension}"
        os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)

        image.save(
            os.path.join(
                current_app.config["UPLOAD_FOLDER"],
                new_image_filename
            )
        )

    old_name = organization.name

    if name != old_name:
        for opportunity in organization.opportunities:
            opportunity.organization_name = name

        for record in ServiceRecord.query.filter_by(
            organization_name=old_name
        ).all():
            record.organization_name = name

    organization.name = name
    organization.cause = cause
    organization.location = location
    organization.email = contact_email
    organization.description = description

    if new_image_filename:
        organization.image_filename = new_image_filename

    db.session.commit()

    flash("Organization profile updated.", "success")
    return redirect(url_for(
        "organizations.organization_details",
        organization_id=organization.id
    ))


@organizations_bp.route("/organization-members/<int:membership_id>/remove", methods=["POST"])
def remove_admin(membership_id):
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("auth.login"))

    membership = db.get_or_404(OrganizationMember, membership_id)

    owner = OrganizationMember.query.filter_by(
        user_id=user_id,
        organization_id=membership.organization_id,
        role="owner"
    ).first()

    if owner is None:
        abort(403)

    if membership.role != "admin":
        abort(400)

    organization_id = membership.organization_id
    db.session.delete(membership)
    db.session.commit()

    flash("Removed admin", "info")
    return redirect(url_for(
        "organizations.organization_details",
        organization_id=organization_id
    ))


def review_volunteer_signup(signup_id, decision):
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("auth.login"))

    signup = db.session.get(OpportunitySignups, signup_id)
    if signup is None:
        abort(404)

    opportunity = signup.opportunity

    membership = OrganizationMember.query.filter_by(
        user_id=user_id,
        organization_id=opportunity.organization_id
    ).first()

    if membership is None or membership.role not in ("owner", "admin"):
        abort(403)

    if signup.status not in ("pending", "waitlisted"):
        flash("This request has already been reviewed.")
        return redirect(url_for(
            "organizations.organization_details",
            organization_id=opportunity.organization_id
        ))

    if decision == "approved":
        approved_count = OpportunitySignups.query.filter_by(
            opportunity_id=opportunity.id,
            status="approved"
        ).count()

        if approved_count >= opportunity.volunteer_requirement:
            signup.status = "waitlisted"
            db.session.commit()
            flash("All spots are filled. This volunteer is now waitlisted.", "info")

            return redirect(url_for(
                "organizations.organization_details",
                organization_id=opportunity.organization_id
            ))

        start = datetime.combine(
            opportunity.event_date,
            opportunity.start_time
        )
        end = datetime.combine(
            opportunity.event_date,
            opportunity.end_time
        )

        if end <= start:
            flash("The opportunity's end time must be after its start time.")
            return redirect(url_for(
                "organizations.organization_details",
                organization_id=opportunity.organization_id
            ))

        existing_record = ServiceRecord.query.filter_by(
            user_id=signup.user_id,
            organization_name=opportunity.organization_name,
            opportunity_title=opportunity.title,
            event_date=opportunity.event_date
        ).first()

        if existing_record is None:
            record = ServiceRecord(
                organization_name=opportunity.organization_name,
                opportunity_title=opportunity.title,
                event_date=opportunity.event_date,
                start_time=opportunity.start_time,
                end_time=opportunity.end_time,
                timezone=opportunity.timezone,
                location=opportunity.location,
                description=opportunity.activities,
                status="unverified",
                user_id=signup.user_id
            )
            db.session.add(record)

        signup.status = "approved"
        flash("Volunteer approved.", "info")

    elif decision == "denied":
        signup.status = "denied"
        flash("Volunteer request denied.", "info")

    else:
        abort(400)

    db.session.commit()

    return redirect(url_for(
        "organizations.organization_details",
        organization_id=opportunity.organization_id
    ))


@organizations_bp.route("/signups/<int:signup_id>/approve", methods=["POST"])
def approve_volunteer(signup_id):
    return review_volunteer_signup(signup_id, "approved")


@organizations_bp.route("/signups/<int:signup_id>/deny", methods=["POST"])
def deny_volunteer(signup_id):
    return review_volunteer_signup(signup_id, "denied")


@organizations_bp.route("/search-organizations")
def search_organizations():
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)

    if user is None:
        session.pop("user_id", None)
        return redirect(url_for("auth.login"))

    query_text = request.args.get("q", "").strip()[:100]
    organizations_query = Organization.query

    if query_text:
        term = f"%{query_text}%"

        organizations_query = organizations_query.filter(
            or_(
                Organization.name.ilike(term),
                Organization.cause.ilike(term),
                Organization.location.ilike(term),
                Organization.description.ilike(term),
            )
        )

    organizations = organizations_query.order_by(
        Organization.name.asc()
    ).all()

    return render_template(
        "organization_search.html",
        user=user,
        organizations=organizations,
        query_text=query_text
    )


@organizations_bp.route("/organizations/<int:organization_id>")
def view_organization(organization_id):
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)

    if user is None:
        session.pop("user_id", None)
        return redirect(url_for("auth.login"))

    organization = db.get_or_404(Organization, organization_id)

    membership = OrganizationMember.query.filter_by(
        user_id=user.id,
        organization_id=organization.id
    ).first()

    admin_request = OrganizationAdminRequest.query.filter_by(
        user_id=user.id,
        organization_id=organization.id
    ).first()

    opportunity_count = Opportunity.query.filter_by(
        organization_id=organization.id
    ).count()

    open_opportunities = (
        Opportunity.query
        .filter_by(
            organization_id=organization.id,
            status="open"
        )
        .order_by(Opportunity.event_date.asc())
        .limit(3)
        .all()
    )

    return render_template(
        "view_organization.html",
        user=user,
        organization=organization,
        membership=membership,
        admin_request=admin_request,
        opportunity_count=opportunity_count,
        open_opportunities=open_opportunities
    )


@organizations_bp.route("/organizations/<int:organization_id>/apply-admin", methods=["POST"])
def apply_to_be_admin(organization_id):
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    if db.session.get(User, user_id) is None:
        session.pop("user_id", None)
        return redirect(url_for("auth.login"))

    organization = db.get_or_404(Organization, organization_id)

    profile_url = url_for(
        "organizations.view_organization",
        organization_id=organization.id
    )

    membership = OrganizationMember.query.filter_by(
        user_id=user_id,
        organization_id=organization.id
    ).first()

    if membership is not None:
        flash("You already have a role in this organization.", "info")
        return redirect(profile_url)

    admin_request = OrganizationAdminRequest.query.filter_by(
        user_id=user_id,
        organization_id=organization.id
    ).first()

    if admin_request is None:
        admin_request = OrganizationAdminRequest(
            user_id=user_id,
            organization_id=organization.id,
            status="pending"
        )
        db.session.add(admin_request)

    elif admin_request.status == "pending":
        flash("Your application is already awaiting review.", "info")
        return redirect(profile_url)

    elif admin_request.status == "approved":
        flash("Your application was already approved.", "info")
        return redirect(profile_url)

    else:
        admin_request.status = "pending"

    db.session.commit()

    flash("Application sent. The organization owner will review it.", "success")
    return redirect(profile_url)


@organizations_bp.route("/organizations/<int:organization_id>/admin-requests/<int:request_id>/review", methods=["POST"])
def review_admin_request(organization_id, request_id):
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    owner = OrganizationMember.query.filter_by(
        user_id=user_id,
        organization_id=organization_id,
        role="owner"
    ).first()

    if owner is None:
        abort(403)

    admin_request = db.get_or_404(
        OrganizationAdminRequest,
        request_id
    )

    if admin_request.organization_id != organization_id:
        abort(404)

    profile_url = url_for(
        "organizations.view_organization",
        organization_id=organization_id
    )

    if admin_request.status != "pending":
        flash("This application has already been reviewed.")
        return redirect(profile_url)

    decision = request.form.get("decision")

    if decision == "approve":
        membership = OrganizationMember.query.filter_by(
            user_id=admin_request.user_id,
            organization_id=organization_id
        ).first()

        if membership is None:
            db.session.add(
                OrganizationMember(
                    admin_request.user_id,
                    organization_id,
                    "admin"
                )
            )

        admin_request.status = "approved"
        flash("Admin application approved.", "info")

    elif decision == "deny":
        admin_request.status = "denied"
        flash("Admin application denied.", "info")

    else:
        abort(400)

    db.session.commit()

    return redirect(url_for(
        "organizations.organization_details",
        organization_id=organization_id
    ))