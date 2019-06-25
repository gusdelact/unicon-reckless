from __future__ import print_function  #Code should work with Python 2 or 3
from chalice import Chalice
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch
import hmac
import hashlib
import base64
import sys
import requests
import os
import boto3
import json

patch(('boto3','requests'))

app = Chalice(app_name='swapcaser')
app.debug = True

try:
    client = boto3.client('ssm')
    response = client.get_parameter(Name='/unicornrentals/swapcaser/externalservice')
    SWAPCASESERVICE = response['Parameter']['Value']
    response = client.get_parameter(Name='/unicornrentals/team/teamid')
    TEAMID = response['Parameter']['Value']
    response = client.get_parameter(Name='/unicornrentals/team/teamhash')
    HASH = response['Parameter']['Value']
except:
    print("SSM unavailable - do you have the TeamRole attached")
    print("You could setup envars")
    SWAPCASESERVICE = os.getenv('SWAPCASESERVICE', False)
    TEAMID = os.getenv('TEAMID', False)
    HASH = os.getenv('HASH', False)
print("External Service set to: {}".format(SWAPCASESERVICE))

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

@xray_recorder.capture('json_log')
def json_log(message, status='info', attrs={}):
    #Helper function for adding JSON values in logs
    log = {
    'status':status,
    'host':os.getenv('AWS_LAMBDA_FUNCTION_NAME'),
    'service':'swapcaser',
    'message': message,
    'lambda': {'request_id': app.lambda_context.aws_request_id}
    }
    if attrs:
        attributes = attrs.copy()
        attributes.update(log)
        log = attributes
    print(json.dumps(log))

@app.route('/',methods=['POST', 'GET'])
@xray_recorder.capture('index')
def index():
    request = app.current_request
    json_log("Got a request", attrs=request.json_body)
    if request.method == 'POST':
        xray_recorder.put_annotation("url", "/");
        xray_recorder.put_annotation("method", "POST");
        messageRequest = request.json_body
        xray_recorder.put_annotation('request_body', repr(request.json_body))
        json_log("Message request {}\n".format(repr(request.json_body)), attrs=request.json_body)
        response = {'Message':'','Signature':[]}
        message = messageRequest['Message']
        json_log("Message sent to swapcase service", attrs=request.json_body)
        # try:
            # subsegment = xray_recorder.begin_subsegment('external_request')
            # req = requests.post(SWAPCASESERVICE, json={'Message':messageRequest['Message']}, timeout=2)

            messageRequest['Message'] = messageRequest['Message'].swapcase();

            # xray_recorder.put_annotation('external_service_body', req.text)
            # xray_recorder.put_annotation('call_external_service', req.status_code)
            xray_recorder.end_subsegment()
            #The external service may require anothey key soon, as below.
            #req = requests.post(SWAPCASE_SERVICE, json={'Message':messageRequest['Message'],'ApiVersion':'2'}).json()
        # except requests.exceptions.Timeout:
        #     #request took over 2 seconds, lets try again and hope not to go over 3 second lambda duration
        #     #SWAPCASESERVICE ApiVersion 1 sometimes takes up to 8 seconds
        #     json_log("External service took over 2 seconds. Retrying. By default swapcaser lambda has max 3 second runtime.",status='warning',attrs=request.json_body)
        #     req = requests.post(SWAPCASESERVICE, json={'Message':messageRequest['Message']})
        if req.status_code != 200:
            json_log('External service 500: Inspect "external_request" trace in AWS Xray','error', request.json_body)
        req.raise_for_status()
        req = req.json()
        json_log("Swapcase service request complete", attrs=request.json_body)
        response['Message'] = TEAMID+req['Message']
        response['Signature'] = sign(HASH, response['Message']) #Sign message with my team hash (or HASH)
        json_log("Response from sign function {}\n".format(repr(response)), attrs=response)
        return response

    elif request.method == 'GET':
        xray_recorder.put_annotation("url", "/");
        xray_recorder.put_annotation("method", "GET");
        return {'Status': 'OK'}
