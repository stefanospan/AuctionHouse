from flask import Flask, jsonify, request, send_from_directory
import logging
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime, timedelta

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
    password = db.Column(db.String(80), unique=False, nullable=False)
    currency = db.Column(db.Float, nullable=False, default=0.0)

    def __repr__(self):
        return '<User %r>' % self.username

class UserInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return '<UserInventory %r>' % self.id

# Define Auction model
class Auction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # User who created the auction
    item_id = db.Column(db.Integer, nullable=False)
    start_price = db.Column(db.Float, nullable=False)
    current_bid = db.Column(db.Float, nullable=False)  # Add current_bid attribute
    quantity = db.Column(db.Integer, nullable=False, default=1)  # Amount of items in auction
    expiry_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Auction {self.id}>'

# Create the database tables (if they don't exist)
db.create_all()

# Route to add currency to a user
@app.route('/users/<int:user_id>/currency/add', methods=['POST'])
def add_currency(user_id):
    data = request.get_json()
    amount = data.get('amount')

    if amount is None:
        return jsonify({'error': 'Amount is required'}), 400

    try:
        user = User.query.get_or_404(user_id)
        user.currency += amount
        db.session.commit()
        return jsonify({'message': f'{amount} currency added successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Route to remove currency from a user
@app.route('/users/<int:user_id>/currency/remove', methods=['POST'])
def remove_currency(user_id):
    data = request.get_json()
    amount = data.get('amount')

    if amount is None:
        return jsonify({'error': 'Amount is required'}), 400

    try:
        user = User.query.get_or_404(user_id)
        if user.currency < amount:
            return jsonify({'error': 'Not enough currency to remove'}), 400
        user.currency -= amount
        db.session.commit()
        return jsonify({'message': f'{amount} currency removed successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Route to completely destroy the auctions database
@app.route('/auctions/clear', methods=['DELETE'])
def clear_auctions():
    try:
        # Delete all records from the Auction table
        db.session.query(Auction).delete()
        db.session.commit()
        return jsonify({'message': 'All auctions deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Route to delete the entire auction database
@app.route('/auctions/delete_database', methods=['DELETE'])
def delete_auction_database():
    try:
        # Drop all tables
        db.drop_all()

        # Delete the database itself
        db.engine.execute(f"DROP DATABASE {db.engine.url.database}")

        return jsonify({'message': 'Auction database deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route to set currency for a user
@app.route('/users/<int:user_id>/currency/set', methods=['POST'])
def set_currency(user_id):
    data = request.get_json()
    amount = data.get('amount')

    if amount is None:
        return jsonify({'error': 'Amount is required'}), 400

    try:
        user = User.query.get_or_404(user_id)
        user.currency = amount
        db.session.commit()
        return jsonify({'message': f'Currency set to {amount} successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Route to create a new auction bid
@app.route('/auctions', methods=['POST'])
def create_bid():
    data = request.get_json()

    # Extract data from request JSON
    user_id = data.get('user_id')  # Assuming user_id is provided
    item_id = data.get('item_id')
    start_price = data.get('start_price')
    quantity = data.get('quantity', 1)  # Default to 1 item if quantity is not provided
    expiry_hours = data.get('expiry_hours')  # Expiry time in hours

    if not all([user_id, item_id, start_price, expiry_hours]):
        return jsonify({'error': 'Incomplete data provided'}), 400

    try:
        # Check if the creator has enough quantity of the item
        creator_inventory = UserInventory.query.filter_by(user_id=user_id, item_id=item_id).first()
        if creator_inventory is None or creator_inventory.quantity < quantity:
            return jsonify({'error': 'Creator does not have enough quantity of the item'}), 400

        # Calculate expiry time
        current_time = datetime.now()
        expiry_time = current_time + timedelta(hours=expiry_hours)

        # Create new auction entry
        new_auction = Auction(
            user_id=user_id,
            item_id=item_id,
            start_price=start_price,
            current_bid=start_price,  # Initialize current_bid with start_price
            quantity=quantity,
            expiry_time=expiry_time
        )

        # Reduce quantity from creator's inventory
        creator_inventory.quantity -= quantity

        db.session.add(new_auction)
        db.session.commit()

        return jsonify({'message': 'Auction bid created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Route to place a bid on an existing auction
@app.route('/auctions/<int:auction_id>/bid', methods=['POST'])
def place_bid(auction_id):
    data = request.get_json()

    # Extract data from request JSON
    bidder_id = data.get('bidder_id')  # Assuming bidder_id is provided
    amount = data.get('amount')

    if not all([bidder_id, amount]):
        return jsonify({'error': 'Incomplete data provided'}), 400

    try:
        # Retrieve the auction
        auction = Auction.query.get_or_404(auction_id)

        # Check if the bidder has enough currency
        bidder = User.query.get_or_404(bidder_id)
        if bidder.currency < amount:
            return jsonify({'error': 'Not enough currency to place bid'}), 400

        # Check if the auction has expired
        if auction.expiry_time < datetime.now():
            return jsonify({'error': 'Auction has expired, cannot place bid'}), 400

        # Check if the bid amount is higher than the current bid
        if amount <= auction.current_bid:
            return jsonify({'error': 'Bid amount must be higher than current bid'}), 400

        # Reduce bidder's currency and update the auction with the new bid
        bidder.currency -= amount
        auction.user_id = bidder_id
        auction.current_bid = amount
        db.session.commit()

        return jsonify({'message': 'Bid placed successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Route to retrieve all auctions
@app.route('/auctions', methods=['GET'])
def get_auctions():
    try:
        # Retrieve all auctions from the database
        all_auctions = Auction.query.all()

        # Prepare the response data
        auctions_list = []
        for auction in all_auctions:
            auction_data = {
                'id': auction.id,
                'user_id': auction.user_id,
                'item_id': auction.item_id,
                'start_price': auction.start_price,
                'current_bid': auction.current_bid,
                'quantity': auction.quantity,
                'expiry_time': auction.expiry_time.strftime('%Y-%m-%d %H:%M:%S')
            }
            auctions_list.append(auction_data)

        return jsonify(auctions_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Routes for user inventory
@app.route('/users/<int:user_id>/inventory', methods=['GET'])
def get_user_inventory(user_id):
    user = User.query.get_or_404(user_id)
    inventory = UserInventory.query.filter_by(user_id=user_id).all()
    inventory_list = [{'item_id': item.item_id, 'quantity': item.quantity} for item in inventory]
    return jsonify(inventory_list)

# Route to add item to user inventory
@app.route('/users/<int:user_id>/inventory', methods=['POST'])
def add_item_to_inventory(user_id):
    data = request.get_json()
    if 'item_id' not in data:
        return jsonify({'error': 'Item ID is required'}), 400

    if 'quantity' not in data:
        return jsonify({'error': 'Quantity is required'}), 400

    item_id = data['item_id']
    quantity = data['quantity']

    # Check if the user exists
    user = User.query.get_or_404(user_id)

    # Add item to user inventory
    user_inventory = UserInventory.query.filter_by(user_id=user_id, item_id=item_id).first()
    if user_inventory:
        # Item already exists in user inventory, update quantity
        user_inventory.quantity += quantity
    else:
        # Item doesn't exist in user inventory, create new entry
        user_inventory = UserInventory(user_id=user_id, item_id=item_id, quantity=quantity)
        db.session.add(user_inventory)

    db.session.commit()

    return jsonify({'message': 'Item added to inventory successfully', 'item_id': item_id, 'quantity': quantity}), 201

# Route to remove item(s) from user inventory
@app.route('/users/<int:user_id>/inventory/<int:item_id>', methods=['DELETE'])
def remove_item_from_inventory(user_id, item_id):
    data = request.get_json()
    if 'amount' not in data:
        return jsonify({'error': 'Amount is required'}), 400

    amount = data['amount']

    # Check if the user exists
    user = User.query.get_or_404(user_id)

    # Check if the item exists in user inventory
    user_inventory = UserInventory.query.filter_by(user_id=user_id, item_id=item_id).first()
    if user_inventory:
        # Item found, remove specified amount from quantity
        if user_inventory.quantity > amount:
            user_inventory.quantity -= amount
            db.session.commit()
            return jsonify({'message': f'{amount} item(s) removed from inventory successfully', 'item_id': item_id}), 200
        elif user_inventory.quantity == amount:
            # If the quantity matches the amount, delete the entry
            db.session.delete(user_inventory)
            db.session.commit()
            return jsonify({'message': f'All items removed from inventory successfully', 'item_id': item_id}), 200
        else:
            return jsonify({'error': 'Amount exceeds the quantity in inventory'}), 400
    else:
        # Item not found in user inventory
        return jsonify({'error': 'Item not found in user inventory'}), 404

# Route to update entire inventory of a user
@app.route('/users/<int:user_id>/inventory', methods=['PUT'])
def update_user_inventory(user_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Check if the user exists
    user = User.query.get_or_404(user_id)

    try:
        # Clear user's current inventory
        UserInventory.query.filter_by(user_id=user_id).delete()

        # Add items from provided data
        for item_data in data:
            if 'item_id' not in item_data or 'quantity' not in item_data:
                return jsonify({'error': 'Item ID and quantity are required for each item'}), 400

            item_id = item_data['item_id']
            quantity = item_data['quantity']

            # Add item to user inventory
            user_inventory = UserInventory(user_id=user_id, item_id=item_id, quantity=quantity)
            db.session.add(user_inventory)

        db.session.commit()
        return jsonify({'message': 'User inventory updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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

    if 'password' not in data:
        return jsonify({'error': 'Password is required'}), 400

    username = data['username']
    password = data['password']
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User added successfully', 'username': username}), 201

# Define a route to clear the user database
@app.route('/users/clear', methods=['DELETE'])
def clear_users():
    try:
        # Delete all records from the User table
        db.session.query(User).delete()
        db.session.commit()
        return jsonify({'message': 'All users deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

        # Define a route to reset the database
@app.route('/reset_database', methods=['POST'])
def reset_database():
    try:
        # Drop all tables
        db.drop_all()

        # Recreate all tables
        db.create_all()

        return jsonify({'message': 'Database reset successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

        # Define a route for user login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Both username and password are required'}), 400

    username = data['username']
    password = data['password']

    # Check if the user exists
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({'error': 'Invalid username or password'}), 401

    # Check if the password is correct
    if user.password != password:
        return jsonify({'error': 'Invalid username or password'}), 401

    return jsonify({'message': 'Login successful', 'username': username}), 200

@app.route('/')
def index():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)
