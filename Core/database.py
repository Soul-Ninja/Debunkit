from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
db = SQLAlchemy()

class Analysis(db.Model):
    """Store fact-check analyses performed by users."""
    __tablename__ = 'analyses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    text_analyzed = db.Column(db.Text, nullable=False, index=True)
    verdict = db.Column(db.String(50), nullable=False, index=True)
    confidence = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text)
    fact_check = db.Column(db.Text)
    red_flags = db.Column(db.JSON)
    sources = db.Column(db.JSON)
    mode = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))

    def __repr__(self):
        return f'<Analysis {self.id}: {self.verdict} ({self.confidence}%)>'

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id, 'text_analyzed': self.text_analyzed,
            'verdict': self.verdict, 'confidence': self.confidence, 'reason': self.reason,
            'fact_check': self.fact_check, 'red_flags': self.red_flags or [],
            'sources': self.sources or [], 'mode': self.mode,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class Review(db.Model):
    """Store community reviews and verdicts."""
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    author_name = db.Column(db.String(100), nullable=False)
    author_role = db.Column(db.String(100), default="Truth Seeker")
    rating = db.Column(db.Integer, default=5)
    content = db.Column(db.Text, nullable=False)
    avatar = db.Column(db.String(20), default="⭐")
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self):
        return {
            'id': self.id, 'author_name': self.author_name, 'author_role': self.author_role,
            'rating': self.rating, 'content': self.content, 'avatar': self.avatar,
            'timestamp': self.timestamp.strftime("%b %d, %Y") if self.timestamp else None
        }

def init_db(app):
    """Initialize database with Flask app."""
    db.init_app(app)
    with app.app_context():
        db.create_all()

def save_analysis(text, verdict, confidence, reason, fact_check, red_flags, sources, mode, user, request):
    """Save analysis result to database."""
    try:
        analysis = Analysis(
            user_id=user.id, text_analyzed=text[:5000], verdict=verdict, confidence=confidence,
            reason=reason, fact_check=fact_check, red_flags=red_flags, sources=sources,
            mode=mode, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(analysis)
        db.session.commit()
        return analysis
    except Exception as e:
        logger.error(f"Failed to save analysis: {e}")
        db.session.rollback()
        return None

def get_analysis_history(user=None, limit=50, offset=0):
    """Get recent analyses for a user."""
    try:
        q = Analysis.query.filter_by(user_id=user.id) if user else Analysis.query
        return [a.to_dict() for a in q.order_by(Analysis.timestamp.desc()).limit(limit).offset(offset).all()]
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        return []

def get_analysis_by_id(analysis_id):
    """Get specific analysis by ID."""
    try:
        a = db.session.get(Analysis, int(analysis_id))
        return a.to_dict() if a else None
    except Exception as e:
        logger.error(f"Failed to fetch analysis: {e}")
        return None

def search_analyses(query, user=None, limit=50):
    """Search analyses by text content."""
    try:
        q = Analysis.query.filter_by(user_id=user.id) if user else Analysis.query
        return [a.to_dict() for a in q.filter(Analysis.text_analyzed.ilike(f'%{query}%')).order_by(Analysis.timestamp.desc()).limit(limit).all()]
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

def get_statistics(user=None):
    """Get accuracy statistics."""
    try:
        q = Analysis.query.filter_by(user_id=user.id) if user else Analysis.query
        total = q.count()
        if total == 0:
            return {'total_analyses': 0, 'verdict_breakdown': {}, 'average_confidence': 0, 'mode_breakdown': {}}

        verdicts = dict(q.with_entities(Analysis.verdict, func.count(Analysis.id)).group_by(Analysis.verdict).all())
        modes = dict(q.with_entities(Analysis.mode, func.count(Analysis.id)).group_by(Analysis.mode).all())
        avg_conf = q.with_entities(func.avg(Analysis.confidence)).scalar() or 0

        return {
            'total_analyses': total, 'verdict_breakdown': verdicts,
            'average_confidence': round(float(avg_conf), 2), 'mode_breakdown': modes
        }
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        return {}

def save_review(author_name, author_role, rating, content, avatar="⭐"):
    """Save community review to database."""
    try:
        rev = Review(
            author_name=author_name.strip()[:100], author_role=author_role.strip()[:100] or "Truth Seeker",
            rating=max(1, min(5, int(rating))), content=content.strip()[:500], avatar=avatar
        )
        db.session.add(rev)
        db.session.commit()
        return rev
    except Exception as e:
        logger.error(f"Failed to save review: {e}")
        db.session.rollback()
        return None

def get_recent_reviews(limit=10):
    """Get recent reviews."""
    try:
        return Review.query.order_by(Review.timestamp.desc()).limit(limit).all()
    except Exception as e:
        logger.error(f"Failed to retrieve reviews: {e}")
        return []
