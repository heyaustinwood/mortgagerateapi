from flask import Blueprint, request, jsonify, render_template, abort
from .models import MortgageRate, Token
from .database import db
from datetime import datetime
from functools import wraps

main = Blueprint('main', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            abort(401, description="Token is required")

        token_obj = Token.query.filter_by(token=token).first()
        if not token_obj or token_obj.expiry < datetime.utcnow():
            abort(401, description="Invalid or expired token")

        return f(*args, **kwargs)
    return decorated

@main.route('/')
def home():
    return render_template('home.html')

@main.route('/mortgage_rate', methods=['GET'])
@token_required
def get_mortgage_rate():
    date_str = request.args.get('date')
    term = request.args.get('term')

    if not date_str or not term:
        return jsonify({"error": "Missing date or term parameter"}), 400

    try:
        date = datetime.strptime(date_str, '%Y%m%d').date()
        term = int(term)
    except ValueError:
        return jsonify({"error": "Invalid date format or term"}), 400

    if term not in [15, 30]:
        return jsonify({"error": "Term must be either 15 or 30"}), 400

    closest_rate = MortgageRate.query.filter(
        MortgageRate.term == term,
        MortgageRate.date <= date
    ).order_by(MortgageRate.date.desc()).first()

    if not closest_rate:
        return jsonify({"error": "No data available for the given date and term"}), 404

    return jsonify({
        "date": closest_rate.date.strftime('%Y-%m-%d'),
        "term": closest_rate.term,
        "rate": closest_rate.rate
    })

@main.route('/get_token', methods=['POST', 'GET'])
def get_token():
    token = Token.generate_token()
    return jsonify({"token": token.token, "expiry": token.expiry.isoformat()})

@main.route('/revoke_token', methods=['POST'])
@token_required
def revoke_token():
    token = request.args.get('token')
    Token.query.filter_by(token=token).delete()
    db.session.commit()
    return jsonify({"message": "Token revoked successfully"})

@main.errorhandler(401)
def unauthorized(error):
    return jsonify({"error": "Unauthorized", "message": error.description}), 401