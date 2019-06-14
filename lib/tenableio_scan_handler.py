import uuid
import logging
import boto3
import json
import os
from lib.target import Target
from lib.response import Response
from lib.hosts import Hosts
from lib.event import Event


class TIOScanHandler(object):
    def __init__(
        self, sqs_client=boto3.client('sqs', region_name='us-west-2'),
        queueURL=os.getenv('SQS_URL'),
        logger=logging.getLogger(__name__),
        region='us-west-2'
    ):
        self.sqs_client = sqs_client
        self.queueURL = queueURL
        self.logger = logger
        self.region = region

    def queue(self, event, context):
        # print("Event: {}, context: {}".format(event, context.invoked_function_arn))
        source_event = Event(event, context)
        data = source_event.parse()

        if data:
            target = Target(data.get('target'))
            if not target:
                self.logger.error("Target validation failed of: {}".format(target.name))
                return Response({
                    "statusCode": 400,
                    "body": json.dumps({'error': 'Target was not valid or missing'})
                }).with_security_headers()

            scan_uuid = str(uuid.uuid4())
            self.sqs_client.send_message(
                QueueUrl=self.queueURL,
                MessageBody="tenableio|" + target.name
                + "|" + scan_uuid
            )

            # Use a UUID for the scan type and return it
            return Response({
                "statusCode": 200,
                "body": json.dumps({'uuid': scan_uuid})
            }).with_security_headers()
        else:
            self.logger.error("Unrecognized payload: {}".format(data))
            return Response({
                "statusCode": 400,
                "body": json.dumps({'error': 'Unrecognized payload'})
            }).with_security_headers()

    def pollScanResults(self, event, context):
        # This function will take a hostname, and query Tenable.io
        # API for the latest scan information for that host, and
        # if found, return the results a HTML or JSON object
        
        return
