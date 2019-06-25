# unicon-reckless
Unicorn Rentals AWS GameDay microservices

### Useful links

https://dashboard.eventengine.run/docs?url=https:%2F%2Fs3.amazonaws.com%2Fee-assets-prod-us-east-1%2Fmodules%2Fgd2018-loadgen%2Fv2%2Freadme.md


### Microservices

# Reverser Deployment instructions

A Fargate service that reverses text. Example becomes elpmaxE.
This microservice also gets details about your team at runtime from SSM Parameter Store, for signing its messages. 

The container repository:
753600854378.dkr.ecr.us-east-1.amazonaws.com/unicorn-service-reverser:latest 

A default 'reverser' fargate task definition is already configured with the above repository, using the ":latest" tag.

* Go to the AWS ECS Console.
* In the 'UnicornFargateCluster' Cluster, run a new task using the "reverser"
  (this points to the correct container repository).
* Make sure you create a SecurityGroup that allows port 80
* When task is running, click its task id, to get its public IP. That is your reverser services endpoint.

Troubleshooting:

We have reports the container can crash, however you may be able to troubleshoot this with Cloudwatch Logs and Amazon Xray.
You can also look at error/warning logging with Cloudwatch Insights using with:

fields @timestamp, status, message
| filter status not like /info/
| sort @timestamp desc
| limit 20

Fargate pulls the container from the VPC you connect it to.
If you get error "CannotPullContainerError: API error (500):" validate your VPC internet connectivity.
