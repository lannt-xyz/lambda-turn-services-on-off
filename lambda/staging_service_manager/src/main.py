import boto3
import os
import logging
import watchtower

# Get environment variables for resource identifiers
CLUSTER_NAME = os.getenv("CLUSTER_NAME", "staging-cluster")
SERVICE_NAME = os.getenv("SERVICE_NAME", "staging-service")
DB_INSTANCE_IDENTIFIER = os.getenv("DB_INSTANCE_IDENTIFIER", "staging-db")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LOG_GROUP = os.getenv("LOG_GROUP", "/custom/staging-cost-saver")

def lambda_handler(event, context):
    """
    event: {"action": "stop" | "start"}
    """
    # Logging setup
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(
        watchtower.CloudWatchLogHandler(
            log_group=LOG_GROUP,
            create_log_group=True,
            stream_name="{function_name}-{request_id}"
        )
    )

    # Boto3 clients
    ecs_client = boto3.client("ecs", region_name=AWS_REGION)
    rds_client = boto3.client("rds", region_name=AWS_REGION)

    action = event.get("action", "stop")
    logger.info(f"Lambda triggered with action: {action}")
    
    # ECS: scale service
    if action == "stop":
        desired_count = 0
    elif action == "start":
        desired_count = 1
    else:
        logger.error(f"Unknown action: {action}")
        raise ValueError(f"Unknown action: {action}")

    # ECS update
    logger.info(f"Updating ECS service '{SERVICE_NAME}' in cluster '{CLUSTER_NAME}' to desired count: {desired_count}")
    ecs_response = ecs_client.update_service(
        cluster=CLUSTER_NAME,
        service=SERVICE_NAME,
        desiredCount=desired_count
    )
    logger.info(f"ECS response: {ecs_response}")
    
    # RDS stop/start
    if action == "stop":
        logger.info(f"Stopping RDS instance '{DB_INSTANCE_IDENTIFIER}'")
        rds_response = rds_client.stop_db_instance(DBInstanceIdentifier=DB_INSTANCE_IDENTIFIER)
    else:
        logger.info(f"Starting RDS instance '{DB_INSTANCE_IDENTIFIER}'")
        rds_response = rds_client.start_db_instance(DBInstanceIdentifier=DB_INSTANCE_IDENTIFIER)
    logger.info(f"RDS response: {rds_response}")

    logger.info(f"Action '{action}' executed successfully")

    return {
        "status": f"{action} executed successfully",
        "ecs_desired_count": desired_count,
        "db_instance": DB_INSTANCE_IDENTIFIER,
        "ecs_response": ecs_response,
        "rds_response": rds_response
    }
