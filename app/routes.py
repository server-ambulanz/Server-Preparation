from flask import Blueprint, render_template, request, jsonify
from app.models import db, ServerOnboarding
from flask_login import login_required, current_user

main = Blueprint('main', __name__)

HOSTERS = [
    'Contabo',
    '1&1',
    'Strato',
    'OVH',
    'Hetzner',
    'DigitalOcean',
    'AWS',
    'Google Cloud',
    'Microsoft Azure'
]

@main.route('/server-onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    if request.method == 'POST':
        data = request.json
        new_server = ServerOnboarding(
            ip_address=data['ip_address'],
            hoster=data['hoster'],
            custom_hoster=data.get('custom_hoster'),
            user_id=current_user.id
        )
        db.session.add(new_server)
        db.session.commit()
        return jsonify({'status': 'success'})
    
    return render_template('onboarding.html', hosters=sorted(HOSTERS))