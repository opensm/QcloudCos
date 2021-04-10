# -*- coding=utf-8
# Cos配置
COS_INIT_PARAMS = {
    "Region": "",
    "SecretId": "",
    "SecretKey": "",
    "Scheme": ""
}
BUCKET = ''
ONLINE_URL = ""
CHECK_ONLINE_COUNT = 5
# 企业微信
SECRET = ""
CORPID = ""
AGENTID = ""
PARTY = ""

UPLOAD_DIR = "/data/ftp/apk"
FINISH_DIR = "finish"
ERROR_DIR = "error"

LOG_DIR = "/tmp"
LOG_FILE = "qloud_cos.log"
LOG_LEVEL = "INFO"

ENV_LIST = ['dev-android', 'pre-android', 'prod-android']

__all__ = [
    'COS_INIT_PARAMS',
    'BUCKET',
    'ONLINE_URL',
    'SECRET',
    'CORPID',
    'AGENTID',
    'PARTY',
    'UPLOAD_DIR',
    'FINISH_DIR',
    'ERROR_DIR',
    'LOG_DIR',
    'LOG_FILE',
    'LOG_LEVEL',
    'ENV_LIST',
    'CHECK_ONLINE_COUNT'
]
