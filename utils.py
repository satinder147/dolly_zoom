import os
import json
import boto3
import logging
import time
from datetime import datetime


class SQSUtils:
    def __init__(self):
        region = "ap-south-1"
        queue_name = 'vertigo-effect-creator'
        self.sqs_client = boto3.client('sqs', region_name=region)
        sqs_resource_handle = boto3.resource('sqs', region_name=region)
        queue = sqs_resource_handle.get_queue_by_name(QueueName=queue_name)
        self.queue_url = queue.url
        logging.info("Queue URL: %s", self.queue_url)

    def send_message_to_sqs(self, data):
        """push message to SQS"""
        try:
            self.sqs_client.send_message(QueueUrl=self.queue_url, MessageBody=json.dumps(data))
            return True
        except Exception as e:
            logging.exception(e)

    def get_message_from_queue(self):
        """Receive message from queue"""
        msg = self.sqs_client.receive_message(QueueUrl=self.queue_url)
        if 'Messages' in msg:
            msg = msg['Messages'][0]
            # TODO: compute the md5 of message to check if there is some problem with the message.
            return msg['ReceiptHandle'], msg['Body']
        else:
            return None, None

    def delete_message(self, receipt_handler):
        response = self.sqs_client.delete_message(QueueUrl=self.queue_url,
                                                  ReceiptHandle=receipt_handler)
        print(response)  # How to know if this was successful.


class S3Utils:
    def __init__(self):
        self.s3_bucket = 'vertigo-effect'
        self.s3_client = boto3.client('s3')
        self.video_upload_path_base = 'vertigo_effect/{}/processed/{}'

    def upload_file(self, local_file):
        today = str(datetime.utcnow().date())
        s3_upload_path = self.video_upload_path_base.format(today, local_file)
        self.s3_client.upload_file(local_file, self.s3_bucket, s3_upload_path)
        logging.info("Successfully uploaded the video")

    def download_file(self, file_key):
        # function expects s3 key instead of whole path
        local_file = file_key.split('/')[-1]
        self.s3_client.download_file(self.s3_bucket, file_key, local_file)
        if os.path.exists(local_file):
            logging.info("successfully downloaded the file")
            return local_file
        else:
            raise ValueError('Failed to download video')


if __name__ == '__main__':
    obj = S3Utils()
    # obj.download_file('data/test.mp4')
    obj.upload_file('test.mp4')
    # obj = MessageHandler()
    # data = {'video_path': 'https://', 'sender': 'satinder'}
    # if obj.send_message_to_sqs(data):
    #     print("successfully sent a message")
    # print("sleep for 10 seconds")
    # time.sleep(10)
    # receipt_handle, msg_body = obj.get_message_from_queue()
    # print(msg_body)
    # obj.delete_message(receipt_handle)
    # print("deleted message")

