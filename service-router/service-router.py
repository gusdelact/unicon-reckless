#!/usr/bin/env python
from __future__ import print_function  #Code should work with Python 2 or 3

from flask import Flask, request
import sys, os, json, random, logging, socket
import requests
import boto3
import watchtower
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

#Lets try and log Flask / Requests to Cloudwatch logs
logging.basicConfig(level=logging.INFO)
# use app.logger.info() for logging, as will ship to CWL

ROUTES = {} #Dict for Routes, will be DynamoDB
ROUTES["reverser"] = [] #Could be multiple same service

app = Flask(__name__)

def update_routes():
    "Function to update ROUTES, with microservice endpoint details, from dynamodb/service-table"
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('service-table')
        for _ in range(5):
            services = table.scan()
        global ROUTES #need to declare its a global to modify it, cause threading
        ROUTES = {}

        for service in services['Items']:
            if service['ServiceType'] not in ROUTES.keys():
                ROUTES[service['ServiceType']] = [service['Endpoint'],]
            elif service['Endpoint'] not in ROUTES[service['ServiceType']]:
                ROUTES[service['ServiceType']].append(service['Endpoint'])
    except:
        app.logger.exception('update_routes() error')

def json_log(message, status='info'):
    #Helper function for adding JSON values in logs
    log = {
    'status':status,
    'host':socket.gethostname(),
    'service':'service-router',
    'message': message
    }
    if status == 'info':
        app.logger.info(json.dumps(log))
    elif status == 'warning':
        app.logger.error(json.dumps(log))
    else:
        app.logger.error(json.dumps(log))

@app.route('/', methods=['GET', 'POST'])
def api():
    "Our API logic, to route calls to correct microservices, and return the result"
    if request.method == 'POST': #This code deals with API calls, and sends to microservice chain
        #Lets update our micro service endpoints / routes.
        update_routes()
        json_log('Routes: {}'.format(repr(ROUTES)))
        # Read the API payload, and pass on to external microservices
        messageRequest = request.get_json()
        json_log("Host {} received RequestId {}, asking for services: {}".format(socket.gethostname(),messageRequest['RequestId'],','.join(messageRequest['Services'])))
        xray_recorder.put_annotation("RequestId", str(messageRequest['RequestId']))
        xray_recorder.put_metadata("Services", messageRequest['Services'])
        xray_recorder.put_metadata("InputMessage", messageRequest['Message'])
        routerResponse = {'Responses':[]}
        errors = 0
        for service in messageRequest['Services']:
            # Select a random microservice endpoint, from global ROUTES, updated from DynamoDB
            service_endpoint = ""
            try:
                service_endpoint = random.choice(ROUTES[service])
                json_log('RequestId {} needs Service:{} using Endpoint:{}'.format(messageRequest['RequestId'],service,service_endpoint))
                req = requests.post(service_endpoint, timeout=10, json={'RequestId':messageRequest['RequestId'],'Message':messageRequest['Message']}).json()
            except KeyError as e:
                json_log('Request included a service we dont support, Shutting down server','error')
                json_log('service-router may need HA config, or to run the latest code from the dashboard','warning')
                service_endpoint = "Error"
                func = request.environ.get('werkzeug.server.shutdown')
                func() #Code isnt working correctly, quit so instance will be replaced.
                #Comment out the lines from 'except KeyError' down to this comment, if you dont want the service-router to restart randomly
            except Exception as e: #Catch any issues with upstream microservice
                #If this code happens, our response will end up being invalid, as we didnt do each transformation
                json_log('Error:"{}" connecting to Service:{} Endpoint:{}'.format(e, service, service_endpoint),'exception')
                errors += 1
            try:
                routerResponse['Responses'].append(req)#Add the microservice response to our list of responses
                messageRequest['Message']=req['Message']
            except Exception as e:
                json_log('Bad response:"{}" from Service:{} Endpoint:{}'.format(e,service,service_endpoint),'exception')
                errors += 1
        #return an http 200, and our API output
        xray_recorder.put_metadata("ErrorCount", errors)
        xray_recorder.put_metadata("Response", routerResponse)
        if errors:
            json_log('RequestId {} completed with {} errors'.format(messageRequest['RequestId'], str(errors)))
        else:
            json_log('RequestId {} completed successfully'.format(messageRequest['RequestId']))
        return json.dumps(routerResponse), 200
    return 'Service Map:\n {}'.format(repr(ROUTES)), 200

@app.route('/services', methods=['GET'])
def services():
    #Return the service map the service-router is using
    #This is required for the clients to know what services they can send us.
    return json.dumps(ROUTES), 200

@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    #In case its useful to have a healthcheck
    return 'OK', 200


if __name__ == '__main__':
    #This section just tries to turn on logging to Cloudwatch Logs, X-ray and runs webserver
    try:
        handler = watchtower.CloudWatchLogHandler(log_group='service-router',)
        app.logger.addHandler(handler)
        #Silence noisy logging
        logging.getLogger('botocore').setLevel(logging.CRITICAL)
        logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
    except:
        print('Couldn\'t start CW Logging')

    #Do first load of routes/endpoints/services from DDB
    update_routes()

    #Lets try to use AWS X-ray for metrics / logging if available to us
    try:
        xray_recorder.configure(service='service-router', sampling=False, context_missing='LOG_ERROR')
        XRayMiddleware(app, xray_recorder)
        from aws_xray_sdk.core import patch
        patch(('requests',))
    except:
        print('Failed to import X-ray')

    json_log('New service-router instance {} has come online'.format(socket.gethostname()))

    #Run the flask webserver
    app.run(host='0.0.0.0', port='80')
