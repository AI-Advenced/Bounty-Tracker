"""
Bounty service for managing bounties and payments
"""
from sqlalchemy.orm import Session
from app.models import Bounty, BountyPayment, User

class BountyService:
    def create_bounty(self, db: Session, bounty_data: dict) -> Bounty:
        """Create a new bounty"""
        bounty = Bounty(**bounty_data)
        db.add(bounty)
        db.commit()
        return bounty
    
    def claim_bounty(self, db: Session, bounty_id: str, hunter_id: str) -> bool:
        """Claim a bounty for a hunter"""
        bounty = db.query(Bounty).filter(Bounty.id == bounty_id).first()
        if bounty and not bounty.hunter_id:
            bounty.claim_bounty(hunter_id)
            db.commit()
            return True
        return False