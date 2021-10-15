import os
from flask import Flask, render_template, request, redirect, url_for
import uuid
from datetime import datetime
import json
from redis import Redis
from utils import S3Utils, SQSUtils, DBUtils


redis_db, s3_utils, sqs_utils, db_utils = Redis(), S3Utils(), SQSUtils(), DBUtils
app = Flask(__name__)


@app.route('/callback', methods=['POST'])
def callback():
    """
    /Callback should be accessible from a single host
    Other wise some one can craft a duplicate message, of which we will send a presigned url.
    message-processor-machine posts success/fail message message
    {
        'status': success/fail,
        'video_path': url,
        'request_id': uuid
        'video_decoding_time': ,
        'transform calculation': ,
        'video_encoding':
        'total_time':
        'video_width':
        'video_height':
    }
    """
    video_key, request_id = request['video_key'], request['request_id']
    # This information will be stored in a redis database, each entry is store for at max 2 hours
    # in the redis db, post which it is deleted.
    presigned_s3_path = s3_utils.get_presigned_url(video_key)
    query = """insert into request_stats({request_id}, {video_decoding_time},
               {transform_calculation_time}, {video_encoding_time}, {total_time},
               {video_width}, {video_height}""".format(**request.form)
    db_utils.register_request_to_db(query)
    # After call back user has 24 hours to download the video
    redis_db.set(request_id, presigned_s3_path, ex = 86400)
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
        if result == 'dummy':
            return json.dumps({'status': 'processing'})
        else:
            return json.dumps({'status': 'processed', 'url': result})


@app.route('/upload', methods=['POST'])
def upload_video():
    request_id = str(int(datetime.utcnow().timestamp())) + uuid.uuid4().hex[:22]
    uploaded_file = request.files['file']

    file_name = uploaded_file.filename
    if file_name != '':
        uploaded_file.save(file_name)
    # Add the request id to redis.
    redis_db.set(request_id, 'dummy')
    # Upload video to s3
    upload_path = s3_utils.upload_file(file_name, is_processed=False)
    os.remove(file_name)
    # Add message to queue
    message = {'request_id': request_id, 'video_key': upload_path}
    sqs_utils.send_message_to_sqs(message)

    return json.dumps(
        {
            'request_id': request_id,
            'return_code': 200
        }
    )


if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
