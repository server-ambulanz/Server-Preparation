from app import create_app
from waitress import serve
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()

app = create_app()

if __name__ == '__main__':
    # Prüfe die Umgebung über FLASK_ENV
    if os.getenv('FLASK_ENV') == 'development':
        app.run(host='0.0.0.0', port=5001, debug=True)
    else:
        serve(app, host='0.0.0.0', port=5001)