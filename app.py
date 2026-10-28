
import os
from flask import Flask
from extensions import db
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///gather.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(app.static_folder, "uploads")

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)

from routes.public import public_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.organizations import organizations_bp
from routes.opportunities import opportunities_bp

app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(organizations_bp)
app.register_blueprint(opportunities_bp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)