"""Programmatic UI audit: overflow, overlap, raw i18n keys, broken chars, responsive."""
import os
import sys

sys.path.insert(0, "/mnt/DATA_D/DESKTOP/DATA_DESKTOP/0-CODE/0-app_pentest_vibe_code/AUTO_RECON")
os.chdir("/mnt/DATA_D/DESKTOP/DATA_DESKTOP/0-CODE/0-app_pentest_vibe_code/AUTO_RECON")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import app as appmod
from tests._helpers import start_server, stop_server
from tests.fixture_server import FixtureHandler, SESS

fails = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f" [{extra}]" if extra and not cond else ""))
    if not cond:
        fails.append(name)


fsrv, _, fport = start_server(FixtureHandler)
asrv, _, aport = start_server(appmod.Handler)
T = f"http://127.0.0.1:{fport}"

opts = Options()
opts.add_argument("-headless")
drv = webdriver.Firefox(options=opts, service=Service(executable_path="/tmp/opencode/geckodriver"))
drv.set_window_size(1600, 1000)
W = WebDriverWait(drv, 20)
WL = WebDriverWait(drv, 240)
drv.get(f"http://127.0.0.1:{aport}/")

# scan with auth for data
drv.find_element(By.ID, "target").send_keys(T)
drv.find_element(By.ID, "authMode").find_elements(By.TAG_NAME, "option")[1].click()
drv.find_element(By.ID, "authUser").send_keys("wiener")
drv.find_element(By.ID, "authCookie").send_keys(SESS)
drv.find_element(By.ID, "btnScan").click()
WL.until(lambda d: d.find_element(By.ID, "btnScan").is_enabled())
import time
time.sleep(3)

# 1. no page-level horizontal overflow (desktop)
ov = drv.execute_script("return document.documentElement.scrollWidth - document.documentElement.clientWidth")
check("no-h-overflow-desktop", ov <= 1, f"overflow={ov}px")

# 2. rail/wrap geometry: wrap starts at/after rail end
geo = drv.execute_script("""const r=document.querySelector('#rail').getBoundingClientRect();
const w=document.querySelector('#wrap').getBoundingClientRect();
return {railRight: r.right, wrapLeft: w.left, railW: r.width};""")
check("rail-wrap-no-overlap", geo["wrapLeft"] >= geo["railRight"] - 1, str(geo))

# 3. no raw i18n keys visible + no U+FFFD
body_txt = drv.find_element(By.TAG_NAME, "body").text
import re
rawkeys = [k for k in re.findall(r"[a-z]+_[a-z_]+", body_txt)
           if k in ("nav_overview", "filter_all", "target_ph", "detail_hint", "profile_fast")]
check("no-raw-i18n-keys", not rawkeys, str(rawkeys[:5]))
check("no-replacement-chars", "�" not in body_txt)

# 4. CSS vars resolve
cs = drv.execute_script("""const c=getComputedStyle(document.body);
return {bg: c.backgroundColor, fg: c.color};""")
check("css-vars-resolve", cs["bg"] not in ("", "rgba(0, 0, 0, 0)") and "rgba(0, 0, 0, 0)" not in cs["fg"], str(cs))

# 5. per-cat panel overflow + non-empty
for cat in ["overview", "subdomains", "ports", "endpoints", "params", "js", "tech", "auth", "notes"]:
    drv.find_element(By.CSS_SELECTOR, f'.nav-it[data-cat="{cat}"]').click()
    time.sleep(2.5)
    ov = drv.execute_script(
        "return document.documentElement.scrollWidth - document.documentElement.clientWidth")
    txt = drv.find_element(By.ID, "insp" if cat != "endpoints" else "tree").text
    check(f"cat-{cat}-fits", ov <= 1, f"overflow={ov}px")
    check(f"cat-{cat}-nonempty", len(txt.strip()) > 0)

# 6. responsive 700px: no h-overflow, rail collapsed
drv.set_window_size(700, 900)
time.sleep(1)
ov = drv.execute_script("return document.documentElement.scrollWidth - document.documentElement.clientWidth")
rw = drv.execute_script("return document.querySelector('#rail').getBoundingClientRect().width")
check("responsive-no-overflow", ov <= 1, f"overflow={ov}px")
check("responsive-rail-collapsed", rw < 120, f"rail={rw}px")
drv.save_screenshot("/tmp/opencode/shots/06-mobile.png")

# 7. light theme still fits
drv.set_window_size(1600, 1000)
drv.find_element(By.ID, "btnTheme").click()
time.sleep(0.5)
ov = drv.execute_script("return document.documentElement.scrollWidth - document.documentElement.clientWidth")
check("light-no-overflow", ov <= 1, f"overflow={ov}px")

drv.quit()
stop_server(fsrv)
stop_server(asrv)
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
