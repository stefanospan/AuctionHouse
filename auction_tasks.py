from datetime import datetime, timedelta
import logging
from application import db, Auction, User, UserInventory  # Adjust import based on your project structure
from celery import Celery

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@Celery.task
def process_expired_auctions():
    """
    Task to process expired auctions.
    """
    current_time = datetime.now()
    expired_auctions = Auction.query.filter(Auction.expiry_time <= current_time).all()
    logger.info(f"Found {len(expired_auctions)} expired auctions.")

    for auction in expired_auctions:
        if auction.current_bid is not None:
            # Process auction with bids
            bidder = User.query.get(auction.current_bidder_id)
            creator = User.query.get(auction.user_id)

            # Transfer item to bidder and currency to creator
            bidder_inventory = UserInventory.query.filter_by(user_id=bidder.id, item_id=auction.item_id).first()
            if bidder_inventory:
                bidder_inventory.quantity += auction.quantity
            else:
                bidder_inventory = UserInventory(user_id=bidder.id, item_id=auction.item_id, quantity=auction.quantity)
                db.session.add(bidder_inventory)

            creator.currency += auction.current_bid

            db.session.delete(auction)
            db.session.commit()
            logger.info(f"Auction with bids processed successfully. Creator: {creator.username}, Bidder: {bidder.username}")

        else:
            # Process auction with no bids
            creator = User.query.get(auction.user_id)
            # Return the item to the creator's inventory
            creator_inventory = UserInventory.query.filter_by(user_id=creator.id, item_id=auction.item_id).first()
            if creator_inventory:
                creator_inventory.quantity += auction.quantity
            else:
                creator_inventory = UserInventory(user_id=creator.id, item_id=auction.item_id, quantity=auction.quantity)
                db.session.add(creator_inventory)

            db.session.delete(auction)
            db.session.commit()
            logger.info(f"Auction with no bids processed successfully. Creator: {creator.username}")

    return 'Expired auctions processed successfully.'

# Define the Celery beat schedule
Celery.conf.beat_schedule = {
    'process-expired-auctions': {
        'task': 'auction_tasks.process_expired_auctions',  # Specify the task function
        'schedule': 5.0,  # Run every 5 seconds
    },
}
