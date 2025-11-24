import os
import time
import requests

## \file main.py
## \brief 微信公众号推送消息脚本
## \author 作业提交者
## \date 2025-11-23

APPID = os.getenv("WECHAT_APPID", "wxbde07a7ea1251f19")
APPSECRET = os.getenv("WECHAT_APPSECRET", "d82252ef9303acd4205c5d62faf2c37c")
TO_OPENID = os.getenv("WECHAT_TO_OPENID", "byOhGAnRGMY9nY20IPQNSA")

## \brief 获取微信 access_token
## \param appid 微信 AppID
## \param secret 微信 AppSecret
## \return access_token, expires_in

def get_access_token(appid, secret):
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type":"client_credential", "appid":appid, "secret":secret}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if "access_token" in data:
        return data["access_token"], data.get("expires_in", 7200)
    else:
        raise RuntimeError(f"无法获取 access_token: {data}")

## \brief 发送自定义文本消息到指定 openid
## \param access_token 微信 access_token
## \param openid 用户 openid
## \param text 文本内容
## \return 微信接口响应

def send_custom_text(access_token, openid, text):
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}"
    payload = {
        "touser": openid,
        "msgtype": "text",
        "text": {"content": text}
    }
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

## \brief 主程序入口，推送测试消息
if __name__ == "__main__":
    if APPID.startswith("YOUR") or APPSECRET.startswith("YOUR") or TO_OPENID.startswith("TARGET"):
        print("请先把 WECHAT_APPID、WECHAT_APPSECRET、WECHAT_TO_OPENID 放到环境变量，或直接修改脚本中的值后再运行。")
        exit(1)
    token, expires = get_access_token(APPID, APPSECRET)
    print("access_token 获取成功，expires_in=", expires)
    text = "这是来自作业三的测试推送消息 —— 本地脚本发送（无长期服务器）。"
    resp = send_custom_text(token, TO_OPENID, text)
    print("发送结果：", resp)

