
import random
import string
import time
from datetime import datetime

from colorama import Fore, Style
import requests





def get_proxy(nstproxy_Channel, nstproxy_Password):
    while True:
        session = ''.join(random.choices(string.digits + string.ascii_letters, k=8))
        nstproxy = f"http://{nstproxy_Channel}-zone-bwc-session-{session}-sessTime-1:{nstproxy_Password}@4904d5e899cf60a7.abcproxy.vip:4950"
        proxy = {
            "http": nstproxy,
            "https": nstproxy
        }
        log_message(f"获取代理成功： {nstproxy} ", "success")
        return proxy


def check_proxy(proxy):
    try:
        response = requests.get('http://httpbin.org/ip', proxies={"http": proxy, "https": proxy}, timeout=5)
        if response.status_code == 200:
            return True
        else:
            log_message(f"代理 {proxy} 无效", "error")
            return False
    except requests.exceptions.RequestException as e:
        log_message(str(e), "error")
        return False


def log_message(message="", message_type="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    colors = {
        "success": Fore.LIGHTGREEN_EX,
        "error": Fore.LIGHTRED_EX,
        "warning": Fore.LIGHTYELLOW_EX,
        "process": Fore.LIGHTCYAN_EX
    }

    log_color = colors.get(message_type, Fore.LIGHTWHITE_EX)
    print(f"{Fore.WHITE}[{Style.DIM}{timestamp}{Style.RESET_ALL}{Fore.WHITE}]{log_color}{message}")



def try_requests(url, method, headers=None, data=None, timeout=30, retry=3, proxies=None):
    for i in range(retry):
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, data=data, timeout=timeout, proxies=proxies)
            elif method == 'POST':
                response = requests.post(url, headers=headers, data=data, timeout=timeout, proxies=proxies)
                print(response.text)
            else:
                log_message(f"不支持的请求方法：{method}", 'error')
                return None
            return response.json()
        except Exception as e:
            log_message(f"第{i + 1}次请求失败，原因：{e}", 'error')
        log_message(f"超过最大重试次数，放弃请求", 'process')
        return None
    return None


def generate_random_string(length=6):
    letters = string.ascii_letters
    result_str = ''.join(random.choice(letters) for _ in range(length))
    return result_str


def random_password(length=10):
    letters = string.ascii_letters + string.digits + "@%$"
    result_str = ''.join(random.choice(letters) for _ in range(length))
    return result_str


def get_captcha(api_key, websiteURL, website_key):
    json_data = {
        "clientKey": api_key,
        "task":
            {
                "type": "TurnstileTaskProxyless",
                "websiteURL": websiteURL,
                "websiteKey": website_key
            },
        "softID": "51545"
    }
    response = requests.post(url='https://api.yescaptcha.com/createTask', json=json_data).json()
    log_message(f"reCaptchaV2创建任务成功，任务ID：{response['taskId']}", "success")
    if response['errorId'] != 0:
        log_message(f"reCaptchaV2创建任务失败，请检查reCaptchaV2是否还有余额", "error")
        raise ValueError(response)
    task_id = response['taskId']
    time.sleep(5)
    for _ in range(30):
        log_message("正在循环获取reCaptchaV2验证", "process")
        data = {"clientKey": api_key, "taskId": task_id}
        response = requests.post(url='https://api.yescaptcha.com/getTaskResult', json=data).json()
        if response['status'] == 'ready':
            return response['solution']['token']
        else:
            time.sleep(2)
            return None
    return None


def update_email_list(email_to_remove):
    # 读取文件中的邮箱列表
    with open("email.txt", "r", encoding="utf-8") as file:
        emails = file.readlines()

    # 移除已使用的邮箱，并处理空白字符
    emails = [email for email in emails if email.split(":")[0].strip() != email_to_remove]

    # 将更新后的邮箱列表写回文件
    with open("email.txt", 'w', encoding="utf-8") as file:
        file.writelines(emails)


def save_account_data(email, password):
    try:
        with open("registration.txt", "a") as f:
            f.write(f"{email}---{password}\n")
    except IOError as e:
        log_message(f"保存账户数据时出错: {str(e)}", "error")

