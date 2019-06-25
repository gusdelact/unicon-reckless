from __future__ import print_function  #Code should work with Python 2 or 3
#Service Reverser
from flask import Flask, Response, request
import json
import hmac
import hashlib
import base64
import sys
import boto3
import os, socket
import logging
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
#Import requests for the dynamic proxying healthcheck
import requests

application = Flask(__name__)

logging.basicConfig(level=logging.INFO,format='%(message)s')
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)

# Attempt to get our region
try:
    r = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document").json()
    region = r.get('region')
    boto3.setup_default_session(region_name=region)
    print("Default region set to {}".format(region))
except:
    print("Detecting region from EC2 metadata failed")

try:
    client = boto3.client('ssm')
    response = client.get_parameter(Name='/unicornrentals/team/teamid')
    TEAMID = response['Parameter']['Value']
    response = client.get_parameter(Name='/unicornrentals/team/teamhash')
    HASH = response['Parameter']['Value']
except:
    print("SSM unavailable - do you have the TeamRole attached")
    print("You could setup envars for TEAMID & HASH")
    TEAMID = os.getenv('TEAMID', False)
    HASH = os.getenv('HASH', False)

if not TEAMID and not HASH:
    print("Critical Error: Environment variables TEAMID and HASH, not set.")
    sys.exit()
    
try:
    xray_recorder.configure(service='l33t3r', sampling=False, context_missing='LOG_ERROR')
    XRayMiddleware(application, xray_recorder)
except:
    print('Failed to import X-ray')

@xray_recorder.capture('json_log')
def json_log(message, status='info', attrs={}):
    log = {
    'status':status,
    'host':socket.gethostname(),
    'service':'leeter',
    'message': message,
    }
    if attrs:
        attributes = attrs.copy()
        attributes.update(log)
        log = attributes
    if status == 'info':
        application.logger.info(json.dumps(log))
    elif status == 'warning':
        application.logger.error(json.dumps(log))
    else:
        application.logger.exception(json.dumps(log))

@xray_recorder.capture('sign')
def sign(key, message): #HMAC signing, sign with our teams secret hash
    if sys.version_info[0] < 3: #HMAC bahavior for Python2
        message = bytes(message).encode('utf-8')
        key = bytes(key).encode('utf-8')
    else: #HMAC bahavior for Python3
        message = bytes(message, 'utf-8')
        key = bytes(key, 'utf-8')
    sig = hmac.new(key, message, hashlib.sha256)
    return base64.b64encode(sig.digest()).decode()

@xray_recorder.capture('transform')
def transform(response, message):
    #transform replaces letters with numbers: o -> 0; e -> 3; l -> 1; t -> 7
    message=message.replace('o','0')
    message=message.replace('e','3')
    message=message.replace('l','1')
    message=message.replace('t','7')
    message=message.replace('O','0')
    message=message.replace('E','3')
    message=message.replace('L','1')
    message=message.replace('T','7')
    response['Message'] = TEAMID+message
    response['Signature'] = sign(HASH, response['Message']) #Sign message with my team hash
    return response

@application.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        json_log("Got a request", attrs=request.json)
        messageRequest = request.json
        response = {'Message':'','Signature':[]}
        message = messageRequest['Message']
        response = transform(response, message)
        json_log("Response {}\n".format(repr(response)), attrs=response)
        return json.dumps(response)
    elif request.method == 'GET':
        return json.dumps({'Status': 'OK'})

#proxy health check, so we can configure any healthcheck to test our instance can reach a required endpoint
@application.route('/healthcheck/<path:path>', methods=['GET'])
def healthcheck(path):
    # Code snippet found here - must be safe to use:
    # https://stackoverflow.com/questions/15463004/how-can-i-send-a-get-request-from-my-flask-app-to-another-site
    # Lets pass a secret just in case
    teamhash = request.args.get('teamhash')
    if teamhash == HASH:
        uri = "http://%s" % path
        r = requests.get(uri)
        return Response(
            r.text,
            status=r.status_code,
            content_type=r.headers['content-type'],
        )
    else:
        return "Authenticate with query parameter 'teamhash'", 401

if __name__ == '__main__':
    application.debug = True
    application.run()
