from flask import Flask, render_template, request, redirect, url_for, session, flash
import razorpay
import secret_key
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///registration.db"
# postgresql://postgresql:{{password}}@localhost/{{ database_name }}
db = SQLAlchemy(app)
admin_auth = False

class Data(db.Model):
    __tablename__ = "data"
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(100))
    order_id = db.Column(db.String(100))

    def __init__(self, payment_id, order_id):
        self.payment_id = payment_id
        self.order_id = order_id

    def __str__(self):
        return self.id


@app.route("/")
def home():
    return render_template("app.html")


@app.route("/pay", methods=["POST"])
def pay():
    global payment, name, units
    name = request.form.get("username")
    units = int(request.form.get("units"))
    client = razorpay.Client(auth=(secret_key.key_id, secret_key.key_secret))

    data = {"amount": units*50000, "currency": "INR", "receipt": "#11"}
    payment = client.order.create(data=data)
    user_dets = {
        "name": name,
        "email": request.form.get("email"),
        "ph_nm": request.form.get("contact"),
        "payment": payment
    }
    return render_template("pay.html", details=user_dets)


@app.route("/pay/fail")
def pay_failure():
    flash("Payment couldn't go through and failed due to some reason.")
    return redirect(url_for('home'))


@app.route("/pay/verify", methods=["GET", "POST"])
def pay_verify():
    client = razorpay.Client(auth=(secret_key.key_id, secret_key.key_secret))
    payment_id = request.form.get("payment_id")
    order_id = request.form.get("order_id")
    signature = request.form.get("signature")
    params_dict = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }
    # Try and expect block to save the details.
    res = client.utility.verify_payment_signature(params_dict)
    if not res:
        temp = Data(payment_id, order_id)
        db.session.add(temp)
        db.session.commit()

    data = {
        "order_id": order_id,
        "payment_id": payment_id,
        "status": res
    }
    return render_template('verification.html', data=data)


@app.route("/refund", methods=["POST"])
def refund():
    client = razorpay.Client(auth=(secret_key.key_id, secret_key.key_secret))
    payment_id = request.form.get('payment_id')
    resp = client.payment.fetch(payment_id)
    data = {
        "payment_id": payment_id,
        "amount": resp["amount"]
    }
    return render_template("refund.html", data=data)


@app.route("/refund/process", methods=["GET", "POST"])
def refund_process():
    client = razorpay.Client(auth=(secret_key.key_id, secret_key.key_secret))
    payment_id = request.form.get("payment_id")
    amount = int(request.form.get("amount"))
    reason = request.form.get("reason")
    if reason != "other":
        client.payment.refund(payment_id, amount*100)
        message = "Refund was initiated successfully!!"
    else:
        message = "Your refund will be reviewed and initiated once confirmed.."
    flash(message)
    return redirect(url_for("home"))


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    global admin_auth
    if admin_auth:
        return redirect(url_for("tracker"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == secret_key.admin_username and password == secret_key.admin_password:
            admin_auth = True
            return redirect(url_for("tracker"))
        else:
            flash("Credentials entered are not in admin database")
    return render_template("login.html")


@app.route("/logs")
def tracker():
    global admin_auth
    if admin_auth:
        queryset = Data.query.all()
        return render_template("transaction_tracker.html", dataset=queryset)
    else:
        return redirect(url_for("login"))


