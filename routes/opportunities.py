from flask import Blueprint, render_template, session, redirect, request, url_for, current_app, flash, abort
from extensions import db
from models import (
    Opportunity, OpportunitySignups, SavedOpportunities,
    User, Organization, OrganizationMember,
)
import os
import os
from datetime import date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from uuid import uuid4

from flask import (
    Blueprint, abort, current_app, flash, redirect, render_template,
    request, session, url_for,
)
from werkzeug.utils import secure_filename

from extensions import db
from models import (
    Opportunity, OpportunitySignups, Organization, OrganizationMember,
    SavedOpportunities, User,
)


opportunities_bp = Blueprint("opportunities", __name__)


def event_start_error(event_date, start_time, timezone):
    try:
        event_zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        return "Please enter a valid time zone."

    event_start = datetime.combine(
        event_date,
        start_time,
        tzinfo=event_zone
    )

    if event_start <= datetime.now(event_zone):
        return "Choose a start date and time in the future."

    return None


def require_org_manager(organization_id):
    user_id = session.get("user_id")
    if user_id is None:
        abort(401)

    membership = OrganizationMember.query.filter_by(
        user_id=user_id,
        organization_id=organization_id
    ).first()

    if membership is None or membership.role not in ("owner", "admin"):
        abort(403)


@opportunities_bp.route(
    "/opportunities/<int:opportunity_id>/unsave",
    methods=["POST"]
)
def unsave_opportunity(opportunity_id):
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)

    if user is None:
        session.pop("user_id", None)
        return redirect(url_for("auth.login"))

    saved_entry = SavedOpportunities.query.filter_by(
        user_id=user.id,
        opportunity_id=opportunity_id
    ).first()

    if saved_entry is not None:
        db.session.delete(saved_entry)
        db.session.commit()
        flash("Opportunity removed from saved.", "info")

    if request.form.get("source") == "dashboard":
        return redirect(url_for("dashboard.dashboard"))

    return redirect(
        url_for(
            "opportunities.view_opportunity",
            opportunity_id=opportunity_id
        )
    )


@opportunities_bp.post("/opportunities/<int:opportunity_id>/save")
def save_opportunity(opportunity_id):
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)

    if user is None:
        session.pop("user_id", None)
        return redirect(url_for("auth.login"))

    db.get_or_404(Opportunity, opportunity_id)

    existing = SavedOpportunities.query.filter_by(
        user_id=user.id,
        opportunity_id=opportunity_id
    ).first()

    if existing is None:
        saved = SavedOpportunities(
            user_id=user.id,
            opportunity_id=opportunity_id
        )
        db.session.add(saved)
        db.session.commit()
        flash("Opportunity saved for later.", "success")

    return redirect(
        url_for(
            "opportunities.view_opportunity",
            opportunity_id=opportunity_id
        )
    )


@opportunities_bp.route("/search-opportunites")
def search_opportunities():
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)

    if user is None:
        session.pop("user_id", None)
        return redirect(url_for("auth.login"))

    opportunities = (
        Opportunity.query
        .order_by(Opportunity.event_date.asc())
        .all()
    )

    return render_template(
        "opportunities_search.html",
        opportunities=opportunities,
        user=user
    )


@opportunities_bp.route(
    "/organizations/<int:organization_id>/opportunities/create",
    methods=["POST"]
)
def create_opportunity(organization_id):
    organization = db.get_or_404(Organization, organization_id)
    require_org_manager(organization.id)

    title = request.form["title"].strip()
    cause = request.form["cause"].strip()
    location = request.form["location"].strip()
    timezone = request.form["timezone"].strip()
    summary = request.form["summary"].strip()
    activities = request.form["description"].strip()
    materials = request.form["materials"].strip()

    event_date = date.fromisoformat(request.form["date"])
    start_time = time.fromisoformat(request.form["start_time"])
    end_time = time.fromisoformat(request.form["end_time"])
    capacity = int(request.form["capacity"])

    if end_time <= start_time:
        flash("End time must be after start time.", "danger")
        return redirect(
            url_for(
                "organizations.organization_details",
                organization_id=organization.id
            )
        )

    if event_date < date.today():
        flash("Choose today or a future date for the opportunity.", "danger")
        return redirect(
            url_for(
                "organizations.organization_details",
                organization_id=opportunity.organization_id
            )
        )

    minimum_age_text = request.form.get("minimum_age", "").strip()
    minimum_age = int(minimum_age_text) if minimum_age_text else None

    image_filename = None
    image = request.files.get("image")

    if image and image.filename:
        safe_name = secure_filename(image.filename)
        extension = os.path.splitext(safe_name)[1].lower()

        if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
            return "Please upload a PNG, JPG, or WEBP image.", 400

        image_filename = f"{uuid4().hex}{extension}"
        image.save(
            os.path.join(
                current_app.config["UPLOAD_FOLDER"],
                image_filename
            )
        )

    opportunity = Opportunity(
        title=title,
        cause=cause,
        event_date=event_date,
        start_time=start_time,
        end_time=end_time,
        timezone=timezone,
        location=location,
        volunteer_requirement=capacity,
        description=summary,
        activities=activities,
        materials=materials,
        organization_name=organization.name,
        organization_id=organization.id,
        minimum_age=minimum_age,
        image_filename=image_filename,
        status="open"
    )

    db.session.add(opportunity)
    db.session.commit()

    flash("Opportunity created.", "success")
    return redirect(
        url_for(
            "organizations.organization_details",
            organization_id=organization.id
        )
    )


@opportunities_bp.route(
    "/opportunities/<int:opportunity_id>/edit",
    methods=["POST"]
)
def edit_opportunity(opportunity_id):
    opportunity = db.get_or_404(Opportunity, opportunity_id)
    require_org_manager(opportunity.organization_id)

    event_date = date.fromisoformat(request.form["event_date"])
    start_time = time.fromisoformat(request.form["start_time"])
    end_time = time.fromisoformat(request.form["end_time"])
    timezone = request.form["timezone"].strip()

    if end_time <= start_time:
        flash("End time must be after start time.", "danger")
        return redirect(
            url_for(
                "organizations.organization_details",
                organization_id=opportunity.organization_id
            )
        )

    if event_date < date.today():
        flash("Choose today or a future date for the opportunity.", "danger")
        return redirect(
            url_for(
                "organizations.organization_details",
                organization_id=opportunity.organization_id
            )
        )

    minimum_age_text = request.form.get("minimum_age", "").strip()
    minimum_age = int(minimum_age_text) if minimum_age_text else None

    opportunity.title = request.form["title"].strip()
    opportunity.cause = request.form["cause"].strip()
    opportunity.minimum_age = minimum_age
    opportunity.status = request.form["status"]
    opportunity.event_date = event_date
    opportunity.start_time = start_time
    opportunity.end_time = end_time
    opportunity.timezone = timezone
    opportunity.location = request.form["location"].strip()
    opportunity.volunteer_requirement = int(
        request.form["volunteer_requirement"]
    )
    opportunity.description = request.form["description"].strip()
    opportunity.activities = request.form["activities"].strip()
    opportunity.materials = request.form["materials"].strip()

    image = request.files.get("image")

    if image and image.filename:
        safe_name = secure_filename(image.filename)
        extension = os.path.splitext(safe_name)[1].lower()

        if extension not in {".png", ".jpg", ".jpeg", ".webp"}:
            return "Please upload a PNG, JPG, or WEBP image.", 400

        image_filename = f"{uuid4().hex}{extension}"
        image.save(
            os.path.join(
                current_app.config["UPLOAD_FOLDER"],
                image_filename
            )
        )
        opportunity.image_filename = image_filename

    db.session.commit()

    flash("Opportunity updated.", "success")
    return redirect(
        url_for(
            "organizations.organization_details",
            organization_id=opportunity.organization_id
        )
    )


@opportunities_bp.route(
    "/opportunities/<int:opportunity_id>/delete",
    methods=["POST"]
)
def delete_opportunity(opportunity_id):
    opportunity = db.get_or_404(Opportunity, opportunity_id)
    require_org_manager(opportunity.organization_id)

    organization_id = opportunity.organization_id

    for signup in opportunity.signups:
        db.session.delete(signup)

    db.session.flush()
    db.session.delete(opportunity)
    db.session.commit()

    flash("Opportunity deleted.", "info")
    return redirect(
        url_for(
            "organizations.organization_details",
            organization_id=organization_id
        )
    )


@opportunities_bp.route("/opportunities/<int:opportunity_id>")
def view_opportunity(opportunity_id):
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)

    if user is None:
        session.pop("user_id", None)
        return redirect(url_for("auth.login"))

    opportunity = db.get_or_404(Opportunity, opportunity_id)

    saved_entry = SavedOpportunities.query.filter_by(
        user_id=user.id,
        opportunity_id=opportunity.id
    ).first()

    approved_count = OpportunitySignups.query.filter_by(
        opportunity_id=opportunity.id,
        status="approved"
    ).count()

    existing_signup = OpportunitySignups.query.filter_by(
        user_id=user.id,
        opportunity_id=opportunity.id
    ).first()

    return render_template(
        "view_opportunity.html",
        user=user,
        opportunity=opportunity,
        saved_entry=saved_entry,
        spots_left=max(
            0,
            opportunity.volunteer_requirement - approved_count
        ),
        existing_signup=existing_signup,
        event_has_passed=opportunity.event_date < date.today()
    )


@opportunities_bp.route(
    "/opportunities/<int:opportunity_id>/signup",
    methods=["POST"]
)
def signup_opportunity(opportunity_id):
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)

    if user is None:
        session.pop("user_id", None)
        return redirect(url_for("auth.login"))

    opportunity = db.get_or_404(Opportunity, opportunity_id)

    if opportunity.status != "open" or opportunity.event_date < date.today():
        flash("Signups for this opportunity are closed.", "warning")
        return redirect(
            url_for(
                "opportunities.view_opportunity",
                opportunity_id=opportunity.id
            )
        )

    approved_count = OpportunitySignups.query.filter_by(
        opportunity_id=opportunity.id,
        status="approved"
    ).count()

    status = (
        "waitlisted"
        if approved_count >= opportunity.volunteer_requirement
        else "pending"
    )

    signup = OpportunitySignups(
        user_id=user.id,
        opportunity_id=opportunity.id,
        organization_id=opportunity.organization.id,
        status=status
    )

    db.session.add(signup)
    db.session.commit()

    if status == "waitlisted":
        flash(
            f"You joined the waitlist for {opportunity.title}.",
            "info"
        )
    else:
        flash(
            f"Your signup for {opportunity.title} was sent for review.",
            "success"
        )

    return redirect(url_for("dashboard.dashboard"))


@opportunities_bp.post("/signups/<int:signup_id>/cancel")
def cancel_signup(signup_id):
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    signup = db.get_or_404(OpportunitySignups, signup_id)

    if signup.user_id != user_id:
        abort(403)

    if signup.status in {"pending", "approved", "waitlisted"}:
        signup.status = "cancelled"
        db.session.commit()
        flash(
            f"Signup cancelled for {signup.opportunity.title}.",
            "info"
        )

    return redirect(url_for("dashboard.dashboard"))