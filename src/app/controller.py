from app import app, Session
from app.models import Picture, Tag, Base
from app.views import get_images, get_image, get_tags
from flask import request, jsonify
from datetime import datetime
import base64
import requests
import os
import json
from uuid import uuid4
from imagekitio import ImageKit

with open('./credentials.json') as f: 
    credentials = json.load(f)

IMAGEKIT_UPLOAD_URL = 'https://upload.imagekit.io/api/v1/files/upload'
IMAGEKIT_PUBLIC_KEY = credentials['IMAGEKIT_PUBLIC_KEY']
IMAGEKIT_PRIVATE_KEY = credentials['IMAGEKIT_PRIVATE_KEY']
IMAGGA_API_KEY = credentials['IMAGGA_API_KEY']
IMAGGA_API_SECRET = credentials['IMAGGA_API_SECRET']
UPLOAD_FOLDER = 'uploads'

imagekit = ImageKit(
    public_key=IMAGEKIT_PUBLIC_KEY,
    private_key=IMAGEKIT_PRIVATE_KEY,
    url_endpoint = 'https://ik.imagekit.io/JesusMF23'
)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['POST'])
def upload_picture():
    data = request.json
    min_confidence = request.args.get('min_confidence', 80)

    picture_id = str(uuid4())
    image_data = base64.b64decode(data['image'])
    image_path = os.path.join(UPLOAD_FOLDER, f"{picture_id}.jpg")

    with open(image_path, 'wb') as image_file:
        image_file.write(image_data)

    with open(image_path, 'rb') as image_file:
        upload_image = base64.b64encode(image_file.read())
        upload_info = imagekit.upload(file=upload_image, file_name=f"{picture_id}.jpg")
    
    image_url = upload_info.url
    file_id = upload_info.file_id

    response = requests.get(
    'https://api.imagga.com/v2/tags',
        params={'image_url': image_url, 'threshold': min_confidence},
        auth=(IMAGGA_API_KEY, IMAGGA_API_SECRET)
    )

    if response.status_code != 200:
        return jsonify({'error': 'Failed to get tags from Imagga'}), 500

    tags_data = response.json()['result']['tags']

    delete_image = imagekit.delete_file(file_id=file_id)

    session = Session()
    try:
        picture = Picture(
            id=picture_id,
            path=image_path,
            date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        session.add(picture)

        tags_list = []
        for tag_data in tags_data:
            tag = Tag(
                tag=tag_data['tag']['en'],
                picture_id=picture.id,
                confidence=tag_data['confidence'],
                date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            session.add(tag)
            tags_list.append({
                'tag': tag_data['tag']['en'],
                'confidence': tag_data['confidence']
            })

        session.commit()

        image_size_kb = os.path.getsize(image_path) / 1024

        response_data = {
            'id': picture.id,
            'size': image_size_kb,
            'date': picture.date,
            'tags': tags_list,
            'data': data['image']
            }

    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()
    
    
    return jsonify(response_data), 201


@app.route('/images', methods=['GET'])
def filter_images():
    min_date = request.args.get('min_date', None)
    max_date = request.args.get('max_date', None)
    tags = request.args.get('tags', None)

    if tags is None:
        return jsonify({'error': 'Bad rYou must provide at least one tag to use this endpoint.'}), 400
    
    tags_array = tags.split(',')

    session = Session()

    try:
        pictures = get_images(session, min_date, max_date, tags_array)
        
        images_data = []
        for row in pictures:
            id, date, path, tags, confidences = row
            tags_list = [{'tag': tag, 'confidence': confidence} for tag, confidence in zip(tags.split(','), confidences.split(','))]
            image_data = {
                'id': id,
                'date': date,
                'size': os.path.getsize(path) / 1024,
                'tags': tags_list
            }
            images_data.append(image_data)
        
        return jsonify(images_data), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        session.close()

@app.route('/image/<image_id>', methods=['GET'])
def download_image(image_id):

    session = Session()
    try:
        picture = get_image(session, image_id)

        if picture:
            tags_list = [{'tag': tag, 'confidence': confidence} for tag, confidence in zip(picture.tags.split(','), picture.confidences.split(','))]
            image_data = {
                'id': image_id,
                'date': picture.date,
                'size': os.path.getsize(picture.path) / 1024,  # size in KB
                'tags': tags_list,
                'data': base64.b64encode(open(picture.path, 'rb').read()).decode('utf-8')
            }
            return jsonify(image_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        session.close()

@app.route('/tags', methods=['GET'])
def filter_tags():
    min_date = request.args.get('min_date', None)
    max_date = request.args.get('max_date', None)

    session = Session()
    try:
        tags = get_tags(session, min_date, max_date)
        tags_data = []
        for row in tags:
            id, n_images, min_confidence, max_confidence, mean_confidence = row
            tag_data = {
                'tag': id,
                'n_images': n_images,
                'min_confidence': min_confidence,
                'max_confidence': max_confidence,
                'mean_confidence': mean_confidence,
            }
            tags_data.append(tag_data)
        return jsonify(tags_data), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        session.close()