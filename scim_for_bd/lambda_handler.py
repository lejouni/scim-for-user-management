import awsgi
from app import api

def lambda_handler(event, context):
    return awsgi.response(api, event, context)