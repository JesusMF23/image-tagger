from sqlalchemy.sql import text
from datetime import datetime

def get_images(session, min_date=None, max_date=None, tags=None):
    base_query = """
    SELECT p.id, p.date, p.path, GROUP_CONCAT(t.tag) as tags, GROUP_CONCAT(t.confidence) as confidences
    FROM pictures p
    LEFT JOIN tags t ON p.id = t.picture_id
    """

    params = {}
    if min_date:
        base_query += ' AND p.date >= :min_date'
        params['min_date'] = min_date

    if max_date:
        base_query += ' AND p.date <= :max_date'
        params['max_date'] = max_date

    if tags:
        tags_placeholders = ','.join([f":tag_{i}" for i in range(len(tags))])
        base_query += f" AND t.tag IN ({tags_placeholders})"
        params.update({f"tag_{i}": tag for i, tag in enumerate(tags)})

    base_query += ' GROUP BY p.id'

    return session.execute(text(base_query), params).fetchall()

def get_image(session, image_id=None):
    base_query = """
    SELECT p.id, p.date, p.path, GROUP_CONCAT(t.tag) as tags, GROUP_CONCAT(t.confidence) as confidences
    FROM pictures p
    LEFT JOIN tags t ON p.id = t.picture_id
    """

    if image_id:
        base_query += ' WHERE p.id = :image_id'
    
    base_query += ' GROUP BY p.id'

    return session.execute(text(base_query), params={'image_id': image_id}).fetchone()

def get_tags(session, min_date=None, max_date=None):
    base_query = """
    SELECT tag, COUNT(DISTINCT picture_id) as n_images, MIN(confidence) as min_confidence, 
    MAX(confidence) as max_confidence, AVG(confidence) as mean_confidence FROM tags
    """

    params = {}
    if min_date and max_date:
        base_query += ' WHERE date >= :min_date AND date <= :max_date'
        params['min_date'] = min_date
        params['max_date']=max_date
    if min_date and not max_date:
        base_query += ' WHERE date >= :min_date'
        params['min_date'] = min_date

    if max_date and not min_date:
        base_query += ' WHERE date <= :max_date'
        params['max_date'] = max_date

    base_query += ' GROUP BY tag'

    return session.execute(text(base_query), params).fetchall()