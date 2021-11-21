import os
import time
import logging
import requests
from utils import SQSUtils, S3Utils
from dolly_zoom import DollyZoom
from datetime import datetime
from botocore.exceptions import EndpointConnectionError

from logging_init import initialize_logging

call_back_url = "https://13.233.212.77:5005/callback"

logger = logging.getLogger(__name__)


def main(sqs_utils, s3_utils):
    while 1:
        try:
            receipt_handler, message = sqs_utils.get_message_from_queue()
        except EndpointConnectionError:
            logger.warning("No internet, waiting for %s seconds and again trying", 5)
            time.sleep(5)
            continue

        if not receipt_handler:
            logger.info("No new message. Sleep for 5 seconds..........")
            time.sleep(5)
            continue
        try:
            processed_video_path, local_file = None, None
            request_id = message['request_id']
            video_key = message['video_key']
            skip_frames = int(message['skip_frames'])
            request_time = message['request_time']
            bbox = message['bbox']
            bbox = list(map(int, bbox))
            call_back = {'request_id': request_id, 'status': 'failed'}
            local_file = s3_utils.download_file(video_key)
            with DollyZoom(local_file, skip_frames) as dolly_zoom:
                processed_video_path, video_decoding_time, \
                transform_calculation_time, video_encoding_time,\
                video_width, video_height, fps = dolly_zoom.process(bbox)

            video_key = s3_utils.upload_file(processed_video_path, is_processed=True)
            sqs_utils.delete_message(receipt_handler)
            call_back['status'] = 'success'
            call_back['s3_path'] = s3_utils.get_presigned_url(video_key)
        except Exception as e:
            logger.info("failed to process video")
            logger.exception(e)

        finally:
            if local_file and os.path.exists(local_file):
                os.remove(local_file)
            if processed_video_path and os.path.exists(processed_video_path):
                os.remove(processed_video_path)
            start_time = datetime.strptime(request_time, '%Y-%m-%d %H:%M:%S')
            current_time = datetime.utcnow()
            total_time = (current_time - start_time).seconds
            call_back['total_time'] = total_time
            logger.info(call_back)
            r = requests.post(call_back_url, json=call_back, verify=False)
            logger.info("callback status {}".format(r.status_code))
            logger.info("==============================================")


if __name__ == "__main__":
    initialize_logging(logger, logging.INFO)
    while 1:
        try:
            sqs_util = SQSUtils()
            s3_util = S3Utils()
            break
        except EndpointConnectionError as error:
            logger.info("no internet")

    main(sqs_util, s3_util)


