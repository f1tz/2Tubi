# -*- coding:utf-8 -*-
# coding by F1tz
import requests
import re
import json
import time
import hashlib
import hmac
import base64
import urllib.parse
import random

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.80 Safari/537.36'
}

url_login = 'https://www.t00ls.net/login.html'
url_checklogin = 'https://www.t00ls.net/checklogin.html'
url_signin = 'https://www.t00ls.net/ajax-sign.json'
url_tubilog= 'https://www.t00ls.net/members-tubilog.json'
url_domain= 'https://www.t00ls.net/domain.html'


# #####配置项开始#######

# questionid
# 1 母亲的名字
# 2 爷爷的名字
# 3 父亲出生的城市
# 4 您其中一位老师的名字
# 5 您个人计算机的型号
# 6 您最喜欢的餐馆名称
# 7 驾驶执照的最后四位数字

username = ''  # 用户名
password = ''  # 明文密码或密码MD5
password_hash = True  # 密码为md5时设置为True
questionid = ''  # 问题ID，参考上面注释，没有可不填
answer = ''  # 问题答案，没有可不填

# 配置各种key
# Server酱申请的skey
SCKEY = ''
# Webhook加签秘钥
secret_key = ''
# Webhook access_token
access_token = ''

# 配置通知方式 0=dingding 1=weixin 2=dd+wx一起通知
notice_type = 2

# 配置查询域名前缀后缀
domain_prefix = ''  # 前缀如：sabcsadfsafsf
domain_suffix = ''  # 后缀如：xyz.cn

# #####配置项结束#######


# 临时变量
tubi_tmp = 0
formhash = ''


# 第一步----获取formhash
def get_formhash(session):
    res = session.get(url=url_login, headers=headers)
    formhash_1 = re.findall('value=\"[0-9a-f]{8}\"', res.text)
    formhash = re.findall('[0-9a-f]{8}', formhash_1[0])[0]
    #    print(formhash)
    time.sleep(1)
    return formhash


def get_current_user(session):
    current_user = re.findall(
        '<a href="members-profile-[\d+].*\.html" target="_blank">{username}</a>'.format(username=username), session)
    # print(''.join(current_user))
    cuser = re.findall('[\d+]{4,5}', ''.join(current_user))[0]
    # print("用户ID:" + cuser)
    return cuser


# 登录T00ls
def login_t00ls(session):
    formhash = get_formhash(session)
    if password_hash:
        passwords = password
    else:
        passwords = hashlib.md5(password.encode('utf-8')).hexdigest()
    data = {
        'username': username,
        'password': passwords,
        'questionid': questionid,
        'answer': answer,
        'formhash': formhash,
        'loginsubmit': '登录',
        'redirect': 'https://www.t00ls.net',
        'cookietime': '2592000'
    }
    print(data)
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    headers[
        'Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
    headers['Referer'] = 'https://www.t00ls.net/login.html'
    res = session.post(url=url_login, headers=headers, data=data)
    # print(res.headers)
    time.sleep(1)
    # res2=session.get("https://www.t00ls.net/checklogin.html");
    # print(res2.text)
    return res, formhash


# 获取formhash, uid
def get_formhash_1(session):
    res = session.get(url=url_checklogin, headers=headers)
    # print("检查登录："+res.text)
    uid = get_current_user(res.text)
    # formhash = re.findall('[0-9a-f]{8}', res.text)[0]
    formhash = re.findall(re.compile('formhash=(.*?)">'), res.text)[0]  # 20200318修复来源不正确问题
    return formhash, uid


# 签到
def signin_t00ls(session):
    global formhash
    formhash, uid = get_formhash_1(session)
    print("\n[+]用户ID：%s\n[+]formhash：%s \n" % (uid,formhash))
    data = {
        'formhash': formhash,
        'signsubmit': 'apply'
    }
    headers['Referer'] = 'https://www.t00ls.net/members-profile-{uid}.html'.format(uid=uid)
    res = session.post(url=url_signin, data=data, headers=headers)
    return res


# 域名查询
def domain_query(session):
    retry = 0
    while (retry<10): # 域名查询重试10次
        domain = domain_prefix + str(random.randint(100000, 999999)) + domain_suffix
        data = f'domain={domain}&formhash={formhash}&querydomainsubmit=%E6%9F%A5%E8%AF%A2'
        try:
            resp = session.post(url_domain, headers=headers, data=data)
            if domain in resp.text:
                print('[+]域名查询成功：%s\n' % domain)
                if int(get_tubi(session)) > int(tubi_tmp)+1:
                    return domain
        except Exception as e:
            print(e)
        time.sleep(5) #
        retry+=1
    print('[!]无法获得域名查询金币')
    return '无法获得域名查询金币！'


# 获取当前Tubi数量
def get_tubi(session):
    resp = session.get(url_tubilog, headers=headers)
    tubilog = json.loads(resp.text)
    cmoney = tubilog['loglist'][0]['cmoney']
    return cmoney


# dingding加签函数
def add_sign():
    timestamp = str(round(time.time() * 1000))
    secret = secret_key # 加签秘钥
    secret_enc = secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    ts_sign = {'timestamp': timestamp, 'sign': sign}
    return ts_sign


# 消息发送
def send_msg(data):
    if notice_type == 0:
        # dingding
        try:
            sendMsg_by_dd(data)
        except Exception:
            print('请检查钉钉配置是否正确')
    elif notice_type == 1:
        # weixin
        try:
            sendMsg_by_wx(data)
        except Exception:
            print('请检查Server酱配置是否正确')
    else:
        try:
            sendMsg_by_dd(data)
        except Exception:
            print('请检查钉钉配置是否正确')
        try:
            sendMsg_by_wx(data)
        except Exception:
            print('请检查Server酱配置是否正确')


def sendMsg_by_dd(data):
    datamsg = {"msgtype": "text",
               "text": {
                   "content": "T00ls签到成功！\n%s" % data
               }
               }
    send_url = 'https://oapi.dingtalk.com/robot/send'
    ts_sign = add_sign()
    params = {
        'access_token': access_token,
        'timestamp': ts_sign['timestamp'],
        'sign': ts_sign['sign']
              }
    headers = {
        'Content-Type' : 'application/json'
    }

    req = requests.post(send_url, params=params, headers=headers, data=json.dumps(datamsg))
    print(req.text)


def sendMsg_by_wx(data):
    datamsg = {"text": "T00ls签到成功！", "desp": data}
    requests.post("https://sc.ftqq.com/" + SCKEY + ".send", data=datamsg)


def main():
    global tubi_tmp
    session = requests.session()  # 定义全局session
    get_formhash(session)  # 第一步----获取formhash
    login_t00ls(session)  # 登录T00ls
    tubi_tmp = get_tubi(session) # 原Tubi数量
    res_signin = signin_t00ls(session)  # 签到
    domain = domain_query(session) # 域名查询
    tubi_now = get_tubi(session) # 现Tubi数量
    print(time.strftime("%Y-%m-%d %H:%M:%S\n", time.localtime()), res_signin.text)
    data = '本次查询域名为：%s  \n原Tubi数量为：%s  \n现Tubi数量为：%s' % (domain, tubi_tmp, tubi_now)
    if "success" in res_signin.text:
        send_msg(data)


def main_handler(event, context):
    return main()


if __name__ == '__main__':
    main()