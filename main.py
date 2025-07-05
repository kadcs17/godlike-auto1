import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime

# --- 配置项 ---
# 目标服务器页面
SERVER_URL = "https://panel.godlike.host/server/61b8ad3c"
# 登录页面
LOGIN_URL = "https://panel.godlike.host/auth/login"
# Cookie 名称
COOKIE_NAME = "remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d"

def login_with_playwright(page):
    """
    处理登录逻辑，优先使用Cookie，失败则使用邮箱密码。
    返回 True 表示登录成功，False 表示失败。
    """
    # 从环境变量获取凭据
    remember_web_cookie = os.environ.get('PTERODACTYL_COOKIE')
    pterodactyl_email = os.environ.get('PTERODACTYL_EMAIL')
    pterodactyl_password = os.environ.get('PTERODACTYL_PASSWORD')

    # --- 方案一：优先尝试使用 Cookie 会话登录 ---
    if remember_web_cookie:
        print("检测到 PTERODACTYL_COOKIE，尝试使用 Cookie 登录...")
        session_cookie = {
            'name': COOKIE_NAME,
            'value': remember_web_cookie,
            'domain': '.panel.godlike.host',
            'path': '/',
            'expires': int(time.time()) + 3600 * 24 * 365,
            'httpOnly': True,
            'secure': True,
            'sameSite': 'Lax'
        }
        page.context.add_cookies([session_cookie])
        print(f"已设置 Cookie。正在访问目标服务器页面: {SERVER_URL}")
        page.goto(SERVER_URL, wait_until="domcontentloaded")
        
        # 检查是否因 Cookie 无效被重定向到登录页
        if "auth/login" in page.url:
            print("Cookie 登录失败或会话已过期，将回退到邮箱密码登录。")
            page.context.clear_cookies() # 清除无效Cookie
        else:
            print("Cookie 登录成功！")
            return True

    # --- 方案二：如果 Cookie 登录失败或未提供，则使用邮箱密码登录 ---
    if not (pterodactyl_email and pterodactyl_password):
        print("错误: Cookie 无效或未提供，且未提供 PTERODACTYL_EMAIL 和 PTERODACTYL_PASSWORD。无法登录。")
        return False

    print("正在尝试使用邮箱和密码登录...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")

    try:
        # 点击 "Through login/password" 按钮以显示登录表单
        print("正在点击 'Through login/password'...")
        page.locator('a:has-text("Through login/password")').click()
        
        # 定义选择器并填写表单
        email_selector = 'input[name="username"]'
        password_selector = 'input[name="password"]'
        login_button_selector = 'button[type="submit"]:has-text("Login")'
        
        print("等待登录表单元素加载...")
        page.wait_for_selector(email_selector)
        page.wait_for_selector(password_selector)

        print("正在填写邮箱和密码...")
        page.fill(email_selector, pterodactyl_email)
        page.fill(password_selector, pterodactyl_password)

        print("正在点击登录按钮...")
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.click(login_button_selector)
        
        # 检查登录后是否成功跳转
        if "auth/login" in page.url:
            print("邮箱密码登录失败，请检查凭据是否正确。")
            page.screenshot(path="login_fail_error.png")
            return False
        
        print("邮箱密码登录成功！")
        return True

    except Exception as e:
        print(f"邮箱密码登录过程中发生错误: {e}")
        page.screenshot(path="login_process_error.png")
        return False

def add_time_task(page):
    """
    执行一次增加90分钟时长的任务。
    """
    try:
        print("\n----------------------------------------------------")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行增加时长任务...")
        
        # 确保当前在正确的服务器页面
        if page.url != SERVER_URL:
            print(f"当前不在目标页面，正在导航至: {SERVER_URL}")
            page.goto(SERVER_URL, wait_until="domcontentloaded")

        # 1. 找到并点击 "Add 90 minutes" 按钮
        add_button_selector = 'button:has-text("Add 90 minutes")'
        print("正在查找并点击 'Add 90 minutes' 按钮...")
        page.locator(add_button_selector).wait_for(state='visible', timeout=30000)
        page.locator(add_button_selector).click()
        print("已点击 'Add 90 minutes'。")

        # 2. 在弹出的页面/模态框中，找到并点击 "Watch advertisment" 按钮
        watch_ad_selector = 'button:has-text("Watch advertisment")'
        print("正在查找并点击 'Watch advertisment' 按钮...")
        page.locator(watch_ad_selector).wait_for(state='visible', timeout=30000)
        page.locator(watch_ad_selector).click()
        print("已点击 'Watch advertisment'，等待广告完成...")

        # 3. 等待成功提示出现 (广告播放时间可能较长，设置足够长的超时)
        success_selector = 'p:has-text("Successfully added 90 minutes to server timer")'
        print("正在等待成功提示...")
        page.locator(success_selector).wait_for(state='visible', timeout=120000) # 120秒超时
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 成功增加90分钟！")
        print("----------------------------------------------------")
        
        return True

    except PlaywrightTimeoutError as e:
        print(f"❌ 任务执行超时: 未在规定时间内找到元素。错误: {e}")
        page.screenshot(path="task_timeout_error.png")
        return False
    except Exception as e:
        print(f"❌ 任务执行过程中发生未知错误: {e}")
        page.screenshot(path="task_general_error.png")
        return False


def main():
    """
    主函数，初始化浏览器并循环执行任务。
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # 设置一个全局的较长超时时间，以应对慢加载
        page.set_default_timeout(60000) # 60秒

        try:
            # 首先执行登录
            if not login_with_playwright(page):
                print("登录失败，程序终止。")
                browser.close()
                return

            # 进入主循环
            while True:
                if not add_time_task(page):
                    print("任务执行失败，可能需要检查页面结构或登录状态。正在尝试重新导航到主页...")
                    # 尝试重新导航，如果会话失效，下次循环的add_time_task会再次导航
                    page.goto(SERVER_URL, wait_until="domcontentloaded")

                print("任务循环结束，将等待6分钟后继续...")
                time.sleep(360) # 等待 6 分钟 (6 * 60 = 360秒)
        
        except Exception as e:
            print(f"主程序发生严重错误: {e}")
            page.screenshot(path="main_critical_error.png")
        finally:
            print("关闭浏览器，程序结束。")
            browser.close()


if __name__ == "__main__":
    print("启动自动化任务...")
    main()
    exit(0)
