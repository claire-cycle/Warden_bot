# Warden Bot

## 项目简介

Warden Bot 是一个自动化工具，用于 Warden Protocol 平台的账户注册、登录和日常任务执行。该工具使用以太坊钱包进行身份验证，并通过代理服务器执行各种操作，包括账户注册、设置代币名称和完成日常任务。

## 功能特点

- 自动化账户注册流程
- 自动设置随机代币名称
- 自动完成日常任务（登录、聊天互动、游戏）
- 支持代理服务器配置
- 支持批量处理多个钱包账户
- 错误重试机制

## 安装要求

- Python 3.8+
- 以下Python库：
  - json
  - random
  - string
  - time
  - uuid
  - datetime
  - pytz
  - requests
  - eth_account
  - colorama
  - cryptography

## 安装步骤

1. 克隆仓库到本地：

```bash
git clone https://github.com/claire-cycle/Warden_bot.git
cd Warden_bot
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

## 配置说明

1. 创建或编辑 `config_dev.json` 文件，设置代理服务器信息：

```json
{
  "proxy_user": "your_proxy_username",
  "proxy_password": "your_proxy_password"
}
```

2. 在 `wallets.txt` 文件中添加以太坊钱包私钥（每行一个）

3. 在 `refcode.txt` 文件中添加邀请码（每行一个）

## 使用方法

运行主程序：

```bash
python main.py
```

程序会提示是否进行注册：
- 输入 `y` 进行注册流程
- 输入 `n` 仅执行日常任务

## 注意事项

- 请确保您的代理服务器配置正确
- 请勿泄露您的私钥信息
- 建议使用测试钱包进行操作，避免使用包含大量资产的主钱包

## 许可证

本项目采用 MIT 许可证，详情请参阅 [LICENSE](LICENSE) 文件。