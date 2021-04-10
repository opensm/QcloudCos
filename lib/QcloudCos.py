# -*- coding=utf-8
# appid 已在配置中移除,请在参数 Bucket 中带上 appid。Bucket 由 BucketName-APPID 组成
# 1. 设置用户配置, 包括 secretId，secretKey 以及 Region
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys
from settings import *
import os
import commands
from Log import RecodeLog
import glob
import time
import hashlib
import simplejson as json


def out_md5(src):
    # 简单封装
    m = hashlib.md5()
    m.update(src)
    return m.hexdigest()


class CosUpload:
    def __init__(self):
        self.tag_file = os.path.join(LOG_DIR, 'cos.tag')
        try:
            cnf = CosConfig(**COS_INIT_PARAMS)
            self.client = CosS3Client(cnf)
        except Exception as error:
            RecodeLog.error(msg="初始化COS失败，{0}".format(error))
            sys.exit(1)

    def read_json(self, json_file):
        """
        :param json_file:
        :return:
        """
        try:
            if not os.path.exists(json_file):
                raise Exception("文件不存在,{0}".format(json_file))
            with open(json_file, 'r') as fff:
                data = json.loads(fff.read())
                return data
        except Exception as error:
            RecodeLog.error(msg="读取{1}文件失败：{0}".format(error, json_file))
            return False

    def read_js(self, js_file):
        """
        :param js_file:
        :return:
        """
        try:
            if not os.path.exists(js_file):
                raise Exception("文件不存在,{0}".format(js_file))
            with open(js_file, 'r') as fff:
                data = fff.readlines()
                return data
        except Exception as error:
            RecodeLog.error(msg="读取{1}文件失败：{0}".format(error, js_file))
            return False

    def check_package(self, abs_path, achieve):
        """
        :param abs_path:
        :param achieve:
        :return:
        """
        achieve_list = []
        for x in ['baicorv.json', 'baicorv.js']:
            abs_achieve = os.path.join(abs_path, x)
            if not os.path.exists(abs_achieve):
                RecodeLog.warn(msg="{1}文件异常，文件个数：0,请检查压缩包:{0}！".format(achieve, abs_achieve))
                self.alert(message="{1}文件异常，文件个数：0,请检查压缩包:{0}！".format(achieve, abs_achieve))
                return False
            achieve_list.append(abs_achieve)
        json_version_data = self.read_json(json_file=os.path.join(abs_path, 'baicorv.json'))
        if not json_version_data:
            RecodeLog.error(msg="{0}:数据读取异常！".format(os.path.join(abs_path, 'baicorv.json')))
            self.alert(message="{0}:数据读取异常！".format(os.path.join(abs_path, 'baicorv.json')))
            return False

        package = json_version_data['package']
        version = json_version_data['version']
        abs_package = os.path.join(abs_path, package)
        if not os.path.exists(abs_package):
            RecodeLog.error(msg="文件不存在：{0}".format(abs_package))
            self.alert(message="文件不存在：{0}".format(abs_package))
            return False
        if package.split("_")[2] != version:
            RecodeLog.error(msg="获取的文件版本：{0}和baicorv.json版本不一致：{1}".format(package, version))
            self.alert(message="获取的文件版本：{0}和baicorv.json版本不一致：{1}".format(package, version))
            return False
        # 检查js
        js_version_data = self.read_js(js_file=os.path.join(abs_path, 'baicorv.js'))
        js_version_status = False
        js_package_status = False
        for y in js_version_data:
            if "'version':'{0}'".format(version) in y.replace(' ', '').strip('\n'):
                js_version_status = True
            if "'package':'{0}'".format(package) in y.replace(' ', '').strip('\n'):
                js_package_status = True
        achieve_list.append(abs_package)
        if js_version_status and js_package_status:
            RecodeLog.info(msg="{0},{1},{2},三者信息对应，检查无问题！".format(
                *[os.path.basename(x) for x in achieve_list]
            ))
            return achieve_list
        else:
            RecodeLog.error(msg="{0},{1},{2},三者信息不对应对应，检查不通过，请打包人员检查！".format(
                *[os.path.basename(x) for x in achieve_list]
            ))
            self.alert(message="{0},{1},{2},三者信息不对应对应，检查不通过，请打包人员检查！".format(
                *[os.path.basename(x) for x in achieve_list]
            ))
            return False

    def check_url(self, url_list, abs_path):
        """
        :param url_list:
        :param abs_path:
        :return:
        """
        import requests
        for url in url_list:
            try:
                check_url = "{0}/{1}".format(
                    ONLINE_URL,
                    url.replace(UPLOAD_DIR, '').replace(os.path.basename(abs_path), '')
                )
                getr = requests.get(url="https://{0}".format(check_url.replace("\/\/", "")), stream=True)
                if getr.status_code != 200:
                    raise Exception("文件检查异常：{0}，{1}".format(check_url, getr.content))
                remote_data = out_md5(src=getr.raw.read())
                with open(url, 'r') as fff:
                    local_data = out_md5(src=fff.read())
                if remote_data != local_data:
                    raise Exception("文件未更新,获取到远程MD5:{0},本地MD5:{1}".format(remote_data, local_data))
                continue
            except Exception as error:
                RecodeLog.error(msg=error)
                return False
        return True

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
        check_result = self.check_package(abs_path=abs_path, achieve=achieve)
        if not check_result:
            exec_str1 = "mv {0} {1}".format(achieve, error_dir)
            exec_str2 = "mv {0} {1}".format(abs_path, error_dir)
            if not self.cmd(exec_str1) or not self.cmd(exec_str2):
                self.alert(message="移动文件失败，文件名:{0}!".format(os.path.basename(achieve)))
            return False
        version_data = self.read_json(json_file=os.path.join(abs_path, 'baicorv.json'))
        # 开始上传
        for x in check_result:
            try:
                with open(x, 'rb') as fp:
                    response = self.client.put_object(
                        Bucket=BUCKET,
                        Body=fp,
                        Key=os.path.join(env_dir, os.path.basename(x)),
                        StorageClass='STANDARD',
                        EnableMD5=False
                    )
                    RecodeLog.info(msg=response)
            except Exception as error:
                RecodeLog.error(msg="文件:{0}，上传失败，原因：{1}".format(os.path.basename(x), error))
                status = False
        # 根据结果移动文件
        if status:
            # 检查生效状态
            i = 0
            while i <= CHECK_ONLINE_COUNT:
                if not self.check_url(url_list=check_result, abs_path=abs_path):
                    time.sleep(20)
                else:
                    self.alert(message="{0}:文件已上传完成，并已生效！".format(os.path.basename(achieve)))
                    break
                i += 1
            self.alert(message="{0}:文件已上传完成，{1}秒检测，未生效，请检查！".format(
                os.path.basename(achieve), CHECK_ONLINE_COUNT * 20
            ))

            exec_str1 = "mv {0} {1}".format(achieve, finish_dir)
            exec_str2 = "mv {0} {1}/".format(abs_path, finish_dir)
            if not self.cmd(exec_str1) or not self.cmd(exec_str2):
                self.alert(message="上传资源成功,移动文件失败,文件名:{0},\n版本信息：{1}!".format(
                    os.path.basename(achieve),
                    str(version_data).replace(',', ',\n'))
                )
                return False
            self.alert(message="上传资源成功,文件名:{0},\n版本信息：{1}!".format(
                os.path.basename(achieve),
                '\n'.join(version_data))
            )
        else:
            exec_str1 = "mv {0} {1}".format(achieve, error_dir)
            exec_str2 = "mv {0} {1}".format(abs_path, error_dir)
            if not self.cmd(exec_str1) or not self.cmd(exec_str2):
                self.alert(message="上传资源失败,移动文件失败,文件名:{0}!".format(
                    os.path.basename(achieve)
                ))
                return False
            self.alert(message="上传资源失败，文件名:{0}!".format(os.path.basename(achieve)))
            return

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

        exec_str1 = "unzip -t {0}".format(package)
        if not self.cmd(cmd_str=exec_str1):
            RecodeLog.error("解压文件失败：{0}，任务退出!".format(package))
            return False

        exec_str = "unzip -o {0} -d {1}".format(package, filename)
        if not self.cmd(cmd_str=exec_str):
            RecodeLog.error("解压文件失败：{0}，任务退出!".format(package))
            sys.exit(1)
        return True

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

    def touch_tag(self):
        try:
            with open(self.tag_file, 'w') as fff:
                fff.write(str(time.time()))
        except Exception as error:
            RecodeLog.error(msg="创建tag文件:{0},失败，原因:{1}!".format(self.tag_file, error))
            self.alert(message="创建tag文件:{0},失败，原因:{1}!".format(self.tag_file, error))
            sys.exit(1)

    def check_tag(self):
        if os.path.exists(self.tag_file):
            try:
                with open(self.tag_file, 'r') as fff:
                    data = float(fff.readline().strip('\n'))
                    if time.time() - data > 1800:
                        raise Exception("标志文件产生时间超过30分钟，请运维检查是否有问题！")
                return True
            except Exception as error:
                self.alert(message=error.message)
                return True
        else:
            return False

    def check_task_file(self, achieve_name):
        """
        :param achieve_name:
        :return:
        """
        current_dir = os.path.dirname(achieve_name)
        achieve_path, filetype = os.path.splitext(os.path.basename(achieve_name))
        finish_dir = os.path.join(current_dir, FINISH_DIR)
        error_dir = os.path.join(current_dir, ERROR_DIR)
        rm_cmd_str = "rm -f {0}".format(achieve_name)
        if os.path.exists(
                os.path.join(
                    finish_dir,
                    os.path.basename(achieve_name)
                )
        ) or os.path.exists(
            os.path.join(
                error_dir,
                os.path.basename(achieve_name)
            )
        ) or os.path.exists(
            os.path.join(
                finish_dir,
                achieve_path
            )
        ) or os.path.exists(
            os.path.join(
                error_dir,
                achieve_path
            )
        ):
            RecodeLog.warn(msg="文件已经上传完成过：{0}".format(os.path.basename(achieve_name)))
            self.alert(message="文件已经上传完成过：{0}".format(os.path.basename(achieve_name)))
            self.cmd(cmd_str=rm_cmd_str)
            return False
        if not os.path.exists(achieve_name):
            RecodeLog.error(msg="文件不存在:{0}".format(achieve_name))
            self.alert(message="文件不存在:{0}".format(achieve_name))
            return False
        achieve_base_name = os.path.basename(achieve_name)
        achieve_name_data = os.path.splitext(achieve_base_name)[0].split("_")
        if len(achieve_name_data) != 3:
            RecodeLog.error(msg="{0}：上传文件必须以:打包时间_版本号_上传时间.zip格式，请检查！".format(achieve_name_data))
            self.alert(message="{0}：上传文件必须以:打包时间_版本号_上传时间.zip格式，请检查！".format(achieve_name_data))
        try:
            timestamp = time.mktime(time.strptime(achieve_name_data[2], "%Y%m%d%H%M%S"))
        except Exception as error:
            RecodeLog.error(msg="{0}：上传文件必须以:打包时间_版本号_上传时间.zip格式，请检查！".format(achieve_name_data, error))
            self.alert(message="{0}：上传文件必须以:打包时间_版本号_上传时间.zip格式，请检查！".format(achieve_name_data))
            return False
        if time.time() < timestamp:
            RecodeLog.warn(msg="任务时间未到：{0}".format(achieve_name))
            return False
        else:
            RecodeLog.info(msg="任务时间已到：{0}".format(achieve_name))
            return True

    def run(self):
        """
        :return:
        """
        if self.check_tag():
            RecodeLog.warn(msg="已经有进程在上传文件，退出！")
            sys.exit(0)
        self.touch_tag()
        for x in ENV_LIST:
            env_upload = os.path.join(UPLOAD_DIR, x)
            if not os.path.exists(
                    env_upload
            ):
                continue
            for y in [ERROR_DIR, FINISH_DIR]:
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
            # 文件名格式 20210410103200_v1.2.1_20210410110100.zip 打包时间_版本号_上传时间.zip
            if not self.check_task_file(achieve_name=achieve_list[0]):
                continue
            if not self.unzip_package(package=achieve_list[0]):
                continue
            self.upload(achieve=achieve_list[0], env_dir=x)
        os.remove(self.tag_file)

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
            "toparty": PARTY,  # 向这些部门发送
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
            RecodeLog.info(msg="发送消息失败,{}".format(error))
            return False
