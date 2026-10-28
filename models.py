
from datetime import datetime
from decimal import Decimal

from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), unique=True, nullable=False)
    firstname = db.Column(db.String(30), nullable=False)
    lastname = db.Column(db.String(30), nullable=False)
    phonenumber = db.Column(db.String(30))
    password_hash = db.Column(db.String(225), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    organization_memberships = db.relationship("OrganizationMember", back_populates="user")
    signups = db.relationship("OpportunitySignups", back_populates="user")
    service_records = db.relationship("ServiceRecord", back_populates="user")
    saved_opportunities = db.relationship("SavedOpportunities", back_populates="user")
    admin_requests = db.relationship("OrganizationAdminRequest", back_populates="user")

    def __init__(self, email, firstname, lastname, password, age, phonenumber=None):
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.age = age
        self.phonenumber = phonenumber
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Opportunity(db.Model):
    __tablename__ = "opportunities"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    cause = db.Column(db.String(100), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    timezone = db.Column(db.String(64), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    volunteer_requirement = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(1200), nullable=False)
    activities = db.Column(db.String(1200), nullable=False)
    materials = db.Column(db.String(1200), nullable=False)
    minimum_age = db.Column(db.Integer, nullable=True)
    image_filename = db.Column(db.String(255))
    status = db.Column(db.String(50))
    organization_name = db.Column(db.String(70), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    organization = db.relationship("Organization", back_populates="opportunities")
    signups = db.relationship("OpportunitySignups", back_populates="opportunity")
    saved_entries = db.relationship("SavedOpportunities", back_populates="opportunity", cascade="all, delete-orphan")

    def __init__(self, title, cause, event_date, start_time, end_time, timezone, location, volunteer_requirement, description, activities, materials, organization_name, organization_id, minimum_age, image_filename=None, status="open"):
        self.title = title
        self.cause = cause
        self.event_date = event_date
        self.start_time = start_time
        self.end_time = end_time
        self.timezone = timezone
        self.location = location
        self.volunteer_requirement = volunteer_requirement
        self.description = description
        self.activities = activities
        self.materials = materials
        self.organization_name = organization_name
        self.organization_id = organization_id
        self.image_filename = image_filename
        self.status = status
        self.minimum_age = minimum_age
        

class Organization(db.Model):
    __tablename__ = "organizations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(70), unique=True, nullable=False)
    cause = db.Column(db.String(500), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    location = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    image_filename = db.Column(db.String(255))
    opportunities = db.relationship("Opportunity", back_populates="organization")
    members = db.relationship("OrganizationMember", back_populates="organization")
    signups = db.relationship("OpportunitySignups", back_populates="organization")
    admin_requests = db.relationship("OrganizationAdminRequest", back_populates="organization")

    def __init__(self, name, cause, email, location, description, image_filename=None):
        self.name = name
        self.cause = cause
        self.email = email
        self.location = location
        self.description = description
        self.image_filename = image_filename


class OrganizationMember(db.Model):
    __tablename__ = "organization_members"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    role = db.Column(db.String(25), nullable=False)
    organization = db.relationship("Organization", back_populates="members")
    user = db.relationship("User", back_populates="organization_memberships")
    def __init__(self, user_id, organization_id, role):
        self.user_id = user_id
        self.organization_id = organization_id
        self.role = role

class OpportunitySignups(db.Model):
    __tablename__= "opportunity_signups"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey("opportunities.id"), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    status = db.Column(db.String(25), nullable=False)
    user = db.relationship("User", back_populates="signups")
    opportunity = db.relationship("Opportunity", back_populates="signups")
    organization = db.relationship("Organization", back_populates="signups")

class ServiceRecord(db.Model):
    __tablename__= "service_record"
    id = db.Column(db.Integer, primary_key=True)
    organization_name = db.Column(db.String(70), nullable=False)
    opportunity_title = db.Column(db.String(100), nullable=False)
    hours = db.Column(db.Numeric(5, 2), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    timezone = db.Column(db.String(64), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500))
    status = db.Column(db.String(25), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", back_populates="service_records")
    def __init__(self, organization_name, opportunity_title, event_date, start_time, end_time, timezone, location, status, user_id, description=None):
        self.organization_name = organization_name
        self.opportunity_title = opportunity_title

        start = datetime.combine(event_date, start_time)
        end = datetime.combine(event_date, end_time)
        seconds = (end - start).total_seconds()
        self.hours = (Decimal(str(seconds)) / Decimal("3600")).quantize(Decimal("0.01"))

        self.event_date = event_date
        self.start_time = start_time
        self.end_time = end_time
        self.timezone = timezone
        self.location = location
        self.description = description
        self.status = status
        self.user_id = user_id
    
class SavedOpportunities(db.Model):
    __tablename__ = "saved_opportunities"
    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey("opportunities.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User", back_populates="saved_opportunities")
    opportunity = db.relationship("Opportunity", back_populates="saved_entries")

class OrganizationAdminRequest(db.Model):
    __tablename__ = "organization_admin_requests"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False)
    status = db.Column(db.String(25), nullable=False, default="pending")
    user = db.relationship("User", back_populates="admin_requests")
    organization = db.relationship("Organization", back_populates="admin_requests")
