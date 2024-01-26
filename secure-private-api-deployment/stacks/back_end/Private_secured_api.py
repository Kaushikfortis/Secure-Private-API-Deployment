from aws_cdk import aws_ec2 as _ec2
from aws_cdk import aws_iam as _iam
from aws_cdk import aws_logs as _logs
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_apigateway as _apigw
from aws_cdk import core
import os


class GlobalArgs:
    """
    Helper to define global statics
    """

    owner = "TagTagDhanyalmation"
    ENVIRONMENT = "production"
    REPO_NAME = "secure-private-api-deployment"
    SOURCE_INFO = f"https://github.com/TagDhanyal/{REPO_NAME}"
    VERSION = "2020_07_30"
    email_noti = ["dhanyal712@gmail.com", ]


class SecurePrivateApiStack(core.Stack):

    def __init__(
        self,
        scope: core.Construct,
        id: str,
        vpc,
        stack_log_level: str,
        back_end_api_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Create Serverless Event Processor using Lambda):
        # Read Lambda Code):
        try:
            with open("Private_secured_api/stacks/back_end/lambda_src/serverless_hello.py", mode="r") as f:
                serverless_py_code = f.read()
        except OSError as e:
            print("Unable to read Lambda Function Code")
            raise e
        # Creating lambda Function
        serverless_py = _lambda.Function(
            self,
            "securehelloFn",
            function_name=f"serverless_py_{id}",
            runtime=_lambda.Runtime.PYTHON_3_7,
            handler="index.lambda_handler",
            code=_lambda.InlineCode(serverless_py_code),
            timeout=core.Duration.seconds(15),
            reserved_concurrent_executions=1,
            environment={
                "LOG_LEVEL": f"{stack_log_level}",
                "Environment": "Production",
                "ANDON_CORD_PULLED": "False"
            }
        )
        serverless_py_version = serverless_py.latest_version
        serverless_py_version_alias = _lambda.Alias(
            self,
            "helloFnAlias",
            alias_name="TagTagDhanyalmation",
            version=serverless_py_version
        )

        # Create Custom Loggroup
        # /aws/lambda/function-name
        serverless_py_lg = _logs.LogGroup(
            self,
            "cloudwatchLoggroup",
            log_group_name=f"/aws/lambda/{serverless_py.function_name}",
            retention=_logs.RetentionDays.ONE_WEEK,
            removal_policy=core.RemovalPolicy.DESTROY
        )

        # Add API GW front end for the Lambda
        back_end_01_api_stage_options = _apigw.StageOptions(
            stage_name="prod",
            throttling_rate_limit=10,
            throttling_burst_limit=100,
            logging_level=_apigw.MethodLoggingLevel.INFO
        )

        # Lets create a private secure end point

        # Create a security group dedicated to our API Endpoint
        self.private_apigw_sec_grp = _ec2.SecurityGroup(
            self,
            "secureApi01SecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            description="adding SG to our private API"
        )

        # Allow 443 inbound on our Security Group
        self.private_apigw_sec_grp.add_ingress_rule(
            _ec2.Peer.ipv4(vpc.vpc_cidr_block),
            _ec2.Port.tcp(443)
        )

        interface_vpcepoint = _ec2.InterfaceVpcEndpoint(
            self,
            "interface_vpcepoint",
            vpc=vpc,
            service=_ec2.InterfaceVpcEndpointAwsService.APIGATEWAY,
            private_dns_enabled=True,
            subnets=_ec2.SubnetSelection(
                subnet_type=_ec2.SubnetType.ISOLATED
            )
        )

        # Create a API Gateway Resource Policy to attach to API GW
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-apigateway-restapi.html#cfn-apigateway-restapi-policy
        private_apigw_res_policy = _iam.PolicyDocument(
            statements=[
                _iam.PolicyStatement(
                    principals=[_iam.AnyPrincipal()],
                    actions=["execute-api:Invoke"],
                    # resources=[f"{api_01.arn_for_execute_api(method="GET",path="hello", stage="miztiik")}"],
                    resources=[core.Fn.join("", ["execute-api:/", "*"])],
                    effect=_iam.Effect.DENY,
                    conditions={
                        "StringNotEquals":
                        {
                            "aws:sourceVpc": f"{interface_vpcepoint.vpc_endpoint_id}"
                        }
                    },
                    sid="DenyAllNonVPCAccessToApi"
                ),
                _iam.PolicyStatement(
                    principals=[_iam.AnyPrincipal()],
                    actions=["execute-api:Invoke"],
                    resources=[core.Fn.join("", ["execute-api:/", "*"])],
                    effect=_iam.Effect.ALLOW,
                    sid="AllowVPCAccessToApi"
                )
            ]
        )

        # Create API Gateway
        private_apigw = _apigw.RestApi(
            self,
            "secbackendAPI",
            rest_api_name=f"{back_end_api_name}",
            deploy_options=back_end_01_api_stage_options,
            endpoint_types=[
                _apigw.EndpointType.PRIVATE
            ],
            policy=private_apigw_res_policy,
        )

        back_end_01_api_res = private_apigw.root.add_resource("secure")
        hello = back_end_01_api_res.add_resource("hello")

        hello_method_get = hello.add_method(
            http_method="GET",
            request_parameters={
                "method.request.header.InvocationType": True,
                "method.request.path.number": True
            },
            integration=_apigw.LambdaIntegration(
                handler=serverless_py,
                proxy=True
            )
        )

        # Outputs
        output_1 = core.CfnOutput(
            self,
            "SecureApiUrl",
            value=f"{hello.url}",
            description="Use an utility like curl from the same VPC as the API to invoke it."
        )