"""
Lambda Function: Execution Handler (Simplified)
Execute agent recommendations with context retention
Triggered by API Gateway from Teams Execute button
Uses same patterns as analysis Lambda: urllib, Cognito, Bedrock AgentCore
"""

import boto3
import json
import os
import urllib.parse
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# CRITICAL: Bypass tool consent prompts for automated execution
os.environ['BYPASS_TOOL_CONSENT'] = 'true'

AWS_REGION = 'ap-southeast-1'

s3 = boto3.client("s3")
# dynamodb = boto3.resource("dynamodb")  # Commented out - not using DynamoDB in simple version
# sns = boto3.client("sns")  # Commented out - not using SNS in simple version


def get_cognito_jwt_token(username, password, client_id, user_pool_id):
    """Get JWT access token from AWS Cognito (same as analysis Lambda)"""
    # Extract region from User Pool ID (format: region_poolId)
    cognito_region = user_pool_id.split('_')[0] if user_pool_id else "ap-southeast-1"

    print(f"Using Cognito region: {cognito_region} (from pool: {user_pool_id})")
    cognito_client = boto3.client("cognito-idp", region_name=cognito_region)

    try:
        response = cognito_client.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
        return response["AuthenticationResult"]["AccessToken"]
    except Exception as e:
        print(f"Error getting Cognito token: {e}")
        return None


def lambda_handler(event, context):
    """
    Execute agent recommendations with context retention
    Triggered by API Gateway from Teams Execute button

    Expected query parameters:
    - alert_id: Unique alert identifier
    - session_id: Agent session ID from analysis phase
    - service_name: Name of the service being analyzed
    - s3_key: (Optional) S3 key to full analysis
    - async: (Optional) Set to "true" for async invocation
    """
    print(f"Execution handler invoked with event: {json.dumps(event)}")

    try:
        # Parse API Gateway query parameters
        query_params = event.get('queryStringParameters', {}) or {}

        # Check if this is an async background invocation
        is_async = query_params.get("async") == "true"

        if not query_params:
            print("ERROR: No query parameters provided")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Query parameters required"}),
            }

        alert_id = query_params.get("alert_id")
        session_id = query_params.get("session_id")
        service_name = query_params.get("service_name", "unknown-service")
        s3_analysis_key = query_params.get("s3_key")

        if not alert_id:
            print("ERROR: alert_id is required")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "alert_id is required"}),
            }

        if not session_id:
            print("ERROR: session_id is required")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "session_id is required"}),
            }

        # If NOT async, invoke self asynchronously and return immediate response
        if not is_async:
            print(f"🚀 Triggering async auto-execution for alert {alert_id}")

            # Invoke this same Lambda function asynchronously
            lambda_client = boto3.client('lambda')

            # Create async payload with same params + async flag
            async_params = query_params.copy()
            async_params['async'] = 'true'

            async_event = event.copy()
            async_event['queryStringParameters'] = async_params

            try:
                lambda_client.invoke(
                    FunctionName=context.function_name,
                    InvocationType='Event',  # Async invocation
                    Payload=json.dumps(async_event)
                )
                print(f"✅ Async auto-execution triggered successfully")
            except Exception as e:
                print(f"⚠️ Failed to trigger async execution: {e}")
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "status": "error",
                        "message": f"Failed to trigger execution: {str(e)}"
                    })
                }

            # Return simple JSON response
            return {
                "statusCode": 202,  # Accepted
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "status": "accepted",
                    "message": "Execution started. Results will be saved to S3.",
                    "alert_id": alert_id,
                    "service_name": service_name,
                    "session_id": session_id
                })
            }

        # If async=true, proceed with actual execution
        print(f"🔄 Processing execution for alert {alert_id}")
        print(f"📋 Service: {service_name}, Session ID: {session_id}")

        # Retrieve full analysis from S3 if key provided
        full_analysis = None
        if s3_analysis_key:
            full_analysis = get_analysis_from_s3(s3_analysis_key)
            if not full_analysis:
                print("⚠️ Could not retrieve full analysis from S3")

        # Execute agent recommendations with context retention (ALWAYS AUTO-EXECUTE)
        execution_result = execute_with_agent(
            service_name=service_name,
            full_analysis=full_analysis,
            session_id=session_id,
            alert_id=alert_id,
            is_approved=True,  # Always auto-execute
        )

        # Upload execution results to S3
        execution_s3_key = upload_execution_results(
            alert_id=alert_id,
            service_name=service_name,
            execution_result=execution_result
        )

        print(f"✅ Execution completed for alert {alert_id}")
        print(f"📄 Results saved to S3: {execution_s3_key}")

        # Return JSON response
        status_text = "SUCCESS" if execution_result["success"] else "FAILED"

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": status_text,
                "alert_id": alert_id,
                "service_name": service_name,
                "session_id": session_id,
                "s3_key": execution_s3_key,
                "message": f"Execution {status_text.lower()}. Results saved to S3."
            })
        }

    except Exception as e:
        print(f"❌ ERROR: Execution failed: {e}")
        import traceback
        traceback.print_exc()

        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        }


# def get_alert_from_dynamodb(alert_id):
#     """Retrieve alert data from DynamoDB"""
#     try:
#         dynamodb_table = os.environ.get("DYNAMODB_ALERTS_TABLE")
#         if not dynamodb_table:
#             print("ERROR: DYNAMODB_ALERTS_TABLE environment variable not set")
#             return None

#         table = dynamodb.Table(dynamodb_table)
#         response = table.get_item(Key={"alert_id": alert_id})

#         if "Item" in response:
#             return response["Item"]
#         else:
#             return None
#     except Exception as e:
#         print(f"Error retrieving alert from DynamoDB: {e}")
#         return None


def get_analysis_from_s3(s3_key):
    """Retrieve full analysis from S3"""
    try:
        s3_bucket = os.environ.get("S3_ANALYSIS_BUCKET")
        if not s3_bucket:
            print("ERROR: S3_ANALYSIS_BUCKET environment variable not set")
            return None

        response = s3.get_object(Bucket=s3_bucket, Key=s3_key)
        analysis_content = response["Body"].read().decode("utf-8")

        print(f"Retrieved analysis from S3: {len(analysis_content)} characters")
        return analysis_content
    except Exception as e:
        print(f"Error retrieving analysis from S3: {e}")
        return None


def execute_with_agent(service_name, full_analysis, session_id, alert_id, is_approved=False):
    """
    Execute agent recommendations with context retention
    Uses the same session_id to maintain conversation context

    Args:
        is_approved: If True, agent executes automatically. If False, agent creates execution plan for approval.
    """
    print(f"⚡ {'Executing' if is_approved else 'Planning'} recommendations for service: {service_name}")
    print(f"🔗 Using session_id: {session_id}")
    print(f"✅ Approved: {is_approved}")

    try:
        # Construct execution prompt with context from analysis
        execution_prompt = construct_execution_prompt(service_name, full_analysis, is_approved)

        # Invoke agent with context retention (using same API as analysis)
        execution_response = invoke_agent_for_execution(
            prompt=execution_prompt, session_id=session_id
        )

        print(f"📊 Agent execution response: {len(execution_response)} characters")

        # Parse execution results
        execution_log = parse_execution_log(execution_response)

        return {
            "success": True,
            "execution_log": execution_response,
            "details": execution_log,
        }

    except Exception as e:
        print(f"❌ Error during agent execution: {e}")
        import traceback

        traceback.print_exc()

        return {
            "success": False,
            "execution_log": f"Execution failed: {str(e)}",
            "details": {"error": str(e), "traceback": traceback.format_exc()},
        }


def construct_execution_prompt(service_name, full_analysis, is_approved=False):
    """
    Construct execution prompt with context from analysis
    References the previous analysis to maintain context

    Args:
        is_approved: If True, generate auto-execution prompt. If False, generate planning/approval prompt.
    """
    # Include analysis context if available
    analysis_context = ""
    if full_analysis:
        # Include full analysis for complete context (critical for execution)
        analysis_context = f"""
**PREVIOUS ANALYSIS SUMMARY:**
{full_analysis}

---
"""

    if is_approved:
        # AUTO-EXECUTION MODE: Natural conversational approach with explicit authorization
        prompt = f"""Thanks for your earlier analysis of {service_name}. I've reviewed and approved your recommendations - please go ahead and implement them now.

{analysis_context}

I'm authorizing you to implement the remediation actions above. Use your use_aws tool to make the necessary AWS changes for {service_name}.

Please document each action as you execute it:
- ✅ Action description (what you're doing)
- 🔧 The use_aws tool call parameters
- 📊 Status (✅ Success / ❌ Failed / ⏭️ Skipped)
- 📝 Output/result from use_aws
- ✔️ Verification results

Format your response with:
- Start: "🚀 **EXECUTION PHASE STARTING**"
- Document each action with clear status indicators
- End: "✅ **EXECUTION COMPLETE**" with summary (successful/failed/skipped counts)

This format helps me parse and display the results properly.
"""
    else:
        # PLANNING MODE: Create execution plan for user approval
        prompt = f"""EXECUTION PLANNING: Create a detailed execution plan for {service_name} remediation.

{analysis_context}

**📋 PLANNING MODE**

You are in PLANNING mode. Based on your previous analysis, create a detailed execution plan for the user to review and approve.

**YOUR TASKS:**

1. **Review Previous Analysis**: Recall the issues and recommendations from your analysis of {service_name}

2. **Create Execution Plan**: List all actions you will take, including:
   - What will be changed (IAM policies, Lambda configs, etc.)
   - Which AWS resources will be modified
   - Specific permissions or configurations to add
   - Expected impact and risks
   - Verification steps

3. **Ask Clarifying Questions** (if needed):
   - S3 bucket names or paths if not clear
   - Confirmation of resource names
   - Any ambiguous configurations
   - Risk tolerance (production vs. staging)

4. **Provide Risk Assessment**:
   - What could go wrong
   - Impact on running services
   - Rollback procedures if needed

**OUTPUT FORMAT:**

## 📋 Execution Plan for {service_name}

### Identified Issues:
[List issues from analysis]

### Proposed Actions:
1. **Action 1**: [Description]
   - Resource: [AWS resource to modify]
   - Change: [What will change]
   - Risk: [Low/Medium/High]

2. **Action 2**: [Description]
   ...

### Clarifying Questions:
[Any questions that need answers before execution]

### Risk Assessment:
- **Impact**: [Service disruption, configuration changes, etc.]
- **Rollback**: [How to undo if needed]

### Approval Required:
Please review the above plan. If you approve, click the "Approve & Execute" button to proceed.

**CREATE THE EXECUTION PLAN NOW.**
"""

    return prompt


def invoke_agent_for_execution(prompt, session_id):
    """
    Invoke Bedrock AgentCore API for execution with session retention
    Uses same pattern as analysis Lambda: urllib + Bedrock AgentCore
    Reuses the same session_id from analysis phase for context continuity
    """
    runtime_arn = os.environ.get("AGENT_RUNTIME_ARN")
    cognito_username = os.environ.get("COGNITO_USERNAME")
    cognito_password = os.environ.get("COGNITO_PASSWORD")
    cognito_client_id = os.environ.get("COGNITO_CLIENT_ID")
    cognito_user_pool_id = os.environ.get("COGNITO_USER_POOL_ID", "ap-southeast-1_jjG5DkVCy")

    if not all([runtime_arn, cognito_username, cognito_password, cognito_client_id]):
        raise ValueError("Agent configuration incomplete - missing environment variables")

    print(f"🚀 Invoking Bedrock AgentCore for execution...")

    try:
        # Get JWT token (same as analysis Lambda)
        jwt_token = get_cognito_jwt_token(
            cognito_username, cognito_password, cognito_client_id, cognito_user_pool_id
        )

        if not jwt_token:
            raise ValueError("Failed to obtain JWT token from Cognito")

        # Prepare agent invocation URL (same pattern as analysis)
        escaped_agent_arn = urllib.parse.quote(runtime_arn, safe="")
        url = f"https://bedrock-agentcore.{AWS_REGION}.amazonaws.com/runtimes/{escaped_agent_arn}/invocations?qualifier=DEFAULT"

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        }

        payload = {
            "prompt": prompt,
            "session_id": session_id,  # CRITICAL: Reuse session for context
            "actor_id": cognito_username,
        }

        print(f"📡 Invoking agent with session: {session_id}")

        # Invoke agent with streaming (same as analysis Lambda)
        req = Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers
        )

        response = urlopen(req, timeout=120)  # Longer timeout for execution

        if response.status in [200, 202]:
            agent_response = ""
            # Collect streaming response
            for line in response:
                if line:
                    decoded_line = line.decode("utf-8")
                    if decoded_line.startswith("data: "):
                        data_content = decoded_line[6:]
                        try:
                            data_json = json.loads(data_content)
                            if data_json.get("type") == "text_delta":
                                agent_response += data_json.get("content", "")
                        except json.JSONDecodeError:
                            pass

            # Format the agent response - convert escaped characters
            formatted_response = (
                agent_response.replace("\\n", "\n")
                .replace("\\ud83d\\udea8", "🚨")
                .replace("\\ud83d\\udccb", "📋")
                .replace("\\ud83d\\udd0d", "🔍")
                .replace("\\u2705", "✅")
                .replace("\\u26a0\\ufe0f", "⚠️")
                .replace("\\u274c", "❌")
                .replace("\\ud83d\\udcca", "📊")
                .replace("\\ud83d\\udd34", "🔴")
                .replace("\\ud83d\\udd27", "🔧")
                .replace("\\u2192", "→")
            )

            print(f"✅ Agent execution completed ({len(formatted_response)} chars)")
            return formatted_response
        else:
            raise Exception(f"Agent invocation failed with status: {response.status}")

    except TimeoutError:
        print("⏱️ Agent request timed out")
        raise
    except URLError as e:
        if isinstance(e.reason, TimeoutError):
            print("⏱️ Agent request timed out")
        else:
            print(f"❌ Error invoking agent: {e}")
        raise
    except Exception as e:
        print(f"❌ Error invoking agent for execution: {e}")
        raise


def parse_execution_log(execution_response):
    """
    Parse execution response to extract structured log
    Returns dictionary of executed actions with status
    """
    execution_log = {
        "actions": [],
        "summary": {"total_actions": 0, "successful": 0, "failed": 0, "skipped": 0},
    }

    try:
        # Simple parsing - look for action markers
        lines = execution_response.split("\n")

        current_action = None
        for line in lines:
            line_lower = line.lower()

            # Detect action start
            if "action:" in line_lower or "executing:" in line_lower:
                if current_action:
                    execution_log["actions"].append(current_action)

                current_action = {
                    "description": line.strip(),
                    "status": "unknown",
                    "timestamp": datetime.now().isoformat(),
                }

            # Detect status
            elif current_action:
                if "success" in line_lower or "✓" in line or "✅" in line:
                    current_action["status"] = "success"
                    execution_log["summary"]["successful"] += 1
                elif (
                    "fail" in line_lower
                    or "error" in line_lower
                    or "✗" in line
                    or "❌" in line
                ):
                    current_action["status"] = "failed"
                    execution_log["summary"]["failed"] += 1
                elif "skip" in line_lower:
                    current_action["status"] = "skipped"
                    execution_log["summary"]["skipped"] += 1

        # Add last action
        if current_action:
            execution_log["actions"].append(current_action)

        execution_log["summary"]["total_actions"] = len(execution_log["actions"])

    except Exception as e:
        print(f"Error parsing execution log: {e}")

    return execution_log


# COMMENTED OUT - Not using DynamoDB in simplified version
# def update_execution_status(alert_id, status, execution_log, execution_details):
#     """Update DynamoDB with execution status"""
#     try:
#         dynamodb_table = os.environ.get("DYNAMODB_ALERTS_TABLE")
#         if not dynamodb_table:
#             print("ERROR: DYNAMODB_ALERTS_TABLE not set")
#             return False
#
#         dynamodb = boto3.resource("dynamodb")
#         table = dynamodb.Table(dynamodb_table)
#
#         table.update_item(
#             Key={"alert_id": alert_id},
#             UpdateExpression="""
#                 SET execution_status = :status,
#                     executed_at = :time,
#                     execution_log = :log,
#                     execution_details = :details
#             """,
#             ExpressionAttributeValues={
#                 ":status": status,
#                 ":time": datetime.now().isoformat(),
#                 ":log": execution_log,
#                 ":details": json.dumps(execution_details),
#             },
#         )
#
#         print(f"Execution status updated in DynamoDB: {status}")
#         return True
#
#     except Exception as e:
#         print(f"Error updating execution status: {e}")
#         return False


def upload_execution_results(alert_id, service_name, execution_result):
    """Upload execution results to S3 as markdown"""
    try:
        s3_bucket = os.environ.get("S3_ANALYSIS_BUCKET")
        if not s3_bucket:
            print("⚠️ S3_ANALYSIS_BUCKET not set - skipping S3 upload")
            return None

        # Sanitize service_name for use in path
        safe_service_name = (
            service_name.replace("/", "-").replace(":", "-").replace(" ", "-")
        )

        # Create markdown document
        markdown_content = f"""# Execution Results: {service_name}

**Alert ID:** `{alert_id}`
**Service:** {service_name}
**Execution Time:** {datetime.now().isoformat()}
**Status:** {'✅ SUCCESS' if execution_result['success'] else '❌ FAILED'}

---

## Execution Log

```
{execution_result['execution_log']}
```

---

## Execution Summary

"""

        # Add structured summary
        if "details" in execution_result and "summary" in execution_result["details"]:
            summary = execution_result["details"]["summary"]
            markdown_content += f"""
- **Total Actions:** {summary.get('total_actions', 0)}
- **Successful:** {summary.get('successful', 0)} ✅
- **Failed:** {summary.get('failed', 0)} ❌
- **Skipped:** {summary.get('skipped', 0)} ⏭️

### Actions Performed

"""

            for action in execution_result["details"].get("actions", []):
                status_icon = {
                    "success": "✅",
                    "failed": "❌",
                    "skipped": "⏭️",
                    "unknown": "❓",
                }.get(action.get("status"), "❓")

                markdown_content += f"{status_icon} **{action.get('description')}**\n"
                markdown_content += f"   - Status: {action.get('status')}\n"
                markdown_content += f"   - Time: {action.get('timestamp')}\n\n"

        markdown_content += "\n---\n\n*Execution completed by AWS CloudOps Agent*\n"

        # Generate S3 key (same pattern as analysis results)
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H-%M-%S')
        s3_key = f"executions/{date_str}/{safe_service_name}/{time_str}-{alert_id}.md"

        # Upload to S3
        s3.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=markdown_content.encode("utf-8"),
            ContentType="text/markdown",
            Metadata={
                "alert-id": alert_id,
                "service-name": safe_service_name,
                "execution-status": "success" if execution_result['success'] else "failed",
                "timestamp": now.isoformat(),
            },
        )

        print(f"📤 Execution results uploaded to s3://{s3_bucket}/{s3_key}")

        return s3_key

    except Exception as e:
        print(f"❌ Error uploading execution results: {e}")
        return None


# COMMENTED OUT - Not using notifications in simplified version
# User gets immediate HTML response when clicking Execute button
# def send_execution_notifications(alert_data, execution_result, execution_s3_key):
#     """Send execution completion notifications to all channels"""
#     print("Sending execution notifications")
#
#     service_name = alert_data.get("service_name")
#     alert_id = alert_data.get("alert_id")
#
#     # Generate S3 URL
#     s3_bucket = os.environ.get("S3_ANALYSIS_BUCKET")
#     execution_url = None
#     if execution_s3_key and s3_bucket:
#         execution_url = f"https://{s3_bucket}.s3.amazonaws.com/{execution_s3_key}"
#
#     # Send notifications here if needed
#     pass


# def send_teams_execution_notification(
#     domain, alert_id, execution_result, execution_url
# ):
#     """Send execution notification to Teams"""
#     webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")

#     if not webhook_url:
#         print("TEAMS_WEBHOOK_URL not configured")
#         return False

#     from urllib.request import Request, urlopen

#     success = execution_result["success"]
#     icon = "✅" if success else "❌"
#     color = "Good" if success else "Attention"
#     title = f"{icon} Execution {'Completed' if success else 'Failed'}: {domain}"

#     card_body = [
#         {
#             "type": "TextBlock",
#             "size": "Large",
#             "weight": "Bolder",
#             "text": title,
#             "wrap": True,
#             "color": color,
#         },
#         {
#             "type": "FactSet",
#             "facts": [
#                 {"title": "Alert ID:", "value": alert_id},
#                 {"title": "Domain:", "value": domain},
#                 {"title": "Status:", "value": "SUCCESS" if success else "FAILED"},
#                 {
#                     "title": "Completed:",
#                     "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 },
#             ],
#         },
#     ]

#     # Add summary if available
#     if "details" in execution_result and "summary" in execution_result["details"]:
#         summary = execution_result["details"]["summary"]
#         card_body.extend(
#             [
#                 {"type": "TextBlock", "text": "---", "separator": True},
#                 {
#                     "type": "TextBlock",
#                     "text": f"**Execution Summary:**\n\n- Total Actions: {summary.get('total_actions', 0)}\n- Successful: {summary.get('successful', 0)} ✅\n- Failed: {summary.get('failed', 0)} ❌\n- Skipped: {summary.get('skipped', 0)} ⏭️",
#                     "wrap": True,
#                 },
#             ]
#         )

#     # Add view results button
#     if execution_url:
#         card_body.append(
#             {
#                 "type": "ActionSet",
#                 "actions": [
#                     {
#                         "type": "Action.OpenUrl",
#                         "title": "📄 View Execution Log",
#                         "url": execution_url,
#                     }
#                 ],
#             }
#         )

#     adaptive_card = {
#         "type": "message",
#         "attachments": [
#             {
#                 "contentType": "application/vnd.microsoft.card.adaptive",
#                 "content": {
#                     "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
#                     "type": "AdaptiveCard",
#                     "version": "1.4",
#                     "body": card_body,
#                 },
#             }
#         ],
#     }

#     try:
#         req = Request(
#             webhook_url,
#             data=json.dumps(adaptive_card).encode("utf-8"),
#             headers={"Content-Type": "application/json"},
#         )
#         response = urlopen(req)
#         print(f"Teams execution notification sent")
#         return True
#     except Exception as e:
#         print(f"Failed to send Teams notification: {e}")
#         return False


# def send_slack_execution_notification(
#     domain, alert_id, execution_result, execution_url
# ):
#     """Send execution notification to Slack"""
#     webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

#     if not webhook_url:
#         print("SLACK_WEBHOOK_URL not configured")
#         return False

#     from urllib.request import Request, urlopen

#     success = execution_result["success"]
#     icon = ":white_check_mark:" if success else ":x:"
#     color = "#00FF00" if success else "#FF0000"

#     blocks = [
#         {
#             "type": "header",
#             "text": {
#                 "type": "plain_text",
#                 "text": f"{icon} Execution {'Completed' if success else 'Failed'}: {domain}",
#                 "emoji": True,
#             },
#         },
#         {
#             "type": "section",
#             "fields": [
#                 {"type": "mrkdwn", "text": f"*Alert ID:*\n`{alert_id}`"},
#                 {"type": "mrkdwn", "text": f"*Domain:*\n{domain}"},
#                 {
#                     "type": "mrkdwn",
#                     "text": f"*Status:*\n{'SUCCESS' if success else 'FAILED'}",
#                 },
#                 {
#                     "type": "mrkdwn",
#                     "text": f"*Completed:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
#                 },
#             ],
#         },
#     ]

#     # Add summary
#     if "details" in execution_result and "summary" in execution_result["details"]:
#         summary = execution_result["details"]["summary"]
#         blocks.append(
#             {
#                 "type": "section",
#                 "text": {
#                     "type": "mrkdwn",
#                     "text": f"*Execution Summary:*\n• Total: {summary.get('total_actions', 0)}\n• Success: {summary.get('successful', 0)} ✅\n• Failed: {summary.get('failed', 0)} ❌\n• Skipped: {summary.get('skipped', 0)} ⏭️",
#                 },
#             }
#         )

#     # Add view button
#     if execution_url:
#         blocks.append(
#             {
#                 "type": "actions",
#                 "elements": [
#                     {
#                         "type": "button",
#                         "text": {"type": "plain_text", "text": "📄 View Execution Log"},
#                         "url": execution_url,
#                     }
#                 ],
#             }
#         )

#     message = {
#         "blocks": blocks,
#         "attachments": [
#             {
#                 "color": color,
#                 "fallback": f"Execution {alert_id} {'completed' if success else 'failed'}",
#             }
#         ],
#     }

#     try:
#         req = Request(
#             webhook_url,
#             data=json.dumps(message).encode("utf-8"),
#             headers={"Content-Type": "application/json"},
#         )
#         response = urlopen(req)
#         print(f"Slack execution notification sent")
#         return True
#     except Exception as e:
#         print(f"Failed to send Slack notification: {e}")
#         return False


# def send_email_execution_notification(
#     domain, alert_id, execution_result, execution_url, alert_data
# ):
#     """Send execution notification via SNS email"""
#     sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")

#     if not sns_topic_arn:
#         print("SNS_TOPIC_ARN not configured")
#         return False

#     try:
#         success = execution_result["success"]
#         status_icon = "✅" if success else "❌"

#         email_message = f"""{status_icon} Execution {'COMPLETED' if success else 'FAILED'}

# Domain: {domain}
# Alert ID: {alert_id}
# Status: {'SUCCESS' if success else 'FAILED'}
# Completed: {datetime.now().isoformat()}

# """

#         # Add summary
#         if "details" in execution_result and "summary" in execution_result["details"]:
#             summary = execution_result["details"]["summary"]
#             email_message += f"""Execution Summary:
# - Total Actions: {summary.get('total_actions', 0)}
# - Successful: {summary.get('successful', 0)}
# - Failed: {summary.get('failed', 0)}
# - Skipped: {summary.get('skipped', 0)}

# """

#         # Add execution log preview
#         execution_log = execution_result.get("execution_log", "")
#         if len(execution_log) > 1000:
#             email_message += f"Execution Log (preview):\n{execution_log[:1000]}...\n\n"
#         else:
#             email_message += f"Execution Log:\n{execution_log}\n\n"

#         if execution_url:
#             email_message += f"Full Execution Log: {execution_url}\n"

#         sns.publish(
#             TopicArn=sns_topic_arn,
#             Subject=f"Execution {'Completed' if success else 'Failed'}: {domain}",
#             Message=email_message,
#         )
#         print("Email execution notification sent")
#         return True
#     except Exception as e:
#         print(f"Failed to send email notification: {e}")
#         return False


def send_teams_execution_plan(alert_id, service_name, session_id, execution_result, s3_analysis_key, is_approved=False, execution_s3_key=None):
    """
    Send execution plan or results to MS Teams with Adaptive Card

    Args:
        is_approved: If False, send plan with Approve & Deny buttons. If True, send final results.
        execution_s3_key: S3 key of the execution plan/result file
    """
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")

    if not webhook_url:
        print("⚠️ TEAMS_WEBHOOK_URL not configured - skipping Teams notification")
        return False

    try:
        api_gateway_id = os.environ.get("API_GATEWAY_ID", "ueit30s254")
        region = os.environ.get("AWS_REGION", "ap-southeast-1")
        s3_bucket = os.environ.get("S3_ANALYSIS_BUCKET", "cloudops-analysis")

        # Generate S3 pre-signed URL for execution plan/results
        plan_s3_url = None
        if execution_s3_key:
            s3_client = boto3.client("s3", region_name="ap-southeast-1")
            try:
                plan_s3_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': s3_bucket, 'Key': execution_s3_key},
                    ExpiresIn=604800  # 7 days
                )
                print(f"✅ Generated S3 pre-signed URL for plan: {execution_s3_key}")
            except Exception as e:
                print(f"⚠️ Failed to generate S3 pre-signed URL: {e}")

        if is_approved:
            # EXECUTION RESULTS - Final notification
            success = execution_result.get("success", False)
            status_icon = "✅" if success else "❌"
            status_text = "SUCCESS" if success else "FAILED"
            color = "Good" if success else "Attention"

            card_body = [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": f"{status_icon} Execution {status_text}",
                    "wrap": True,
                    "color": color
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Alert ID:", "value": alert_id},
                        {"title": "Service:", "value": service_name},
                        {"title": "Status:", "value": status_text},
                        {"title": "Completed:", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": "Execution Log:",
                    "weight": "Bolder",
                    "separator": True
                },
                {
                    "type": "TextBlock",
                    "text": execution_result.get("execution_log", "No log available")[:500] + "...",
                    "wrap": True,
                    "isSubtle": True
                }
            ]

            # Add summary stats
            if "details" in execution_result and "summary" in execution_result["details"]:
                summary = execution_result["details"]["summary"]
                card_body.append({
                    "type": "TextBlock",
                    "text": f"**Summary:** {summary.get('successful', 0)} succeeded, {summary.get('failed', 0)} failed, {summary.get('skipped', 0)} skipped",
                    "wrap": True,
                    "separator": True
                })

        else:
            # EXECUTION PLAN - Awaiting approval
            execution_log = execution_result.get("execution_log", "")

            # Build approval URL
            approval_url = f"https://{api_gateway_id}.execute-api.{region}.amazonaws.com/prod/execute?alert_id={alert_id}&session_id={session_id}&service_name={urllib.parse.quote(service_name)}&s3_key={s3_analysis_key or ''}&approved=true"

            card_body = [
                {
                    "type": "TextBlock",
                    "size": "Large",
                    "weight": "Bolder",
                    "text": "📋 Execution Plan Ready",
                    "wrap": True,
                    "color": "Warning"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Alert ID:", "value": alert_id},
                        {"title": "Service:", "value": service_name},
                        {"title": "Status:", "value": "PENDING APPROVAL"},
                        {"title": "Created:", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": "⚠️ **Approval Required**",
                    "weight": "Bolder",
                    "color": "Warning",
                    "separator": True
                },
                {
                    "type": "TextBlock",
                    "text": "Review the execution plan below and approve to proceed with automatic remediation.",
                    "wrap": True,
                    "isSubtle": True
                },
                {
                    "type": "TextBlock",
                    "text": "Execution Plan:",
                    "weight": "Bolder",
                    "separator": True
                },
                {
                    "type": "TextBlock",
                    "text": execution_log[:1000] + ("..." if len(execution_log) > 1000 else ""),
                    "wrap": True,
                    "isSubtle": True
                }
            ]

        # Create Adaptive Card actions
        card_actions = []

        if not is_approved:
            # PLANNING MODE: Show Approve, Deny, and View Plan buttons
            if plan_s3_url:
                card_actions.append({
                    "type": "Action.OpenUrl",
                    "title": "📄 View Full Plan in S3",
                    "url": plan_s3_url
                })

            card_actions.append({
                "type": "Action.OpenUrl",
                "title": "✅ Approve & Execute",
                "url": approval_url
            })

            # Deny button - just a dummy URL that shows "Denied" message
            # (In production, this could call another Lambda endpoint to log denial)
            card_actions.append({
                "type": "Action.OpenUrl",
                "title": "❌ Deny",
                "url": f"https://{api_gateway_id}.execute-api.{region}.amazonaws.com/prod/execute?alert_id={alert_id}&session_id={session_id}&service_name={urllib.parse.quote(service_name)}&denied=true"
            })
        else:
            # EXECUTION MODE: Show View Report button
            if plan_s3_url:
                card_actions.append({
                    "type": "Action.OpenUrl",
                    "title": "📄 View Full Report in S3",
                    "url": plan_s3_url
                })

        # Create Adaptive Card (matching format from invoke_handler)
        adaptive_card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": card_body,
                        "actions": card_actions,
                        "msteams": {"width": "Full"}
                    }
                }
            ]
        }

        # Send to Teams
        req = Request(
            webhook_url,
            data=json.dumps(adaptive_card).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        response = urlopen(req, timeout=10)

        # Check response
        response_text = response.read().decode() if response.status == 200 else ""

        if response.status == 200:
            print(f"✅ Teams notification sent: {'Execution plan' if not is_approved else 'Execution results'}")
            print(f"Response: {response_text}")
            return True
        else:
            print(f"⚠️ Teams notification returned status {response.status}: {response_text}")
            return False

    except Exception as e:
        print(f"❌ Error sending Teams notification: {e}")
        import traceback
        traceback.print_exc()
        return False
