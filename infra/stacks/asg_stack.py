from aws_cdk import (
    Stack,
    Duration,
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
)
from constructs import Construct
import os


def _load_user_data(efs_id: str, secret_db_name: str, secret_wp_name: str) -> ec2.UserData:
    script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "user_data.sh")
    with open(script_path, "r") as f:
        raw = f.read()
    raw = raw.replace('${EFS_ID}', efs_id)
    raw = raw.replace("prod/wordpress/db", secret_db_name)
    raw = raw.replace("prod/wordpress/app", secret_wp_name)
    user_data = ec2.UserData.for_linux()
    user_data.add_commands(raw)
    return user_data


def _get_lab_role(stack: Stack) -> iam.IRole:
    return iam.Role.from_role_arn(
        stack, "LabRole",
        f"arn:aws:iam::{stack.account}:role/LabRole",
        mutable=False,
    )


class AsgStackPrimary(Stack):
    def __init__(self, scope, construct_id: str, vpc_stack, sg_stack, alb_stack, efs_stack,
                 secret_db_name: str = "prod/wordpress/db",
                 secret_wp_name: str = "prod/wordpress/app", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        lab_role = _get_lab_role(self)

        launch_template = ec2.LaunchTemplate(
            self, "PrimaryLaunchTemplate",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.SMALL),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),
            security_group=sg_stack.asg_sg,
            role=lab_role,
            user_data=_load_user_data(efs_stack.file_system_id, secret_db_name, secret_wp_name),
            associate_public_ip_address=False,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(20, encrypted=True, volume_type=ec2.EbsDeviceVolumeType.GP3),
                )
            ],
        )

        self.asg = autoscaling.AutoScalingGroup(
            self, "PrimaryASG",
            vpc=vpc_stack.vpc,
            launch_template=launch_template,
            min_capacity=2,
            max_capacity=4,
            desired_capacity=2,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            health_check=autoscaling.HealthCheck.elb(grace=Duration.seconds(300)),
        )

        self.asg.attach_to_application_target_group(alb_stack.target_group)

        self.asg.scale_on_cpu_utilization(
            "TargetTrackingCPU", target_utilization_percent=70, cooldown=Duration.seconds(120),
        )

        cpu_metric = cloudwatch.Metric(
            namespace="AWS/EC2", metric_name="CPUUtilization",
            dimensions_map={"AutoScalingGroupName": self.asg.auto_scaling_group_name},
            period=Duration.minutes(5), statistic="Average",
        )

        self.asg.scale_on_metric(
            "StepScalingStressTest",
            metric=cpu_metric,
            scaling_steps=[
                autoscaling.ScalingInterval(lower=50, upper=70, change=+1),
                autoscaling.ScalingInterval(lower=70, change=+2),
                autoscaling.ScalingInterval(upper=20, change=-1),
            ],
            adjustment_type=autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
            cooldown=Duration.seconds(60),
        )


class AsgStackSecondary(Stack):
    def __init__(self, scope, construct_id: str, vpc_stack, sg_stack, alb_stack, efs_stack,
                 secret_db_name: str = "prod/wordpress/db",
                 secret_wp_name: str = "prod/wordpress/app", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        lab_role = _get_lab_role(self)

        launch_template = ec2.LaunchTemplate(
            self, "SecondaryLaunchTemplate",
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.SMALL),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),
            security_group=sg_stack.asg_sg,
            role=lab_role,
            user_data=_load_user_data(efs_stack.file_system_id, secret_db_name, secret_wp_name),
            associate_public_ip_address=False,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(20, encrypted=True, volume_type=ec2.EbsDeviceVolumeType.GP3),
                )
            ],
        )

        self.asg = autoscaling.AutoScalingGroup(
            self, "SecondaryASG",
            vpc=vpc_stack.vpc,
            launch_template=launch_template,
            min_capacity=2,
            max_capacity=4,
            desired_capacity=2,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            health_check=autoscaling.HealthCheck.elb(grace=Duration.seconds(300)),
        )

        self.asg.attach_to_application_target_group(alb_stack.target_group)

        self.asg.scale_on_cpu_utilization(
            "TargetTrackingCPU", target_utilization_percent=70, cooldown=Duration.seconds(120),
        )
