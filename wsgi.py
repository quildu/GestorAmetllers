from scripts.app import app, seed_data
from scripts.database import init_db

init_db()
seed_data()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
