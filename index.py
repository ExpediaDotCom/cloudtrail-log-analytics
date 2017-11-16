""" This module reads the SNS message to get the S3 file location for cloudtrail
 log and stores into Elasticsearch. """

from __future__ import print_function
import json
import boto3
import logging
import datetime
import gzip
import urllib
import os
import traceback

from StringIO import StringIO
from exceptions import *

# from awses.connection import AWSConnection
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
                                
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3', region_name=os.environ['AWS_REGION'])

awsauth = AWS4Auth(os.environ['AWS_ACCESS_KEY_ID'], os.environ['AWS_SECRET_ACCESS_KEY'], os.environ['AWS_REGION'], 'es', session_token=os.environ['AWS_SESSION_TOKEN'])
es = Elasticsearch(
    hosts=[{'host': os.environ['es_host'], 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)
    
def handler(event, context):
    logger.info('Event: ' + json.dumps(event, indent=2))

    s3Bucket = json.loads(event['Records'][0]['Sns']['Message'])['s3Bucket'].encode('utf8')
    s3ObjectKey = urllib.unquote_plus(json.loads(event['Records'][0]['Sns']['Message'])['s3ObjectKey'][0].encode('utf8'))

    logger.info('S3 Bucket: ' + s3Bucket)
    logger.info('S3 Object Key: ' + s3ObjectKey)

    try:
        response = s3.get_object(Bucket=s3Bucket, Key=s3ObjectKey)
        content = gzip.GzipFile(fileobj=StringIO(response['Body'].read())).read()

        for record in json.loads(content)['Records']:
            recordJson = json.dumps(record)
            logger.info(recordJson)
            indexName = 'ct-' + datetime.datetime.now().strftime("%Y-%m-%d")
            res = es.index(index=indexName, doc_type='record', id=record['eventID'], body=recordJson)
            logger.info(res)
        return True
    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        traceback.print_exc()
        return False
 