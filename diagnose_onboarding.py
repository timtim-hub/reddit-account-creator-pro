from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
import time

CAPABILITIES = {
    'platformName': 'Android',
    'automationName': 'UiAutomator2',
    'deviceName': 'emulator-5554',
    'appPackage': 'com.reddit.frontpage',
    'appActivity': 'launcher.default',
    'noReset': True
}

def diagnose():
    options = UiAutomator2Options().load_capabilities(CAPABILITIES)
    driver = webdriver.Remote('http://127.0.0.1:4723', options=options)
    print("Capturing page source...")
    with open("onboarding_source.xml", "w") as f:
        f.write(driver.page_source)
    print("Capturing screenshot...")
    driver.save_screenshot("onboarding_debug.png")
    
    print("Elements with text:")
    elements = driver.find_elements(AppiumBy.XPATH, "//*[@text != '']")
    for el in elements:
        try:
            print(f"- {el.text} (ID: {el.get_attribute('resource-id')}, Clickable: {el.get_attribute('clickable')})")
        except: pass
    
    driver.quit()

if __name__ == "__main__":
    diagnose()
