import json
import boto3
import os
import logging
import time
import uuid  # Import the uuid module

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Initialize DynamoDB and SNS clients
dynamodb = boto3.resource('dynamodb')
sns_client = boto3.client('sns')

# Get the table names and SNS topic ARN from environment variables
TABLE_NAME_READING = os.environ['TABLE_NAME_READING']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
TABLE_NAME_THRESHOLD = os.environ['TABLE_NAME_THRESHOLD']

def save_reading(device_id, readings, timestamp=None):
    """Save the readings to DynamoDB."""
    readings_table = dynamodb.Table(TABLE_NAME_READING)
    unique_id = str(uuid.uuid4())  # Generate a new UUID
    try:
        # Convert readings to JSON string format
        readings_json = json.dumps([
            {
                'sensor': reading['sensor'],
                'unit': reading['unit'],
                'value': reading['value']  # Keep as float for direct representation
            }
            for reading in readings
        ])

        readings_table.put_item(
            Item={
                'id': unique_id,  # Use the UUID as the unique ID directly as a string
                'deviceId': device_id,
                'timestamp': timestamp or time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),  # ISO 8601 format
                'readings': readings_json  # Save as a string
            }
        )
        logger.info(f"Successfully saved readings for deviceId: {device_id}, unique_id: {unique_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save readings for deviceId {device_id}: {str(e)}")
        return False


def lambda_handler(event, context):
    device_id = event['deviceId']
    timestamp = event['timestamp']
    readings = event['readings']
    
    # Save the readings to DynamoDB
    if not save_reading(device_id, readings, timestamp):
        return {
            'statusCode': 500,
            'body': json.dumps("Failed to save readings.")
        }

    # Fetch the thresholds from DynamoDB for the given deviceId
    thresholds_table = dynamodb.Table(TABLE_NAME_THRESHOLD)
    threshold_response = thresholds_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr('deviceId').eq(device_id)
    )

    # Log the database response for thresholds
    logger.info(f"Database response for thresholds for deviceId: {device_id}: {threshold_response}")

    if 'Items' not in threshold_response or not threshold_response['Items']:
        logger.warning(f"No thresholds found for deviceId: {device_id}")
        return {
            'statusCode': 404,
            'body': json.dumps("No thresholds found.")
        }

    triggered_thresholds = []

    for reading in readings:
        sensor = reading['sensor']
        unit = reading['unit']
        value = reading['value']

        # Loop through each threshold item and check conditions
        for item in threshold_response['Items']:
            if item['sensorId'] == sensor and item['unit'] == unit:  # Check if the threshold is for the current sensor and unit
                condition_str = item['condition']

                if not condition_str:
                    logger.warning(f"No condition defined for deviceId: {device_id}, sensor: {sensor}")
                    continue

                try:
                    # Convert logical operators from JavaScript-style to Python-style
                    condition_str = condition_str.replace("&&", "and").replace("||", "or")

                    # Evaluate the condition string with 'value' in the context
                    if eval(condition_str, {'reading': float(value)}):  # Ensure 'value' is a float for evaluation
                        triggered_thresholds.append(item)
                        logger.info(f"Triggered threshold for deviceId: {device_id}, sensor: {sensor}, level: {item['level']}")

                        # Create a message to publish to the SNS topic
                        message = f"Threshold Alert! Device ID: {device_id}, Sensor: {sensor}, Value: {value} has triggered a {item['level']} threshold."

                        # Publish the message to SNS
                        try:
                            sns_response = sns_client.publish(
                                TopicArn=SNS_TOPIC_ARN,
                                Subject=f"Threshold Alert: {item['level']} Level Triggered",
                                Message=message
                            )
                            logger.info(f"Alert sent to SNS topic. Response: {sns_response}")
                        except Exception as e:
                            logger.error(f"Failed to publish message to SNS for deviceId {device_id}, sensor: {sensor}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error evaluating condition for deviceId {device_id}, sensor: {sensor}: {str(e)}")

    if triggered_thresholds:
        return {
            'statusCode': 200,
            'body': json.dumps(f"Alerts sent for {len(triggered_thresholds)} thresholds.")
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps("No thresholds triggered.")
        }
