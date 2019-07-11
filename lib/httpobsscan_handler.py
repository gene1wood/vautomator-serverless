import uuid
import logging
import boto3
import json
import os
from lib.target import Target
from lib.response import Response
from lib.hosts import Hosts
from lib.event import Event

REGION = os.environ.get('REGION')


class HTTPObsScanHandler(object):
    def __init__(self, sqs_client=boto3.client('sqs', region_name=REGION), queueURL=os.getenv('SQS_URL'), logger=logging.getLogger(__name__), region=REGION):
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
                MessageBody="httpobservatory|" + target.name
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

    def queue_scheduled(self, event, context, hostname_list=[]):
        if len(hostname_list) == 0:
            hosts = Hosts()
            hostname_list = hosts.getList()
        for hostname in hostname_list:
            self.sqs_client.send_message(
                QueueUrl=self.queueURL,
                DelaySeconds=2,
                MessageBody="httpobservatory|" + hostname
                + "|"
            )
            self.logger.info("Tasking http observatory scan of: {}".format(hostname))

        self.logger.info("Host list has been added to the queue "
                         "for http observatory scan.")
