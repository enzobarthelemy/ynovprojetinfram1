import os
from aws_cdk import (
    Stack,
    CfnParameter,
    Fn,
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_cloudwatch as cloudwatch,
)
from constructs import Construct


def _build_user_data(efs_id_value, secret_db_name: str, secret_wp_name: str):
    """
    Lit user_data.sh, remplace les noms de secrets (statiques) en Python,
    puis injecte l'EFS_ID via Fn.join (résolu au deploy, pas figé au synth).
    Fn.join évite les problèmes d'échappement des variables bash ${...} de Fn.sub.
    Retourne un token Fn.base64 — compatible BootstraplessSynthesizer (pas d'asset).
    """
    script_path = os.path.join(os.path.dirname(__file__), "..", "script", "user_data.sh")
    with open(script_path, "r") as f:
        raw = f.read()

    # Remplacements statiques (chaînes littérales, pas de token)
    raw = raw.replace("prod/wordpress/db", secret_db_name)
    raw = raw.replace("prod/wordpress/app", secret_wp_name)

    # Découpe sur le placeholder ${EFS_ID} puis rejoint avec la vraie valeur
    parts = raw.split("${EFS_ID}")
    joined = Fn.join(efs_id_value, parts)
    return Fn.base64(joined)


class AsgStackPrimary(Stack):
    def __init__(self, scope, construct_id: str, vpc_stack, sg_stack, alb_stack,
                 secret_db_name: str = "prod/wordpress/db",
                 secret_wp_name: str = "prod/wordpress/app", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # EFS ID passé au deploy via parameter-overrides (récupéré depuis EfsStackPrimary)
        efs_id = CfnParameter(self, "EfsId", type="String").value_as_string

        user_data_b64 = _build_user_data(efs_id, secret_db_name, secret_wp_name)

        lt = ec2.CfnLaunchTemplate(
            self, "PrimaryLaunchTemplate",
            launch_template_data=ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
                instance_type="t3.small",
                image_id=ec2.MachineImage.latest_amazon_linux2().get_image(self).image_id,
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
            # Politique de maintenance : zero interruption lors des remplacements d'instances
            instance_maintenance_policy=autoscaling.CfnAutoScalingGroup.InstanceMaintenancePolicyProperty(
                min_healthy_percentage=100,  # garde 100% de la capacite active
                max_healthy_percentage=200,  # double temporairement (nouveau avant de couper l'ancien)
            ),
            tags=[
                autoscaling.CfnAutoScalingGroup.TagPropertyProperty(
                    key="Name", value="wordpress-asg-primary", propagate_at_launch=True
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
    def __init__(self, scope, construct_id: str, vpc_stack, sg_stack, alb_stack,
                 secret_db_name: str = "prod/wordpress/db",
                 secret_wp_name: str = "prod/wordpress/app", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        efs_id = CfnParameter(self, "EfsId", type="String").value_as_string

        user_data_b64 = _build_user_data(efs_id, secret_db_name, secret_wp_name)

        lt = ec2.CfnLaunchTemplate(
            self, "SecondaryLaunchTemplate",
            launch_template_data=ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
                instance_type="t3.small",
                image_id=ec2.MachineImage.latest_amazon_linux2().get_image(self).image_id,
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
            # Politique de maintenance : zero interruption lors des remplacements d'instances
            instance_maintenance_policy=autoscaling.CfnAutoScalingGroup.InstanceMaintenancePolicyProperty(
                min_healthy_percentage=100,
                max_healthy_percentage=200,
            ),
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
