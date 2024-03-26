from flask import Flask, send_from_directory
import logging
from flask_sqlalchemy import SQLAlchemy
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set logging level to INFO

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

database_url = os.environ.get('DATABASE_URL')
logging.info(f'DATABASE_URL: {database_url}')  # Log the retrieved DATABASE_URL

# Configure the database URI from the environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')


# Suppress deprecation warnings
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define a simple model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username

# Create the database tables (if they don't exist)
db.create_all()

# Define a route to return all users as JSON
@app.route('/users', methods=['GET'])
def get_users():
    all_users = User.query.all()
    users_list = [{'id': user.id, 'username': user.username} for user in all_users]
    return jsonify(users_list)

# Define a route to add a new user
@app.route('/users', methods=['POST'])
def add_user():
    data = request.get_json()
    if 'username' not in data:
        return jsonify({'error': 'Username is required'}), 400

    username = data['username']
    new_user = User(username=username)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User added successfully', 'username': username}), 201


@app.route('/')
def index():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)
