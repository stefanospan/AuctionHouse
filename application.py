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
#app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')


# Suppress deprecation warnings
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
#db = SQLAlchemy(app)

# Define a simple model
#class User(db.Model):
#    id = db.Column(db.Integer, primary_key=True)
#    username = db.Column(db.String(80), unique=True, nullable=False)

#    def __repr__(self):
#        return '<User %r>' % self.username

# Create the database tables (if they don't exist)
#db.create_all()

@app.route('/')
def index():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)
