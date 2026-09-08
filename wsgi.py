import os

from app import create_app, seed_data
from app.database import init_db

app = create_app()

init_db()
seed_data()

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', '0') == '1', host='0.0.0.0', port=5000)
