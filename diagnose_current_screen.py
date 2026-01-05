from appium import webdriver
from appium.options.android import UiAutomator2Options

options = UiAutomator2Options()
options.platform_name = 'Android'
options.automation_name = 'UiAutomator2'
options.device_name = 'emulator-5554'
options.app_package = 'com.reddit.frontpage'
options.app_activity = 'launcher.default'
options.no_reset = False
options.auto_grant_permissions = True

driver = webdriver.Remote('http://127.0.0.1:4723', options=options)

print("Capturing diagnostic info...")
driver.save_screenshot("diagnostic_screen.png")
with open("diagnostic_dump.xml", "w") as f:
    f.write(driver.page_source)
print("Done.")
driver.quit()
