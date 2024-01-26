#!/usr/bin/env python3

from aws_cdk import core

from Private_secured_api.stacks.back_end.vpc_stack import VpcStack
from Private_secured_api.stacks.back_end.Private_secured_api import SecurePrivateApiStack
from Private_secured_api.stacks.back_end.public_api import UnSecurePublicApiStack
from Private_secured_api.stacks.back_end.api_trigger import ApiConsumerStack


app = core.App()

# VPC Stack for hosting Secure API & Other resources
vpc_stack = VpcStack(
    app, "secure-private-api-deployment-vpc-stack",
    description="VPC Stack for hosting Secure API & Other resources"
)

# Deploy an unsecure public API
unsecure_public_api = UnSecurePublicApiStack(
    app,
    "unsecure-public-api",
    stack_log_level="INFO",
    back_end_api_name="unsecure_public_api_01",
    description="Deploy an unsecure public API"
)

# Secure your API by create private EndPoint to make it accessible from your VPCs
Private_secured_api = SecurePrivateApiStack(
    app,
    "secure-private-api-deployment",
    vpc=vpc_stack.vpc,
    stack_log_level="INFO",
    back_end_api_name="private_apigw",
    description="Secure your API by create private EndPoint to make it accessible from your VPCs"
)

# Launch an EC2 Instance in a given VPC
api_consumer_stack = ApiConsumerStack(
    app,
    "api-consumer",
    vpc=vpc_stack.vpc,
    api_sec_grp=Private_secured_api.private_apigw_sec_grp,
    stack_log_level="INFO",
    description="Launch an EC2 Instance in a given VPC"
)

app.synth()
