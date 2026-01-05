import csv
import time
import random
import string
import imaplib
import email
import re
import os
from datetime import datetime
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions.mouse_button import MouseButton

# --- Configuration ---
EMAILS_CSV = '/Users/macbookpro13/androidvm/emails.csv'
IMAP_SERVER = 'imap.gmx.com'
IMAP_PORT = 993
CREATED_ACCOUNTS_CSV = '/Users/macbookpro13/androidvm/created_accounts.csv'
USED_EMAILS_CSV = '/Users/macbookpro13/androidvm/used_email_adresses.csv'
LOG_DIR = '/Users/macbookpro13/androidvm/logs'
SCREENSHOT_DIR = '/Users/macbookpro13/androidvm/screenshots'

# Create directories
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

APPIUM_SERVER_URL = 'http://127.0.0.1:4723'
CAPABILITIES = {
    'platformName': 'Android',
    'automationName': 'UiAutomator2',
    'deviceName': 'emulator-5554',
    'appPackage': 'com.reddit.frontpage',
    'appActivity': 'launcher.default',
    'appWaitActivity': '*',
    'noReset': True,
    'autoGrantPermissions': True
}

# --- Logging System ---
class Logger:
    def __init__(self, account_email):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_email = account_email.replace('@', '_at_').replace('.', '_')
        self.log_file = os.path.join(LOG_DIR, f"{safe_email}_{timestamp}.log")
        self.screenshot_prefix = os.path.join(SCREENSHOT_DIR, f"{safe_email}_{timestamp}")
        self.step_counter = 0
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')
    
    def screenshot(self, driver, description):
        self.step_counter += 1
        filename = f"{self.screenshot_prefix}_step{self.step_counter:03d}_{description}.png"
        try:
            driver.save_screenshot(filename)
            self.log(f"Screenshot saved: {filename}")
            return filename
        except Exception as e:
            self.log(f"Failed to save screenshot: {e}", "ERROR")
            return None
    
    def save_page_source(self, driver, description):
        self.step_counter += 1
        filename = f"{self.screenshot_prefix}_step{self.step_counter:03d}_{description}.xml"
        try:
            with open(filename, 'w') as f:
                f.write(driver.page_source)
            self.log(f"Page source saved: {filename}")
            return filename
        except Exception as e:
            self.log(f"Failed to save page source: {e}", "ERROR")
            return None

# --- Helper Functions ---
def random_sleep(min_s=1, max_s=3):
    """Sleep for a random amount of time to look human."""
    time.sleep(random.uniform(min_s, max_s))

def random_click(driver, element, logger):
    """Click a random point within the element's bounds for human-like interaction."""
    try:
        location = element.location
        size = element.size
        x = location['x'] + random.randint(int(size['width'] * 0.2), int(size['width'] * 0.8))
        y = location['y'] + random.randint(int(size['height'] * 0.2), int(size['height'] * 0.8))
        
        actions = ActionBuilder(driver)
        finger = actions.add_pointer_input(PointerInput.TOUCH, "finger")
        finger.create_pointer_move(duration=0, x=x, y=y)
        finger.create_pointer_down(MouseButton.LEFT)
        finger.create_pointer_move(duration=random.randint(50, 150), x=x, y=y)
        finger.create_pointer_up(MouseButton.LEFT)
        actions.perform()
        logger.log(f"Clicked element at ({x}, {y})")
        return True
    except Exception as e:
        logger.log(f"Random click failed, trying standard click: {e}", "WARN")
        try:
            element.click()
            return True
        except:
            return False

def generate_username():
    """Generates a random username."""
    adjectives = ['Epic', 'Cool', 'Fast', 'Smart', 'Bright', 'Neon', 'Hyper', 'Mega', 'Ultra', 'Super']
    nouns = ['Panda', 'Tiger', 'Eagle', 'Falcon', 'Wolf', 'Bear', 'Fox', 'Hawk', 'Lion', 'Shark']
    adj = random.choice(adjectives)
    noun = random.choice(nouns)
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f"{adj}{noun}{random_suffix}"

def get_verification_code(email_address, email_password, logger, retries=20, delay=10):
    """Retrieves verification code from email."""
    logger.log(f"Checking email for verification code...")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email_address, email_password)
        
        for i in range(retries):
            mail.select('inbox')
            status, messages = mail.search(None, '(UNSEEN)')
            
            if not messages[0]:
                logger.log(f"No new emails. Waiting... ({i+1}/{retries})")
            else:
                for num in messages[0].split()[::-1]:
                    status, msg_data = mail.fetch(num, '(RFC822)')
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    subject = msg["Subject"]
                    sender = msg["From"]
                    
                    logger.log(f"Email found - Subject: {subject} | From: {sender}")
                    mail.store(num, '+FLAGS', '\\Seen')

                    match = re.search(r'(\d{6}) is your Reddit verification code', str(subject))
                    if match:
                        code = match.group(1)
                        logger.log(f"Verification code found: {code}")
                        return code
            
            time.sleep(delay)
        
        logger.log("Failed to retrieve verification code after all retries", "ERROR")
        return None
    except Exception as e:
        logger.log(f"IMAP Error: {e}", "ERROR")
        return None

def save_account_info(email, password, username):
    """Appends created account details to CSV."""
    file_exists = os.path.isfile(CREATED_ACCOUNTS_CSV)
    with open(CREATED_ACCOUNTS_CSV, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['email', 'password', 'username', 'date_created'])
        writer.writerow([email, password, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

def log_used_email(email):
    """Logs email to used emails CSV."""
    file_exists = os.path.isfile(USED_EMAILS_CSV)
    with open(USED_EMAILS_CSV, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['email'])
        writer.writerow([email])

def find_and_click_button(driver, wait, logger, button_texts, description, timeout=10):
    """Generic function to find and click buttons by text."""
    logger.log(f"Looking for {description}: {button_texts}")
    logger.screenshot(driver, f"before_{description.replace(' ', '_')}")
    
    for text in button_texts:
        try:
            elements = driver.find_elements(AppiumBy.XPATH, f"//*[@text='{text}']")
            for elem in elements:
                if elem.is_displayed() and elem.is_enabled():
                    logger.log(f"Found '{text}' button")
                    random_click(driver, elem, logger)
                    random_sleep(2, 4)
                    logger.screenshot(driver, f"after_{description.replace(' ', '_')}")
                    return True
        except Exception as e:
            logger.log(f"Error finding '{text}': {e}", "WARN")
    
    logger.log(f"Could not find any of: {button_texts}", "ERROR")
    logger.save_page_source(driver, f"missing_{description.replace(' ', '_')}")
    return False

def run_bot():
    print("=" * 80)
    print("Starting Self-Diagnosing Reddit Bot v2")
    print("=" * 80)
    
    # Read credentials
    credentials = []
    try:
        with open(EMAILS_CSV, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                credentials.append(row)
    except FileNotFoundError:
        print(f"Error: {EMAILS_CSV} not found.")
        return
    
    # Read used emails
    used_emails = set()
    if os.path.exists(USED_EMAILS_CSV):
        with open(USED_EMAILS_CSV, mode='r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                used_emails.add(row['email'].strip().lower())

    print(f"Found {len(credentials)} total accounts. {len(used_emails)} already processed.")
    
    # Initialize driver ONCE
    driver = None
    wait = None
    
    try:
        print("Initializing Appium session...")
        import subprocess
        subprocess.run(["adb", "shell", "pm", "clear", "com.reddit.frontpage"])
        
        options = UiAutomator2Options().load_capabilities(CAPABILITIES)
        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        wait = WebDriverWait(driver, 20)
        print("✓ Appium session initialized successfully!")
        random_sleep(3, 5)
        
    except Exception as e:
        print(f"✗ Failed to initialize Appium session: {e}")
        return

    # Process each account
    for cred in credentials:
        email_addr = cred['email'].strip()
        password = cred['password'].strip()
        
        if not email_addr: continue
        if email_addr.lower() in used_emails:
            print(f"⊘ Skipping already processed: {email_addr}")
            continue
        
        # Create logger for this account
        logger = Logger(email_addr)
        username = generate_username()
        
        logger.log("=" * 60)
        logger.log(f"PROCESSING ACCOUNT: {email_addr}")
        logger.log(f"Generated username: {username}")
        logger.log("=" * 60)
        
        try:
            # Initial screenshot
            logger.screenshot(driver, "initial_screen")
            logger.save_page_source(driver, "initial_screen")
            
            # Step 1: Click Sign Up
            if not find_and_click_button(driver, wait, logger, ['Sign up'], 'signup_button'):
                logger.log("Failed to find Sign Up button, skipping account", "ERROR")
                continue
            
            # Step 2: Continue with Email
            find_and_click_button(driver, wait, logger, ['Continue with email', 'Email'], 'email_option')
            
            # Step 3: Enter Email
            logger.log("Entering email address...")
            logger.screenshot(driver, "before_email_entry")
            try:
                email_field = wait.until(EC.presence_of_element_located((AppiumBy.CLASS_NAME, "android.widget.EditText")))
                random_click(driver, email_field, logger)
                email_field.send_keys(email_addr)
                logger.log(f"Email entered: {email_addr}")
                random_sleep(1, 2)
                logger.screenshot(driver, "after_email_entry")
            except Exception as e:
                logger.log(f"Failed to enter email: {e}", "ERROR")
                continue
            
            # Step 4: Click Continue
            if not find_and_click_button(driver, wait, logger, ['Continue', 'Next'], 'continue_after_email'):
                logger.log("Failed to continue after email", "ERROR")
                continue
            
            # Step 5: Get Verification Code
            logger.log("Waiting for verification code...")
            random_sleep(10, 12)
            code = get_verification_code(email_addr, password, logger)
            
            if not code:
                logger.log("Failed to get verification code, skipping account", "ERROR")
                continue
            
            # Step 6: Enter Verification Code
            logger.log("Entering verification code...")
            logger.screenshot(driver, "before_code_entry")
            try:
                code_field = wait.until(EC.presence_of_element_located((AppiumBy.CLASS_NAME, "android.widget.EditText")))
                random_click(driver, code_field, logger)
                code_field.send_keys(code)
                logger.log(f"Code entered: {code}")
                random_sleep(2, 3)
                logger.screenshot(driver, "after_code_entry")
            except Exception as e:
                logger.log(f"Failed to enter code: {e}", "ERROR")
                continue
            
            # Step 7: Continue after code
            find_and_click_button(driver, wait, logger, ['Continue', 'Next'], 'continue_after_code')
            random_sleep(3, 5)
            
            # Step 8: Enter Username
            logger.log("Entering username...")
            logger.screenshot(driver, "before_username_entry")
            try:
                username_field = wait.until(EC.presence_of_element_located((AppiumBy.CLASS_NAME, "android.widget.EditText")))
                random_click(driver, username_field, logger)
                username_field.clear()
                username_field.send_keys(username)
                logger.log(f"Username entered: {username}")
                random_sleep(1, 2)
                logger.screenshot(driver, "after_username_entry")
            except Exception as e:
                logger.log(f"Failed to enter username: {e}", "ERROR")
            
            # Step 9: Continue after username
            find_and_click_button(driver, wait, logger, ['Continue', 'Next'], 'continue_after_username')
            random_sleep(3, 5)
            
            # Step 10: Skip through onboarding
            logger.log("Navigating through onboarding screens...")
            for i in range(10):
                logger.screenshot(driver, f"onboarding_screen_{i}")
                
                # Try to find and click skip/continue buttons
                if find_and_click_button(driver, wait, logger, 
                    ['Skip', 'Continue', 'Next', 'Maybe Later', 'Not now'], 
                    f'onboarding_step_{i}', timeout=3):
                    random_sleep(2, 4)
                else:
                    logger.log(f"No more onboarding buttons found at step {i}")
                    break
            
            # Final verification
            logger.log("Checking if we reached the home screen...")
            logger.screenshot(driver, "final_screen")
            logger.save_page_source(driver, "final_screen")
            
            # Check for home avatar
            if driver.find_elements(AppiumBy.ID, "com.reddit.frontpage:id/toolbar_home_avatar"):
                logger.log("✓ SUCCESS: Reached home screen!", "SUCCESS")
                save_account_info(email_addr, password, username)
                log_used_email(email_addr)
            else:
                logger.log("⚠ Account created but home screen not confirmed", "WARN")
                save_account_info(email_addr, password, username)
                log_used_email(email_addr)
            
        except Exception as e:
            logger.log(f"Critical error: {e}", "ERROR")
            logger.screenshot(driver, "error_state")
            logger.save_page_source(driver, "error_state")
    
    # Cleanup
    if driver:
        print("All accounts processed. Closing session.")
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    run_bot()
