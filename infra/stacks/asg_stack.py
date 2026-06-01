import base64
import os
from aws_cdk import (
    Stack,
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    Duration,
    Fn,
)
from constructs import Construct


def _build_user_data(efs_id: str, secret_db_name: str, secret_wp_name: str) -> str:
    """
    Lit user_data.sh, remplace les placeholders et retourne le script en base64.
    Pas d'upload S3 → compatible BootstraplessSynthesizer.
    """
    script_path = os.path.join(os.path.dirname(__file__), "..", "script", "user_data.sh")
    with open(script_path, "r") as f:
        raw = f.read()
    raw = raw.replace("${EFS_ID}", efs_id)
    raw = raw.replace("prod/wordpress/db", secret_db_name)
    raw = raw.replace("prod/wordpress/app", secret_wp_name)
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


def _get_lab_role_arn(stack: Stack) -> str:
    return f"arn:aws:iam::{stack.account}:role/LabRole"


class AsgStackPrimary(Stack):
    def __init__(self, scope, construct_id: str, vpc_stack, sg_stack, alb_stack, efs_stack,
                 secret_db_name: str = "prod/wordpress/db",
                 secret_wp_name: str = "prod/wordpress/app", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        user_data_b64 = _build_user_data(
            efs_stack.file_system_id, secret_db_name, secret_wp_name
        )

        # L1 LaunchTemplate — pas d'assets, compatible BootstraplessSynthesizer
        lt = ec2.CfnLaunchTemplate(
            self, "PrimaryLaunchTemplate",
            launch_template_data=ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
                instance_type="t3.small",
                image_id=ec2.MachineImage.latest_amazon_linux2()
                    .get_image(self).image_id,
                security_group_ids=[sg_stack.asg_sg.ref],
                iam_instance_profile=ec2.CfnLaunchTemplate.IamInstanceProfileProperty(
                    arn=f"arn:aws:iam::{self.account}:instance-profile/LabInstanceProfile"
                ),
                user_data=user_data_b64,
                block_device_mappings=[
                    ec2.CfnLaunchTemplate.BlockDeviceMappingProperty(
                        device_name="/dev/xvda",
                        ebs=ec2.CfnLaunchTemplate.EbsProperty(
                            volume_size=20,
                            volume_type="gp3",
                            encrypted=True,
                            delete_on_termination=True,
                        ),
                    )
                ],
                monitoring=ec2.CfnLaunchTemplate.MonitoringProperty(enabled=True),
            ),
        )

        # Subnets web privés exposés directement depuis vpc_stack (L2 PrivateSubnet)
        subnet_ids = [
            vpc_stack.web_subnet_1.subnet_id,
            vpc_stack.web_subnet_2.subnet_id,
        ]

        self.asg = autoscaling.CfnAutoScalingGroup(
            self, "PrimaryASG",
            min_size="2",
            max_size="4",
            desired_capacity="2",
            vpc_zone_identifier=subnet_ids,
            launch_template=autoscaling.CfnAutoScalingGroup.LaunchTemplateSpecificationProperty(
                launch_template_id=lt.ref,
                version=lt.attr_latest_version_number,
            ),
            target_group_arns=[alb_stack.target_group_arn],
            health_check_type="ELB",
            health_check_grace_period=300,
            tags=[
                autoscaling.CfnAutoScalingGroup.TagPropertyProperty(
                    key="Name", value="wordpress-asg-primary", propagate_at_launch=True
                )
            ],
        )

        # Target Tracking CPU 70 %
        autoscaling.CfnScalingPolicy(
            self, "TargetTrackingCPU",
            auto_scaling_group_name=self.asg.ref,
            policy_type="TargetTrackingScaling",
            target_tracking_configuration=autoscaling.CfnScalingPolicy.TargetTrackingConfigurationProperty(
                target_value=70.0,
                predefined_metric_specification=autoscaling.CfnScalingPolicy.PredefinedMetricSpecificationProperty(
                    predefined_metric_type="ASGAverageCPUUtilization",
                ),
                disable_scale_in=False,
            ),
        )

        # Step Scaling pour stress-test
        cpu_alarm_high = cloudwatch.CfnAlarm(
            self, "CpuAlarmHigh",
            alarm_description="CPU > 70% — scale out",
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            dimensions=[cloudwatch.CfnAlarm.DimensionProperty(
                name="AutoScalingGroupName", value=self.asg.ref
            )],
            period=300,
            evaluation_periods=1,
            statistic="Average",
            threshold=70,
            comparison_operator="GreaterThanThreshold",
        )

        step_out = autoscaling.CfnScalingPolicy(
            self, "StepScaleOut",
            auto_scaling_group_name=self.asg.ref,
            policy_type="StepScaling",
            adjustment_type="ChangeInCapacity",
            cooldown="60",
            step_adjustments=[
                autoscaling.CfnScalingPolicy.StepAdjustmentProperty(
                    metric_interval_lower_bound=0, metric_interval_upper_bound=20, scaling_adjustment=1
                ),
                autoscaling.CfnScalingPolicy.StepAdjustmentProperty(
                    metric_interval_lower_bound=20, scaling_adjustment=2
                ),
            ],
        )
        cpu_alarm_high.alarm_actions = [step_out.ref]


class AsgStackSecondary(Stack):
    def __init__(self, scope, construct_id: str, vpc_stack, sg_stack, alb_stack, efs_stack,
                 secret_db_name: str = "prod/wordpress/db",
                 secret_wp_name: str = "prod/wordpress/app", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        user_data_b64 = _build_user_data(
            efs_stack.file_system_id, secret_db_name, secret_wp_name
        )

        lt = ec2.CfnLaunchTemplate(
            self, "SecondaryLaunchTemplate",
            launch_template_data=ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
                instance_type="t3.small",
                image_id=ec2.MachineImage.latest_amazon_linux2()
                    .get_image(self).image_id,
                security_group_ids=[sg_stack.asg_sg.ref],
                iam_instance_profile=ec2.CfnLaunchTemplate.IamInstanceProfileProperty(
                    arn=f"arn:aws:iam::{self.account}:instance-profile/LabInstanceProfile"
                ),
                user_data=user_data_b64,
                block_device_mappings=[
                    ec2.CfnLaunchTemplate.BlockDeviceMappingProperty(
                        device_name="/dev/xvda",
                        ebs=ec2.CfnLaunchTemplate.EbsProperty(
                            volume_size=20,
                            volume_type="gp3",
                            encrypted=True,
                            delete_on_termination=True,
                        ),
                    )
                ],
                monitoring=ec2.CfnLaunchTemplate.MonitoringProperty(enabled=True),
            ),
        )

        subnet_ids = [
            vpc_stack.web_subnet_1.subnet_id,
            vpc_stack.web_subnet_2.subnet_id,
        ]

        self.asg = autoscaling.CfnAutoScalingGroup(
            self, "SecondaryASG",
            min_size="2",
            max_size="4",
            desired_capacity="2",
            vpc_zone_identifier=subnet_ids,
            launch_template=autoscaling.CfnAutoScalingGroup.LaunchTemplateSpecificationProperty(
                launch_template_id=lt.ref,
                version=lt.attr_latest_version_number,
            ),
            target_group_arns=[alb_stack.target_group_arn],
            health_check_type="ELB",
            health_check_grace_period=300,
            tags=[
                autoscaling.CfnAutoScalingGroup.TagPropertyProperty(
                    key="Name", value="wordpress-asg-secondary", propagate_at_launch=True
                )
            ],
        )

        autoscaling.CfnScalingPolicy(
            self, "TargetTrackingCPU",
            auto_scaling_group_name=self.asg.ref,
            policy_type="TargetTrackingScaling",
            target_tracking_configuration=autoscaling.CfnScalingPolicy.TargetTrackingConfigurationProperty(
                target_value=70.0,
                predefined_metric_specification=autoscaling.CfnScalingPolicy.PredefinedMetricSpecificationProperty(
                    predefined_metric_type="ASGAverageCPUUtilization",
                ),
                disable_scale_in=False,
            ),
        )