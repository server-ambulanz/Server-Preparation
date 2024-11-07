# app.py
from app import create_app
from waitress import serve

app = create_app()

if __name__ == '__main__':
    if app.config['ENV'] == 'development':
        app.run(host='0.0.0.0', port=5001, debug=True)
    else:
        serve(app, host='0.0.0.0', port=5001)

# wsgi.py
from app import create_app

app = create_app()