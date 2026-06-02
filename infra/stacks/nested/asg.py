import os
from aws_cdk import (
    NestedStack,
    Fn,
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_cloudwatch as cloudwatch,
)
from constructs import Construct


def _build_user_data(efs_id, rds_host):
    """
    Construit le user_data en injectant EFS_ID et RDS_HOST via tokens CDK (Fn.join).
    Le script lit ces valeurs en variables d'env (exportees dans l'entete).
    Les variables bash ${...} du script restent intactes (pas de Fn.sub).
    """
    script_path = os.path.join(os.path.dirname(__file__), "..", "..", "script", "user_data.sh")
    with open(script_path, "r") as f:
        raw = f.read()

    # Retire le shebang d'origine (on ajoute notre entete avec les exports)
    lines = raw.split("\n", 1)
    body = lines[1] if len(lines) > 1 else ""

    return Fn.base64(Fn.join("", [
        "#!/bin/bash\n",
        "export EFS_ID='", efs_id, "'\n",
        "export RDS_HOST='", rds_host, "'\n",
        body,
    ]))


class AsgNested(NestedStack):
    """
    Auto Scaling Group (L1) + Launch Template + scaling policies.
    Recoit subnets web, asg_sg, target_group_arn, efs_id, rds_host directement.
    """

    def __init__(self, scope: Construct, construct_id: str, *,
                 web_subnet_ids: list, asg_sg_id: str, target_group_arn: str,
                 efs_id: str, rds_host: str, name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account_id = self.account
        user_data_b64 = _build_user_data(efs_id, rds_host)

        lt = ec2.CfnLaunchTemplate(self, "LaunchTemplate",
            launch_template_data=ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
                instance_type="t3.small",
                image_id=ec2.MachineImage.latest_amazon_linux2().get_image(self).image_id,
                security_group_ids=[asg_sg_id],
                iam_instance_profile=ec2.CfnLaunchTemplate.IamInstanceProfileProperty(
                    arn=f"arn:aws:iam::{account_id}:instance-profile/LabInstanceProfile"),
                user_data=user_data_b64,
                block_device_mappings=[ec2.CfnLaunchTemplate.BlockDeviceMappingProperty(
                    device_name="/dev/xvda",
                    ebs=ec2.CfnLaunchTemplate.EbsProperty(
                        volume_size=20, volume_type="gp3", encrypted=True,
                        delete_on_termination=True))],
                monitoring=ec2.CfnLaunchTemplate.MonitoringProperty(enabled=True),
            ),
        )

        self.asg = autoscaling.CfnAutoScalingGroup(self, "Asg",
            min_size="2", max_size="4", desired_capacity="2",
            vpc_zone_identifier=web_subnet_ids,
            launch_template=autoscaling.CfnAutoScalingGroup.LaunchTemplateSpecificationProperty(
                launch_template_id=lt.ref, version=lt.attr_latest_version_number),
            target_group_arns=[target_group_arn],
            health_check_type="ELB",
            health_check_grace_period=300,
            instance_maintenance_policy=autoscaling.CfnAutoScalingGroup.InstanceMaintenancePolicyProperty(
                min_healthy_percentage=100, max_healthy_percentage=200),
            tags=[autoscaling.CfnAutoScalingGroup.TagPropertyProperty(
                key="Name", value=f"wordpress-asg-{name}", propagate_at_launch=True)],
        )

        # Target Tracking CPU 70%
        autoscaling.CfnScalingPolicy(self, "TargetTrackingCPU",
            auto_scaling_group_name=self.asg.ref,
            policy_type="TargetTrackingScaling",
            target_tracking_configuration=autoscaling.CfnScalingPolicy.TargetTrackingConfigurationProperty(
                target_value=70.0,
                predefined_metric_specification=autoscaling.CfnScalingPolicy.PredefinedMetricSpecificationProperty(
                    predefined_metric_type="ASGAverageCPUUtilization"),
                disable_scale_in=False),
        )
