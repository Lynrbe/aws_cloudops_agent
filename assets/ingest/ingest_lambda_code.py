import boto3
import json
import os
import logging
from utils.config import load_configs
import utils.mylogger as mylogger

logger = mylogger.get_logger()

agentcore_config, _ = load_configs()
kb_config = agentcore_config.get("knowledge_base", {})
memory_id = kb_config.get("kb_id")
