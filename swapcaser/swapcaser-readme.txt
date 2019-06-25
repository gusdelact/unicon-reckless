# Swapcaser Deployment instructions

A SAM Lambda service (Python 3.6) that swaps case of text. Text becomes tEXT.

Options 1 & 2 below use CLI. Option 3 can be done without using CLI.
To use a CLI option, use the Console Login button on dashboard, and copy/paste the CLI credentials into your terminal.

What is AWS SAM? https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html
Installing SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html

Method 1: Using awscli if installed

1. Create a bucket for your lambda package:
aws s3 mb s3://some-bucket-name
2. Send the lambda code to s3, and update the SAM template with a real CodeURI:
aws cloudformation package --template-file service-swapcaser.yml --s3-bucket some-bucket-name --output-template serverless-output.yaml
3. Deploy cloudformation file "serverless-output.yaml" using AWS Console or below AWS CLI:
aws cloudformation deploy --template-file serverless-output.yaml --stack-name swapcaser
4. Once Cloudformation is deployed, use aws cloudformation describe-stacks --stack-name swapcaser, or the AWS Cloudformation console, to retrieve the endpoint address.


Method 2: Using samcli if installed

1. Create a bucket for your lambda package:
aws s3 mb s3://some-bucket-name
2. Send the lambda code to s3, and update the SAM template with a real CodeURI:
sam package \
    --template-file service-swapcaser.yml \
    --output-template-file serverless-output.yaml \
    --s3-bucket some-bucket-name
3. Deploy cloudformation file "serverless-output.yaml" using AWS Console or below SAM CLI:
sam deploy --template-file serverless-output.yaml --stack-name swapcaser
4. Once Cloudformation is deployed, use aws cloudformation describe-stacks --stack-name swapcaser, or the AWS Cloudformation console, to retrieve the endpoint address.


Method 3: I don't have any tools deployed.
1. Create a bucket for your lambda package, using console, and upload the service-swapcaser.zip (inside swapcaser.zip) to it.
2. Copy the s3 objects URI (the s3:// URI format, not HTTPS://)
3. Edit service-swapcaser.yml, so that line 9 / "CodeUri:"" has its value set as the s3 objects URI in s3:// format.
4. Deploy cloudformation file "service-swapcaser.yml"


TROUBLESHOOTING:
Swapcaser has some operational issues. Use X-ray & Cloudwatch logs to help fix any issues.
It uses an external service that can be a bit slow. They will upgrade the API Version at some point today, which will give a speed boost.

Cloudwatch Insights could also be useful using:

filter @type = "REPORT"
| stats avg(@duration), max(@duration), min(@duration) by bin(5m)

fields @timestamp, status, @message
| filter status not like /info/
| sort @timestamp desc
| limit 100

Lookup an X-ray request issue in Cloudwatch Insights:
fields @timestamp, @message
| filter @requestId like /REQUESTID/
