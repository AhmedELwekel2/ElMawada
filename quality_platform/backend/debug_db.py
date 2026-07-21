from database import SessionLocal
from models import Article
from datetime import datetime, timedelta

def debug_database():
    db = SessionLocal()
    try:
        total_count = db.query(Article).count()
        print(f"Total articles in DB: {total_count}")

        if total_count == 0:
            print("The database is empty.")
            return

        relevant_count = db.query(Article).filter(Article.is_relevant == True).count()
        print(f"Articles with is_relevant=True: {relevant_count}")

        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        
        sample_articles = db.query(Article).order_by(Article.id.desc()).limit(10).all()
        
        print(f"\nLatest 10 Articles Info:")
        print(f"{'ID':<5} | {'Relevant':<10} | {'Published':<20} | {'Created':<20}")
        print("-" * 65)
        for a in sample_articles:
            pub = str(a.published_at) if a.published_at else "NULL"
            cre = str(a.created_at) if a.created_at else "NULL"
            print(f"{a.id:<5} | {str(a.is_relevant):<10} | {pub:<20} | {cre:<20}")

        recent_count = db.query(Article).filter(
            (Article.published_at >= yesterday) | (Article.created_at >= yesterday)
        ).count()
        print(f"\nArticles matching Daily Filter (published/created >= {yesterday.date()}): {recent_count}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_database()