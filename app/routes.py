from flask import Blueprint, render_template, redirect, url_for, session, request
from .models import db, User, ServerOnboarding
from .auth import requires_auth, oauth

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)

@main.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(auth0_id=session['user']['sub']).first()
    if not user:
        return redirect(url_for('auth.callback'))
        
    # Prüfe ob Server-Onboarding bereits ausgefüllt wurde
    onboarding = ServerOnboarding.query.filter_by(user_id=user.id).first()
    if onboarding:
        return redirect(url_for('main.mein_konto'))
    
    return redirect(url_for('main.server_onboarding'))

@auth.route('/login')
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for('auth.callback', _external=True)
    )

@auth.route('/callback')
def callback():
    token = oauth.auth0.authorize_access_token()
    session['user'] = token
    
    # User in Datenbank speichern/updaten
    user = User.query.filter_by(auth0_id=token['sub']).first()
    if not user:
        user = User(
            auth0_id=token['sub'],
            email=token['email']
        )
        db.session.add(user)
        db.session.commit()
    
    return redirect(url_for('main.home'))

@auth.route('/logout')
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("main.home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

@main.route('/server-onboarding', methods=['GET', 'POST'])
@requires_auth
def server_onboarding():
    if request.method == 'POST':
        user = User.query.filter_by(auth0_id=session['user']['sub']).first()
        
        onboarding = ServerOnboarding(
            user_id=user.id,
            order_number=user.order_number,
            ip_address=request.form['ip_address'],
            hoster=request.form['hoster'],
            custom_hoster=request.form.get('custom_hoster')
        )
        db.session.add(onboarding)
        db.session.commit()
        
        return redirect(url_for('main.mein_konto'))
        
    return render_template('onboarding.html')

@main.route('/mein-konto')
@requires_auth
def mein_konto():
    return render_template('mein_konto.html')