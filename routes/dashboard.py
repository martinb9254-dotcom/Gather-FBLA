from flask import Blueprint, redirect, render_template, request, session, url_for
from extensions import db
from decimal import Decimal
from models import (
    SavedOpportunities, OpportunitySignups,
    ServiceRecord, User, Opportunity)

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
def dashboard():
    user = db.session.get(User, session["user_id"])
    saved_entries = SavedOpportunities.query.filter_by(user_id=user.id).all()
    hours = ServiceRecord.query.filter_by(user_id=user.id)
    verified_hours = sum((record.hours for record in hours if record.status == "verified"), Decimal("0.00"))
    pending_hours = sum((record.hours for record in hours if record.status.lower() == "unverified"),Decimal("0.00"))
    upcoming_events = OpportunitySignups.query.join(OpportunitySignups.opportunity).filter(OpportunitySignups.user_id == user.id).order_by(Opportunity.event_date.asc(), Opportunity.start_time.asc()).all()
    return render_template("dashboard.html", user=user, hours=list(hours), verified_hours=verified_hours, pending_hours=pending_hours, saved_entries=list(saved_entries), upcoming_events=list(upcoming_events))

