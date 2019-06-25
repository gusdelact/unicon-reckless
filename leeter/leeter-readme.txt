# Leeter Deployment instructions

An Elastic Beanstalk service that converts text to l33tspeak. Example becomes 3x4mpl3.

This microservice also gets details about your team at runtime from SSM Parameter Store, for signing its messages. 
The elastic beanstalk source package is leeter-elastic-beanstalk-python36.zip

* Go to the AWS Elastic Beanstalk Console, and launch with the default wizard for "Preconfigured Python" applications.


Troubleshooting:

Troubleshoot with Elastic Beanstalk logging. Optionally configure for Cloudwatch Logs and Amazon Xray.
