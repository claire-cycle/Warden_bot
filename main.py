import json
import random
import string
import time
import uuid
from datetime import datetime
from functools import wraps

import pytz
import requests
from eth_account.messages import encode_defunct
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import cycle
from eth_account import Account

def retry_on_failure(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        cycle.log_message(f"最大重试次数已达到，最终错误: {e}", "error")
                        return None
                    cycle.log_message(f"第{attempt + 1}次重试，错误: {e}", "info")
                    time.sleep(delay * (attempt + 1))
            return None
        return wrapper
    return decorator

def get_current_time_iso():
    """获取当前UTC时间的ISO格式"""
    utc_time = datetime.now(pytz.UTC)
    return utc_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def create_siwe_message(wallet_address, nonce):
    """创建SIWE消息"""
    issued_at = get_current_time_iso()
    message = f"""app.wardenprotocol.org wants you to sign in with your Ethereum account:
{wallet_address}

By signing, you are proving you own this wallet and logging in. This does not initiate a transaction or cost any fees.

URI: https://app.wardenprotocol.org
Version: 1
Chain ID: 56
Nonce: {nonce}
Issued At: {issued_at}
Resources:
- https://privy.io"""

    return message, issued_at

def random_string(length=6):
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_letters, k=length))


def sign_message(private_key, message):
    """使用私钥对消息进行签名"""
    try:
        if not private_key.startswith("0x"):
            private_key = "0x" + private_key
        account = Account.from_key(private_key)
        # 将消息编码为 EthereumMessage 对象
        encoded_message = encode_defunct(text=message)
        signature = account.sign_message(encoded_message)
        return signature.signature.hex()
    except Exception as e:
        cycle.log_message(f"签名失败: {e}", "error")
        return None

def get_wallet_address(private_key):
    """根据私钥获取钱包地址"""
    try:
        if not private_key.startswith('0x'):
            private_key = '0x' + private_key
        account = Account.from_key(private_key)
        return account.address
    except Exception as e:
        cycle.log_message(f"获取钱包地址失败: {e}", "error")
        return None



class Warden:
    def __init__(self, proxies=None):
        self.user_id = None
        self.proxies = proxies
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置超时
        self.timeout = 30
        
        self.base_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Origin': 'https://app.wardenprotocol.org',
            'Referer': 'https://app.wardenprotocol.org/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'privy-app-id': 'cm7f00k5c02tibel0m4o9tdy1',
        }

    @retry_on_failure()
    def get_nonce(self, wallet_address):
        """获取nonce"""
        try:
            url = 'https://auth.privy.io/api/v1/siwe/init'
            headers = {
                **self.base_headers,
                "privy-ca-id": str(uuid.uuid4())
            }
            payload = {"address": wallet_address}
            response = self.session.post(url, json=payload, headers=headers, proxies=self.proxies, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if 'nonce' in data:
                cycle.log_message(f"获取nonce成功: {data['nonce']}", "info")
                return data['nonce']
            cycle.log_message("nonce字段不存在", "error")
            return None
        except requests.exceptions.RequestException as e:
            cycle.log_message(f"获取nonce失败: {e}", "error")
            raise


    @retry_on_failure()
    def login(self, wallet_address, message, signature):
        """登录"""
        try:
            url = "https://auth.privy.io/api/v1/siwe/authenticate"
            headers = {
                **self.base_headers,
                "privy-ca-id": str(uuid.uuid4())
            }
            payload = {
                "message": message,
                "signature": f"0x{signature}",
                "chainId": "eip155:56",
                "walletClientType": "okx_wallet",
                "connectorType": "injected",
                "mode": "login-or-sign-up"
            }

            response = self.session.post(url, json=payload, headers=headers, proxies=self.proxies, timeout=self.timeout)

            response.raise_for_status()
            data = response.json()
            cycle.log_message(f"{wallet_address}：登录成功", "info")
            return data
        except requests.exceptions.RequestException as e:
            cycle.log_message(f"{wallet_address}:登录错误，错误信息 {e}", "error")
            raise


    @retry_on_failure()
    def get_ref_code(self, wallet_address, token, ref_code):
        """获取邀请码"""
        try:
            url = f"https://api.app.wardenprotocol.org/api/users/me?referralCode={ref_code}"
            headers = {
                **self.base_headers,
                'Host': 'api.app.wardenprotocol.org',
                'Connection': 'keep-alive',
                'sec-ch-ua-platform': '"macOS"',
                'Authorization': f'Bearer {token}',
                'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?0'
            }
            response = self.session.get(url, headers=headers, proxies=self.proxies, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            cycle.log_message(f"{wallet_address}绑定验证码成功", "info")
            self.user_id = data['id']
            return data["referralCode"]
        except requests.exceptions.RequestException as e:
            cycle.log_message(f"{wallet_address}:绑定邀请码错误，错误信息 {e}", "error")
            raise


    @retry_on_failure()
    def set_token_name(self, wallet_address, token, name):
        """设置代币名称"""
        try:
            url = "https://api.app.wardenprotocol.org/api/tokens"
            headers = {
                **self.base_headers,
                'Host': 'api.app.wardenprotocol.org',
                'Connection': 'keep-alive',
                'sec-ch-ua-platform': '"macOS"',
                'Authorization': f'Bearer {token}',
                'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?0'
            }
            payload = {
                "userId": self.user_id,
                "tokenName": name,
            }
            response = self.session.post(url, json=payload, headers=headers, proxies=self.proxies, timeout=self.timeout)
            response.raise_for_status()
            cycle.log_message(f"{wallet_address}:设置代币名称{name}成功", "info")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                cycle.log_message(f"{wallet_address}:设置代币名称{name}失败，{name}代币已存在", "error")
                return False
            cycle.log_message(f"{wallet_address}:设置代币名称{name}失败，状态码: {e.response.status_code}", "error")
            raise
        except requests.exceptions.RequestException as e:
            cycle.log_message(f"{wallet_address}:设置代币名称{name}错误，错误信息 {e}", "error")
            raise


    @retry_on_failure()
    def activate_token(self, wallet_address, token, activityType):
        """激活账户"""
        try:
            url = "https://api.app.wardenprotocol.org/api/tokens/activity"
            action_data = {
                "LOGIN": "user_login",
                "CHAT_INTERACTION": "user_chat",
                "GAME_PLAY": "user_game"
            }
            payload = {
                "activityType": activityType,
                "metadata": {
                    "action": action_data.get(activityType),
                    "timestamp": get_current_time_iso(),
                    "source": "privy"
                }
            }
            headers = {
                **self.base_headers,
                'Host': 'api.app.wardenprotocol.org',
                'Connection': 'keep-alive',
                'sec-ch-ua-platform': '"macOS"',
                'Authorization': f'Bearer {token}',
                'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
                'sec-ch-ua-mobile': '?0'
            }
            response = self.session.post(url, json=payload, headers=headers, proxies=self.proxies, timeout=self.timeout)
            response.raise_for_status()
            cycle.log_message(f"{wallet_address}:账户完成{activityType}任务成功", "info")
        except requests.exceptions.RequestException as e:
            cycle.log_message(f"{wallet_address}:账户完成任务错误，错误信息{e}", "error")
            raise


def register(warden:Warden, i, wallet_address, token, referral_code_list):
    new_ref_code = warden.get_ref_code(wallet_address, token, referral_code_list[i % len(referral_code_list)])
    name = random_string(6)
    is_set = warden.set_token_name(wallet_address, token, name)
    if not is_set:
       return False
    with open("success.txt", "a", encoding="utf-8") as f:
        f.write(f"{wallet_address}:{new_ref_code}\n")
    daily_tasks(warden, wallet_address, token)
    return True



def daily_tasks(warden:Warden, wallet_address, token):
    """每日任务"""
    warden.activate_token(wallet_address, token, "LOGIN")
    warden.activate_token(wallet_address, token, "CHAT_INTERACTION")
    time.sleep(random.randint(5, 10))
    warden.activate_token(wallet_address, token, "GAME_PLAY")


def main():
    is_login = input("是否注册(y/n): ")
    # 读取配置文件
    with open('config_dev.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    referral_code_list = open("refcode.txt", "r", encoding="utf-8").read().splitlines()
    nstproxy_Channel = config['proxy_user']
    nstproxy_Password = config['proxy_password']
    wallets = open("wallets.txt", "r", encoding="utf-8").read().splitlines()
    for i, private_key in enumerate(wallets):
        wallet_address = get_wallet_address(private_key)
        proxy = cycle.get_proxy(nstproxy_Channel, nstproxy_Password)
        warden = Warden(proxy)
        nonce = warden.get_nonce(wallet_address)
        if nonce is None:
            continue
        message, issued_at = create_siwe_message(wallet_address, nonce)
        signature = sign_message(private_key, message)
        if signature is None:
            continue
        login_data = warden.login(wallet_address, message, signature)
        if login_data is None:
            continue
        token = login_data['token']
        if is_login == "y":
            register(warden, i, wallet_address, token, referral_code_list)
        else:
            daily_tasks(warden, wallet_address, token)


if __name__ == '__main__':
    main()


