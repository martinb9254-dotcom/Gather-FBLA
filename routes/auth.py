from flask import Blueprint, redirect, render_template, request, session, url_for, flash
from extensions import db
from models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signout")
def signout():
    session.pop("user_id", None)
    return redirect(url_for("public.home"))


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        phonenumber = request.form.get("phonenumber")
        password = request.form.get("password")
        age = request.form.get("age")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user is None:
            user = User(email, firstname, lastname, password, age, phonenumber)
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            flash("Your account is ready. Welcome to Gather!", "success")
            return redirect(url_for("dashboard.dashboard"))
        else:
            flash("An account with that email already exists.", "danger")
            return render_template("signup.html")

    return render_template("signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard.dashboard"))
        else:
            flash("Incorrect email or password.", "danger")
            return render_template("login.html")        

    return render_template("login.html")

@auth_bp.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, user_id)

    if user is None:
        session.pop("user_id", None)
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        values = {
            "firstname": request.form.get("firstname", "").strip(),
            "lastname": request.form.get("lastname", "").strip(),
            "phonenumber": request.form.get("phonenumber", "").strip(),
            "age": request.form.get("age", "").strip(),
        }

        try:
            age = int(values["age"])
        except ValueError:
            age = None

        if (
            not values["firstname"]
            or not values["lastname"]
            or len(values["firstname"]) > 30
            or len(values["lastname"]) > 30
            or len(values["phonenumber"]) > 30
            or age is None
            or age < 1
            or age > 120
        ):
            flash("Please check your profile details and try again.", "danger")
            return render_template("edit_profile.html", user=user, values=values)

        user.firstname = values["firstname"]
        user.lastname = values["lastname"]
        user.phonenumber = values["phonenumber"] or None
        user.age = age

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("auth.edit_profile"))

    values = {
        "firstname": user.firstname,
        "lastname": user.lastname,
        "phonenumber": user.phonenumber or "",
        "age": user.age,
    }

    return render_template("edit_profile.html", user=user, values=values)