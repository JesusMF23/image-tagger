from app import app, Session
from app.models import Picture, Tag, Base
from flask import request, jsonify
from datetime import datetime
import base64
import requests
import os
import json
from uuid import uuid4
from imagekitio import ImageKit

# Load credentials
with open('../credentials.json') as f:  # Ensure the correct path to credentials.json
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
    url_endpoint = "https://ik.imagekit.io/JesusMF23"
)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['POST'])
def upload_picture():
    data = request.json
    query_param = request.args.get('min_confidence', 80)

    # Decode base64 image
    picture_id = str(uuid4())
    image_data = base64.b64decode(data['image'])
    image_path = os.path.join(UPLOAD_FOLDER, f"{picture_id}.jpg")

    with open(image_path, 'wb') as image_file:
        image_file.write(image_data)

    # Step 1: Upload the image to ImageKit.io
    with open(image_path, 'rb') as image_file:
        upload_image = base64.b64encode(image_file.read())
        upload_info = imagekit.upload(file=upload_image, file_name=f"{picture_id}.jpg")
        # response = requests.post(
        #     IMAGEKIT_UPLOAD_URL,
        #     files={'file': image_file, 'fileName': f"{picture_id}.jpg"},
        #     # data={'fileName': f"{picture_id}.jpg"},
        #     auth=(f"{IMAGEKIT_PRIVATE_KEY}:")
        # )
    
    # if response.status_code != 200:
    #     print(f"Response: {response.json()}")
    #     return jsonify({'error': 'Failed to upload image to ImageKit'}), 500
    
    image_url = upload_info.url
    file_id = upload_info.file_id
    print(f"Image URL: {image_url}")
    print(f"File ID: {file_id}")

    # Step 2: Use Imagga to obtain tags for the image
    response = requests.get(
    # 'https://api.imagga.com/v2/tags?image_url=%s' % image_url,
    'https://api.imagga.com/v2/tags',
        params={'image_url': image_url, 'threshold': query_param},
        auth=(IMAGGA_API_KEY, IMAGGA_API_SECRET)
    )
    print(f"Response from Imagga: {response.json()}")

    if response.status_code != 200:
        return jsonify({'error': 'Failed to get tags from Imagga'}), 500

    tags_data = response.json()['result']['tags']
    print(tags_data)

    # Step 3: Delete the uploaded image from ImageKit.io
    # delete_response = requests.delete(
    #     f"https://api.imagekit.io/v1/files/{file_id}",
    #     auth=(IMAGEKIT_PUBLIC_KEY, IMAGEKIT_PRIVATE_KEY)
    # )

    # if delete_response.status_code != 204:
    #     return jsonify({'error': 'Failed to delete image from ImageKit'}), 500
    delete_image = imagekit.delete_file(file_id=file_id)

    print(f"Status deletion image: {delete_image.response_metadata.http_status_code}")

    # Save picture and tags information to the database
    session = Session()
    try:
        picture = Picture(
            id=picture_id,
            path=image_url,
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

        # Calculate image size in KB
        image_size_kb = os.path.getsize(image_path) / 1024

        # Prepare response
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
    
    # Remove the local image file
    os.remove(image_path)
    
    return jsonify(response_data), 201
