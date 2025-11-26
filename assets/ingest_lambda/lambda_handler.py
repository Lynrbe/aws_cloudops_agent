import os
import json
import time
import hashlib
import logging
import boto3
from botocore.exceptions import ClientError

# Logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables (required)
KB_ID = os.environ.get("KNOWLEDGE_BASE_ID")
REGION = os.environ.get("REGION")  # default region if not set
# Optional: if you prefer to pin to a single data source id
DATA_SOURCE_ID_ENV = os.environ.get("DATA_SOURCE_ID", "").strip()

# Optional behavior flags
POLL_FOR_COMPLETION = os.environ.get("POLL_FOR_COMPLETION", "false").lower() in ("1","true","yes")
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "5"))
POLL_MAX_RETRIES = int(os.environ.get("POLL_MAX_RETRIES", "60"))

# boto3 client for bedrock agent
client = boto3.client("bedrock-agent", region_name=REGION)


def make_client_token(bucket: str, key: str) -> str:
    """Deterministic idempotency token from bucket+key."""
    raw = f"{bucket}/{key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]


def choose_data_source(kb_id: str):
    """Return data_source_id: prefer DATA_SOURCE_ID env, else list first from KB."""
    if DATA_SOURCE_ID_ENV:
        return DATA_SOURCE_ID_ENV
    # fallback: list data sources
    resp = client.list_data_sources(knowledgeBaseId=kb_id)
    summaries = resp.get("dataSourceSummaries", [])
    if not summaries:
        raise RuntimeError("No data source found for KB " + kb_id)
    return summaries[0]["dataSourceId"]


def start_ingestion(kb_id: str, ds_id: str, client_token: str, description: str = None):
    kwargs = {
        "knowledgeBaseId": kb_id,
        "dataSourceId": ds_id,
        "clientToken": client_token
    }
    if description:
        kwargs["description"] = description
    return client.start_ingestion_job(**kwargs)


def poll_ingestion(kb_id: str, ds_id: str, ingestion_job_id: str, interval=POLL_INTERVAL_SECONDS, retries=POLL_MAX_RETRIES):
    """Poll until ingestion job reaches terminal state, return final response."""
    for attempt in range(1, retries + 1):
        try:
            resp = client.get_ingestion_job(
                knowledgeBaseId=kb_id,
                dataSourceId=ds_id,
                ingestionJobId=ingestion_job_id
            )
        except ClientError as e:
            logger.warning("get_ingestion_job failed attempt %d: %s", attempt, e)
            time.sleep(interval)
            continue

        job = resp.get("ingestionJob", {})
        status = job.get("status")
        logger.info("Poll attempt %d/%d - ingestion status: %s", attempt, retries, status)
        if status in ("SUCCEEDED", "COMPLETED"):
            return resp
        if status in ("FAILED", "CANCELLED"):
            # terminal states - return immediately
            return resp

        time.sleep(interval)

    raise TimeoutError(f"Timed out waiting for ingestion job {ingestion_job_id} (tried {retries} times)")


def extract_s3_from_event(event: dict):
    """Support both raw S3 put events and manual triggers."""
    # S3 notifications: Records list
    records = event.get("Records", [])
    if not records:
        # If called manually with body containing bucket/key
        bucket = event.get("bucket") or event.get("Bucket")
        key = event.get("key") or event.get("Key")
        if bucket and key:
            return bucket, key
        raise ValueError("No S3 records or bucket/key in event")

    # Use first record as canonical
    s3 = records[0].get("s3", {})
    bucket = s3.get("bucket", {}).get("name")
    key = s3.get("object", {}).get("key")
    if not bucket or not key:
        raise ValueError("Invalid S3 event structure")
    # URL-decoding if need
    return bucket, key


def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event)[:2048])

    if not KB_ID:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "KNOWLEDGE_BASE_ID environment variable not set."})
        }

    try:
        bucket, key = extract_s3_from_event(event)
    except Exception as e:
        logger.exception("Failed to parse S3 event: %s", e)
        return {"statusCode": 400, "body": json.dumps({"error": "invalid s3 event", "detail": str(e)})}

    client_token = make_client_token(bucket, key)
    logger.info("Using clientToken: %s", client_token)

    try:
        data_source_id = choose_data_source(KB_ID)
        logger.info("Selected data source id: %s", data_source_id)
    except Exception as e:
        logger.exception("Failed to determine data source: %s", e)
        return {"statusCode": 500, "body": json.dumps({"error": "no data source", "detail": str(e)})}

    # Try to start ingestion
    try:
        resp = start_ingestion(KB_ID, data_source_id, client_token, description=f"Ingest {bucket}/{key}")
        ingestion_job_id = resp.get("ingestionJob", {}).get("ingestionJobId")
        logger.info("Started ingestion job %s for kb=%s ds=%s", ingestion_job_id, KB_ID, data_source_id)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        msg = e.response.get("Error", {}).get("Message")
        logger.exception("StartIngestionJob ClientError: %s %s", code, msg)
        return {"statusCode": 500, "body": json.dumps({"error": "start_ingestion_failed", "code": code, "message": msg})}
    except Exception as e:
        logger.exception("StartIngestionJob exception: %s", e)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    # Optionally poll until completion
    if POLL_FOR_COMPLETION and ingestion_job_id:
        try:
            final = poll_ingestion(KB_ID, data_source_id, ingestion_job_id)
            logger.info("Ingestion final state: %s", final)
            return {"statusCode": 200, "body": json.dumps({"ingestionJob": final})}
        except TimeoutError as te:
            logger.exception("Polling timed out: %s", te)
            return {"statusCode": 202, "body": json.dumps({"status": "started", "ingestionJobId": ingestion_job_id, "note": "poll timed out, job still running"})}
        except Exception as e:
            logger.exception("Polling error: %s", e)
            return {"statusCode": 500, "body": json.dumps({"error": "polling_failed", "detail": str(e)})}

    # Default: return started job info
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Ingestion job started for KB {KB_ID}",
            "knowledgeBaseId": KB_ID,
            "dataSourceId": data_source_id,
            "ingestionJobId": ingestion_job_id
        })
    }
