import os
import uuid
import json
import subprocess
from datetime import datetime

import configparser
from redis import Redis
from flask import Flask, request, abort

from utils import S3Utils, SQSUtils, DBUtils

config = configparser.ConfigParser()
config.read('config')
redis_db, s3_utils, sqs_utils, db_utils = Redis(), S3Utils(), SQSUtils(), DBUtils
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = int(config['server']['max_file_size']) * 1024 * 1024


def video_validator(file_name):
    """Returns true/false. Video name should not have space in between."""
    command = f"exiftool {file_name} | grep 'Track Duration'"
    popen = subprocess.Popen(["bash", "-c", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = popen.communicate()
    popen.kill()
    out, err = out.decode('UTF-8'), err.decode('UTF-8')
    if err or not out:
        return False
    return True


@app.route('/callback', methods=['POST'])
def callback():
    """
    /Callback should be accessible from a single host
    Other wise some one can craft a duplicate message, of which we will send a presigned url.
    message-processor-machine posts success/fail message message
    {
        'status': success/fail,
        'video_key': url,
        'request_id': uuid
    }
    """
    request_id, status = request.form['request_id'], request.form['status']
    # This information will be stored in a redis database, each entry is store for at max 24 hours
    # in the redis db, post which it is deleted.
    if status == 'success':
        presigned_s3_path = s3_utils.get_presigned_url(request.form['video_key'])
    else:
        presigned_s3_path = 'failed'
    # After call back user has 24 hours to download the video
    redis_db.set(request_id, presigned_s3_path, ex=int(config['presigned_url']['expiry']))
    return 'success'


@app.route('/get_video', methods=['POST'])
def get_video():
    request_id = request.form['request_id']
    """
    If request is not in redis, this mean it is more than 24 hours since we recieved the request.
    else if there is a dummy value means not processed. 
    
    
    UI Show video with current state(processed/not).     
    """
    result = redis_db.get(request_id)
    if not result:
        # The video is no longer there.
        return json.dumps({'status': 'video_removed'})
    else:
        if result == 'processing':
            return json.dumps({'status': 'processing'})
        elif result == 'failed':
            return json.dumps({'status': 'failed'})
        else:
            return json.dumps({'status': 'processed', 'url': result.decode('UTF-8')})


@app.route('/upload', methods=['POST'])
def upload_video():
    """
    Check if the video itself, it is not of greater size.
    :return:
    """
    request_id = str(int(datetime.utcnow().timestamp())) + uuid.uuid4().hex[:22]
    uploaded_file = request.files['video']
    x, y, w, h = request.form['x'], request.form['y'], request.form['width'], request.form['height']
    skip_frames = request.form['skip_frames']
    file_name = uploaded_file.filename
    if len(file_name.split('.')) != 2:
        abort(400)
    _, ext = file_name.split('.')
    random_file_name = str(uuid.uuid4().hex) + "." + ext
    uploaded_file.save(random_file_name)
    if not video_validator(random_file_name):
        abort(415)
    # Add the request id to redis.
    redis_db.set(request_id, 'processing')
    # Upload video to s3
    upload_path = s3_utils.upload_file(random_file_name, is_processed=False)
    os.remove(random_file_name)
    # Add message to queue
    message = {
        'request_id': request_id,
        'video_key': upload_path,
        'request_time': str(datetime.utcnow()).split('.')[0],
        'skip_frames': skip_frames,
        'bbox': [x, y, w, h]
    }
    sqs_utils.send_message_to_sqs(message)

    return json.dumps(
        {
            'request_id': request_id,
            'return_code': 200
        }
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(config['server']['port']))


