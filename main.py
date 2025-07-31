import os
import time
import signal
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime

# --- 配置项 ---
SERVER_URL = "https://panel.godlike.host/server/c5c32cb4"
LOGIN_URL = "https://panel.godlike.host/auth/login"
COOKIE_NAME = "remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d"
# 单次任务执行的超时时间（秒），依然保留以防单次运行卡死
TASK_TIMEOUT_SECONDS = 300  # 5分钟

# --- 超时处理机制 ---
class TaskTimeoutError(Exception):
    """自定义任务超时异常"""
    pass

def timeout_handler(signum, frame):
    """超时信号处理函数"""
    raise TaskTimeoutError("任务执行时间超过设定的阈值")

if os.name != 'nt':
    signal.signal(signal.SIGALRM, timeout_handler)

# login_with_playwright 函数保持不变，此处为完整代码
def login_with_playwright(page):
    """处理登录逻辑，优先使用Cookie，失败则使用邮箱密码。"""
    remember_web_cookie = os.environ.get('PTERODACTYL_COOKIE')
    pterodactyl_email = os.environ.get('PTERODACTYL_EMAIL')
    pterodactyl_password = os.environ.get('PTERODACTYL_PASSWORD')

    if remember_web_cookie:
        print("检测到 PTERODACTYL_COOKIE，尝试使用 Cookie 登录...")
        session_cookie = {
            'name': COOKIE_NAME, 'value': remember_web_cookie, 'domain': '.panel.godlike.host',
            'path': '/', 'expires': int(time.time()) + 3600 * 24 * 365, 'httpOnly': True,
            'secure': True, 'sameSite': 'Lax'
        }
        page.context.add_cookies([session_cookie])
        print(f"已设置 Cookie。正在访问目标服务器页面: {SERVER_URL}")
        page.goto(SERVER_URL, wait_until="domcontentloaded")
        
        if "auth/login" in page.url:
            print("Cookie 登录失败或会话已过期，将回退到邮箱密码登录。")
            page.context.clear_cookies()
        else:
            print("Cookie 登录成功！")
            return True

    if not (pterodactyl_email and pterodactyl_password):
        print("错误: Cookie 无效或未提供，且未提供 PTERODACTYL_EMAIL 和 PTERODACTYL_PASSWORD。无法登录。", flush=True)
        return False

    print("正在尝试使用邮箱和密码登录...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    try:
        print("正在点击 'Through login/password'...")
        
        page.wait_for_load_state('networkidle')  # 页面静止时再继续

        page.wait_for_selector("a:has-text("Through login/password")", timeout=30000)
        page.click('a:has-text("Through login/password")')



        
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
        
        if "auth/login" in page.url:
            print("邮箱密码登录失败，请检查凭据是否正确。", flush=True)
            page.screenshot(path="login_fail_error.png")
            return False
        
        print("邮箱密码登录成功！")
        return True
    except Exception as e:
        print(f"邮箱密码登录过程中发生错误: {e}", flush=True)
        page.screenshot(path="login_process_error.png")
        return False

def add_time_task(page):
    """执行一次增加服务器时长的任务。"""
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行增加时长任务...")
        
        if page.url != SERVER_URL:
            print(f"当前不在目标页面，正在导航至: {SERVER_URL}")
            page.goto(SERVER_URL, wait_until="domcontentloaded")

        add_button_selector = 'button:has-text("Add 90 minutes")'
        print("步骤1: 查找并点击 'Add 90 minutes' 按钮...")
        page.locator(add_button_selector).wait_for(state='visible', timeout=30000)
        page.locator(add_button_selector).click()
        print("...已点击 'Add 90 minutes'。")

        watch_ad_selector = 'button:has-text("Watch advertisment")'
        print("步骤2: 查找并点击 'Watch advertisment' 按钮...")
        page.locator(watch_ad_selector).wait_for(state='visible', timeout=30000)
        page.locator(watch_ad_selector).click()
        print("...已点击 'Watch advertisment'。")

        # 【【【 核心修改点在这里 】】】
        # 不再等待成功提示，而是直接固定等待2分钟。
        print("步骤3: 开始固定等待2分钟...")
        time.sleep(120)  # 等待 2 分钟 (120 秒)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 已等待2分钟，默认任务完成。")
        
        return True

    except PlaywrightTimeoutError as e:
        print(f"❌ 任务执行超时: 未在规定时间内找到元素。请检查选择器或页面是否已更改。", flush=True)
        page.screenshot(path="task_element_timeout_error.png")
        return False
    except Exception as e:
        print(f"❌ 任务执行过程中发生未知错误: {e}", flush=True)
        page.screenshot(path="task_general_error.png")
        return False

def main():
    """
    主函数，执行一次登录和一次任务，然后退出。
    """
    print("启动自动化任务（单次运行, 固定等待模式）...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60000)
        print("浏览器启动成功。", flush=True)

        try:
            # 步骤1: 登录
            if not login_with_playwright(page):
                print("登录失败，程序终止。", flush=True)
                exit(1)

            # 步骤2: 执行增加时长的核心任务 (带超时监控)
            if os.name != 'nt':
                signal.alarm(TASK_TIMEOUT_SECONDS)
            
            print("\n----------------------------------------------------")
            success = add_time_task(page)
            
            if os.name != 'nt':
                signal.alarm(0)

            if success:
                print("本轮任务成功完成。", flush=True)
            else:
                print("本轮任务失败。", flush=True)
                exit(1)

        except TaskTimeoutError as e:
            print(f"🔥🔥🔥 任务强制超时（{TASK_TIMEOUT_SECONDS}秒）！🔥🔥🔥", flush=True)
            print(f"错误信息: {e}", flush=True)
            page.screenshot(path="task_force_timeout_error.png")
            exit(1)
        except Exception as e:
            print(f"主程序发生严重错误: {e}", flush=True)
            page.screenshot(path="main_critical_error.png")
            exit(1)
        finally:
            print("关闭浏览器，程序结束。", flush=True)
            browser.close()

if __name__ == "__main__":
    main()
    print("脚本执行完毕。")
    exit(0)
