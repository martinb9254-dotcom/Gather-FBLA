from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)

@public_bp.route("/")
def home():
    return render_template("home.html")


@public_bp.route("/how-it-works")
def how_it_works():
    return render_template("howitworks.html")
