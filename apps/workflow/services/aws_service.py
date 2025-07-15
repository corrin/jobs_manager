"""
AWS EC2 Instance Management Service
"""

import logging
import os
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AWSService:
    """Service for managing AWS EC2 instances"""

    def __init__(self):
        self.aws_access_key_id = os.environ.get("UAT_AWS_KEY")
        self.aws_secret_access_key = os.environ.get("UAT_AWS_SECRET")
        self.aws_region = os.environ.get("UAT_AWS_REGION", "ap-southeast-2")
        self.uat_instance_id = os.environ.get("UAT_INSTANCE_ID")

        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise ValueError("AWS credentials not found in environment variables")

        if not self.uat_instance_id:
            raise ValueError("UAT_INSTANCE_ID not found in environment variables")

    def _get_ec2_client(self):
        """Get authenticated EC2 client"""
        return boto3.client(
            "ec2",
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

    def get_instance_status(self) -> Dict[str, Any]:
        """Get current status of the UAT instance"""
        try:
            ec2 = self._get_ec2_client()
            response = ec2.describe_instances(InstanceIds=[self.uat_instance_id])

            instance = response["Reservations"][0]["Instances"][0]

            return {
                "success": True,
                "instance_id": self.uat_instance_id,
                "state": instance["State"]["Name"],
                "instance_type": instance["InstanceType"],
                "public_ip": instance.get("PublicIpAddress"),
                "private_ip": instance.get("PrivateIpAddress"),
                "launch_time": instance.get("LaunchTime"),
                "region": self.aws_region,
            }

        except ClientError as e:
            logger.error(
                f"AWS error getting instance status: {e.response['Error']['Message']}"
            )
            return {
                "success": False,
                "error": e.response["Error"]["Message"],
                "error_code": e.response["Error"]["Code"],
            }
        except Exception as e:
            logger.error(f"Unexpected error getting instance status: {str(e)}")
            return {"success": False, "error": str(e)}

    def start_instance(self) -> Dict[str, Any]:
        """Start the UAT instance"""
        try:
            # First check current status
            status = self.get_instance_status()
            if not status["success"]:
                return status

            if status["state"] == "running":
                return {
                    "success": True,
                    "message": "Instance is already running",
                    "instance_id": self.uat_instance_id,
                    "state": "running",
                    "public_ip": status.get("public_ip"),
                }

            if status["state"] not in ["stopped", "stopping"]:
                return {
                    "success": False,
                    "error": (
                        f'Instance is in {status["state"]} state and cannot be '
                        "started"
                    ),
                }

            # Start the instance
            ec2 = self._get_ec2_client()
            response = ec2.start_instances(InstanceIds=[self.uat_instance_id])

            starting_instance = response["StartingInstances"][0]

            return {
                "success": True,
                "message": "Instance start initiated successfully",
                "instance_id": self.uat_instance_id,
                "previous_state": starting_instance["PreviousState"]["Name"],
                "current_state": starting_instance["CurrentState"]["Name"],
                "state_transition_reason": response.get("StateTransitionReason"),
            }

        except ClientError as e:
            logger.error(
                f"AWS error starting instance: {e.response['Error']['Message']}"
            )
            return {
                "success": False,
                "error": e.response["Error"]["Message"],
                "error_code": e.response["Error"]["Code"],
            }
        except Exception as e:
            logger.error(f"Unexpected error starting instance: {str(e)}")
            return {"success": False, "error": str(e)}

    def stop_instance(self) -> Dict[str, Any]:
        """Stop the UAT instance"""
        try:
            # First check current status
            status = self.get_instance_status()
            if not status["success"]:
                return status

            if status["state"] == "stopped":
                return {
                    "success": True,
                    "message": "Instance is already stopped",
                    "instance_id": self.uat_instance_id,
                    "state": "stopped",
                }

            if status["state"] not in ["running", "stopping"]:
                return {
                    "success": False,
                    "error": (
                        f'Instance is in {status["state"]} state and cannot be '
                        "stopped"
                    ),
                }

            # Stop the instance
            ec2 = self._get_ec2_client()
            response = ec2.stop_instances(InstanceIds=[self.uat_instance_id])

            stopping_instance = response["StoppingInstances"][0]

            return {
                "success": True,
                "message": "Instance stop initiated successfully",
                "instance_id": self.uat_instance_id,
                "previous_state": stopping_instance["PreviousState"]["Name"],
                "current_state": stopping_instance["CurrentState"]["Name"],
                "state_transition_reason": response.get("StateTransitionReason"),
            }

        except ClientError as e:
            logger.error(
                f"AWS error stopping instance: {e.response['Error']['Message']}"
            )
            return {
                "success": False,
                "error": e.response["Error"]["Message"],
                "error_code": e.response["Error"]["Code"],
            }
        except Exception as e:
            logger.error(f"Unexpected error stopping instance: {str(e)}")
            return {"success": False, "error": str(e)}

    def reboot_instance(self) -> Dict[str, Any]:
        """Reboot the UAT instance"""
        try:
            # First check current status
            status = self.get_instance_status()
            if not status["success"]:
                return status

            if status["state"] != "running":
                return {
                    "success": False,
                    "error": (
                        f'Instance is in {status["state"]} state and cannot be '
                        "rebooted. Instance must be running to reboot."
                    ),
                }

            # Reboot the instance
            ec2 = self._get_ec2_client()
            ec2.reboot_instances(InstanceIds=[self.uat_instance_id])

            return {
                "success": True,
                "message": "Instance reboot initiated successfully",
                "instance_id": self.uat_instance_id,
                "state": "rebooting",
            }

        except ClientError as e:
            logger.error(
                f"AWS error rebooting instance: {e.response['Error']['Message']}"
            )
            return {
                "success": False,
                "error": e.response["Error"]["Message"],
                "error_code": e.response["Error"]["Code"],
            }
        except Exception as e:
            logger.error(f"Unexpected error rebooting instance: {str(e)}")
            return {"success": False, "error": str(e)}
