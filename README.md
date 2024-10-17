# alco-data-save-notifcation
Step 1: Set Up AWS IoT Core
Create an IoT Thing: Register your device as an IoT Thing in AWS IoT Core.
Create a Policy: Create an IoT policy that allows the Thing to publish to a specific topic.
Create a Rule: Set up an AWS IoT rule to trigger a Lambda function whenever a message is published to the MQTT topic.

Step 2: Create the Lambda Function
The Lambda function will be responsible for processing incoming MQTT messages, saving them to DynamoDB, and checking for threshold alerts.

Step 3: Deploy and Test
Deploy the Lambda Function: Use the AWS Management Console, AWS CLI, or an Infrastructure as Code tool (like AWS CloudFormation or Terraform) to deploy your Lambda function.
Test: Publish a message to the configured MQTT topic and check if the readings are saved to DynamoDB and if any alerts are sent.

Key Components
DynamoDB: For storing sensor readings and thresholds.
SNS: For sending alerts based on threshold evaluations.
AWS IoT Core: For managing MQTT connections and routing messages.
