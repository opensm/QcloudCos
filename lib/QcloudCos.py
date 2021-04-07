# -*- coding=utf-8
# appid 已在配置中移除,请在参数 Bucket 中带上 appid。Bucket 由 BucketName-APPID 组成
# 1. 设置用户配置, 包括 secretId，secretKey 以及 Region
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys
from settings import COS_INIT_PARAMS, BUCKET, AGENTID, CORPID, SECRET, FINISH_DIR, UPLOAD_DIR, ERROR_DIR, ENV_LIST
import os
import commands
from Log import RecodeLog
import glob


class CosUpload:
    def __init__(self):
        try:
            cnf = CosConfig(**COS_INIT_PARAMS)
            self.client = CosS3Client(cnf)
        except Exception as error:
            RecodeLog.error(msg="初始化COS失败，{0}".format(error))
            sys.exit(1)

    def upload(self, achieve, env_dir):
        """
        :param achieve:
        :param env_dir:
        :return:
        """
        current_dir = os.path.dirname(achieve)
        error_dir = os.path.join(current_dir, ERROR_DIR)
        finish_dir = os.path.join(current_dir, FINISH_DIR)
        status = True
        if not os.path.isfile(achieve):
            RecodeLog.warn(msg="文件夹:{0},不支持当前上传！".format(achieve))
            return False
        abs_path, filetype = os.path.splitext(achieve)
        for root, dirs, achieves in os.walk(abs_path):
            for x in achieves:
                abs_achieve = os.path.join(root, x)
                if not os.path.exists(abs_achieve):
                    return False
                try:
                    with open(abs_achieve, 'rb') as fp:
                        response = self.client.put_object(
                            Bucket=BUCKET,
                            Body=fp,
                            Key=os.path.join(env_dir, x),
                            StorageClass='STANDARD',
                            EnableMD5=False
                        )
                        print(response)
                except Exception as error:
                    RecodeLog.error(msg="文件:{0}，上传失败，原因：{1}".format(abs_achieve, error))
                    status = False
        if status:
            exec_str1 = "mv {0} {1}".format(achieve, finish_dir)
            exec_str2 = "mv {0} {1}/".format(abs_path, finish_dir)
            self.cmd(exec_str1)
            self.cmd(exec_str2)
            self.alert(message="上传资源成功,文件名:{0}!".format(achieve))
        else:
            self.alert(message="上传资源失败，文件名:{0}!".format(achieve))
            exec_str1 = "mv {0} {1}".format(achieve, error_dir)
            exec_str2 = "mv {0} {1}".format(abs_path, error_dir)
            self.cmd(exec_str1)
            self.cmd(exec_str2)

    def unzip_package(self, package):
        """
        :param package:
        :return:
        """
        if not os.path.exists(package):
            RecodeLog.error("解压文件不存在，{0}!".format(package))
            sys.exit(1)
        filename, filetype = os.path.splitext(package)
        if filetype != ".zip":
            RecodeLog.error("打包的文件不是zip格式:{0}".format(package))
            self.alert(message="打包的文件不是zip格式:{0}".format(package))
            sys.exit(1)
        exec_str = "unzip -o {}".format(package)
        if not self.cmd(cmd_str=exec_str):
            RecodeLog.error("解压文件失败：{0}，任务退出!".format(package))
            sys.exit(1)

    def cmd(self, cmd_str):
        """
        :param cmd_str:
        :return:
        """
        try:
            status, output = commands.getstatusoutput(cmd_str)
            if status != 0:
                raise Exception(output)
            RecodeLog.info("执行:{0},成功!".format(cmd_str))
            return True
        except Exception as error:
            RecodeLog.error(msg="执行:{0},失败，原因:{1}".format(cmd_str, error))
            return False

    def run(self):
        """
        :return:
        """
        for x in ENV_LIST:
            env_upload = os.path.join(UPLOAD_DIR, x)
            if not os.path.exists(
                    env_upload
            ):
                continue
            for y in ['error', 'finish']:
                dirs = os.path.join(UPLOAD_DIR, x, y)
                if os.path.exists(dirs):
                    continue
                os.makedirs(dirs)
                os.chown(dirs, 1000, 1000)
            os.chdir(env_upload)
            achieve_list = glob.glob(os.path.join(env_upload, "*.zip"))
            if len(achieve_list) > 1:
                RecodeLog.warn(msg="版本：{0},存在：{1}个解压包，退出该版本执行，目前只支持一个ZIP的处理方式。".format(x, len(achieve_list)))
                self.alert(message="版本：{0},存在：{1}个解压包，退出该版本执行，目前只支持一个ZIP的处理方式。".format(x, len(achieve_list)))
                continue
            elif len(achieve_list) == 0:
                RecodeLog.warn("版本：{0}，不存在上传内容，跳过!".format(x))
                continue
            self.unzip_package(package=achieve_list[0])
            self.upload(achieve=achieve_list[0], env_dir=x)

    def alert(self, message):
        """
        :param message:
        :return:
        """
        import requests
        import json
        url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={}&corpsecret={}'
        try:
            getr = requests.get(url=url.format(CORPID, SECRET))
            access_token = getr.json().get('access_token')
        except Exception as error:
            RecodeLog.error(msg="获取token失败，{}".format(error))
            sys.exit(1)
        data = {
            "touser": 'YaoShaoQiang',  # 向这些部门发送
            "msgtype": "text",
            "agentid": AGENTID,  # 应用的 id 号
            "text": {
                "content": message
            }
        }
        try:
            r = requests.post(
                url="https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}".format(access_token),
                data=json.dumps(data)
            )
            if r.json()['errcode'] != 0:
                raise Exception(r.json()['errmsg'])
            RecodeLog.info(msg="发送消息成功:{}".format(r.json()['errmsg']))
            return True
        except Exception as error:
            print("发送消息失败,{}".format(error))
            RecodeLog.info(msg="发送消息失败,{}".format(error))
            return False
