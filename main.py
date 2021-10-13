import os
import time
import logging
from utils import SQSUtils, S3Utils
from dolly_zoom import DollyZoom


def main(sqs_utils, s3_utils):
    while 1:
        receipt_handler, message = sqs_utils.get_message_from_queue()
        if not receipt_handler:
            logging.info("No new message. Sleep for 5 seconds..........")
            time.sleep(5)
            continue
        try:
            # Download the video
            video_key = message['video_key']
            skip_frames = message.get('skip_frames', 0)
            local_file = s3_utils.download_file(video_key)
            with DollyZoom(local_file, skip_frames) as dolly_zoom:
                processed_video_path = dolly_zoom.process()
            s3_utils.upload_file(processed_video_path)
            os.remove(local_file)
            os.remove(processed_video_path)

        except Exception as e:
            logging.info("failed to process video")
            logging.exception(e)
            pass
        finally:
            logging.info("==============================================")


if __name__ == "__main__":
    sqs_util = SQSUtils()
    s3_util = S3Utils()
    main(sqs_util, s3_util)


