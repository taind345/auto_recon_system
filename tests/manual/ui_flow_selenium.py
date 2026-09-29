"""Selenium UI test: real Firefox headless vs AUTO_RECON + fixture. Prints STEP PASS/FAIL."""
import os
import sys
import time

sys.path.insert(0, "/mnt/DATA_D/DESKTOP/DATA_DESKTOP/0-CODE/0-app_pentest_vibe_code/AUTO_RECON")
os.chdir("/mnt/DATA_D/DESKTOP/DATA_DESKTOP/0-CODE/0-app_pentest_vibe_code/AUTO_RECON")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import app as appmod
from tests._helpers import start_server, stop_server
from tests.fixture_server import FixtureHandler, SESS

SHOTS = "/tmp/opencode/shots"
os.makedirs(SHOTS, exist_ok=True)
os.makedirs("/tmp/opencode/dl", exist_ok=True)

fails = []


def step(name, fn):
    try:
        fn()
        print(f"PASS {name}")
    except Exception as e:
        fails.append(name)
        print(f"FAIL {name}: {type(e).__name__}: {str(e)[:220]}")


fsrv, _, fport = start_server(FixtureHandler)
asrv, _, aport = start_server(appmod.Handler)
T = f"http://127.0.0.1:{fport}"
BASE = f"http://127.0.0.1:{aport}"

opts = Options()
opts.add_argument("-headless")
opts.set_preference("browser.download.dir", "/tmp/opencode/dl")
opts.set_preference("browser.download.useDownloadDir", True)
from selenium.webdriver.firefox.service import Service
drv = webdriver.Firefox(options=opts,
                        service=Service(executable_path="/tmp/opencode/geckodriver"))
drv.set_window_size(1600, 1000)
W = WebDriverWait(drv, 20)
WL = WebDriverWait(drv, 240)


def errors():
    try:
        logs = drv.get_log("browser")
        return [l for l in logs if l.get("level") in ("SEVERE",)]
    except Exception:
        return []


drv.get(BASE + "/")
drv.execute_script("window.__errs=[]; window.onerror=function(m){window.__errs.push(m);};")


def jserrs():
    return drv.execute_script("return window.__errs || []")


def check_rail():
    assert "AUTO_RECON" in drv.title
    items = drv.find_elements(By.CSS_SELECTOR, ".nav-it")
    assert len(items) == 9, f"nav={len(items)}"
    assert drv.find_element(By.ID, "btnScan").text != ""


step("rail-9-items", check_rail)


def check_lang_vi():
    opt = drv.find_element(By.CSS_SELECTOR, '#profile option[value="fast"]').text
    assert "Nhanh" in opt, opt


step("default-lang-vi", check_lang_vi)


def toggle_theme():
    drv.find_element(By.ID, "btnTheme").click()
    assert drv.find_element(By.TAG_NAME, "html").get_attribute("data-theme") == "light"
    drv.save_screenshot(f"{SHOTS}/01-light.png")
    drv.find_element(By.ID, "btnTheme").click()
    assert drv.find_element(By.TAG_NAME, "html").get_attribute("data-theme") == "dark"


step("theme-toggle", toggle_theme)


def toggle_lang():
    drv.find_element(By.ID, "btnLang").click()
    assert drv.find_element(By.TAG_NAME, "html").get_attribute("lang") == "en"
    opt = drv.find_element(By.CSS_SELECTOR, '#profile option[value="fast"]').text
    assert "Fast" in opt, opt
    drv.find_element(By.ID, "btnLang").click()
    assert drv.find_element(By.TAG_NAME, "html").get_attribute("lang") == "vi"


step("lang-toggle", toggle_lang)


def do_scan():
    drv.find_element(By.ID, "target").clear()
    drv.find_element(By.ID, "target").send_keys(T)
    sel = drv.find_element(By.ID, "authMode")
    sel.find_elements(By.TAG_NAME, "option")[1].click()  # cookie
    drv.find_element(By.ID, "authUser").send_keys("wiener")
    drv.find_element(By.ID, "authCookie").send_keys(SESS)
    drv.find_element(By.ID, "btnScan").click()
    WL.until(lambda d: d.find_element(By.ID, "btnScan").is_enabled())
    time.sleep(3)  # let result poll land
    eps = drv.find_elements(By.CSS_SELECTOR, "#tree .ep")
    assert len(eps) >= 5, f"tree eps={len(eps)}"
    drv.save_screenshot(f"{SHOTS}/02-tree.png")


step("scan-auth-tree", do_scan)


def open_detail():
    drv.find_elements(By.CSS_SELECTOR, "#tree .ep")[0].click()
    W.until(EC.presence_of_element_located((By.ID, "pane")))
    for t in ["info", "js", "hrefs", "forms", "diff", "raw", "burp"]:
        drv.find_element(By.CSS_SELECTOR, f'.tabs button[data-t="{t}"]').click()
        time.sleep(1.2 if t == "raw" else 0.3)
        txt = drv.find_element(By.ID, "pane").text
        assert len(txt.strip()) > 0, f"empty pane {t}"
        if t == "js":
            views = drv.find_elements(By.CSS_SELECTOR, '#pane [data-js]')
            if views:  # endpoint with JS: VIEW must load source
                views[0].click()
                W.until(lambda d: "AKIA" in d.find_element(By.ID, "jsout").text
                        or "fetch" in d.find_element(By.ID, "jsout").text)
            else:  # JS-less endpoint: explicit empty-state, never a stray hint
                assert "no JS files" in txt, f"missing empty-state: {txt[:120]}"
    drv.save_screenshot(f"{SHOTS}/03-detail.png")


step("detail-7-tabs", open_detail)


def js_view_loads():
    # home page carries /s.js: [VIEW] must fetch and render its source
    drv.find_element(By.CSS_SELECTOR, '#tree .ep[data-u]').click()  # ensure tree focused
    eps = drv.find_elements(By.CSS_SELECTOR, "#tree .ep")
    home = [e for e in eps if e.get_attribute("data-u").rstrip("/") == T.rstrip("/")]
    assert home, "home ep missing in tree"
    home[0].click()
    drv.find_element(By.CSS_SELECTOR, '.tabs button[data-t="js"]').click()
    time.sleep(0.5)
    views = drv.find_elements(By.CSS_SELECTOR, '#pane [data-js]')
    assert views, "home should list a JS file"
    views[0].click()
    W.until(lambda d: "AKIA" in d.find_element(By.ID, "jsout").text
            or "fetch" in d.find_element(By.ID, "jsout").text)


step("js-view-loads", js_view_loads)


def repeater_send():
    # (re-)open the burp tab, then SEND the prefilled raw request
    drv.find_element(By.CSS_SELECTOR, '.tabs button[data-t="burp"]').click()
    time.sleep(0.5)
    drv.find_element(By.ID, "sendReq").click()
    W.until(lambda d: "HTTP" in d.find_element(By.ID, "repRes").text)
    meta = drv.find_element(By.ID, "repMeta").text
    assert "HTTP 200" in meta, meta
    drv.save_screenshot(f"{SHOTS}/03b-repeater.png")


step("repeater-send", repeater_send)


def filters_search():
    n_all = len(drv.find_elements(By.CSS_SELECTOR, "#tree .ep"))
    drv.find_element(By.CSS_SELECTOR, '#filters button[data-f="auth"]').click()
    time.sleep(0.5)
    n_auth = len(drv.find_elements(By.CSS_SELECTOR, "#tree .ep"))
    assert 0 < n_auth <= n_all, f"{n_auth}/{n_all}"
    drv.find_element(By.CSS_SELECTOR, '#filters button[data-f="all"]').click()
    q = drv.find_element(By.ID, "q")
    q.send_keys("my-account")
    time.sleep(0.6)
    n_q = len(drv.find_elements(By.CSS_SELECTOR, "#tree .ep"))
    assert 0 < n_q < n_all, f"search {n_q}/{n_all}"
    q.send_keys(Keys.ESCAPE)
    time.sleep(0.6)
    assert len(drv.find_elements(By.CSS_SELECTOR, "#tree .ep")) == n_all


step("filters-search", filters_search)


def nav_all():
    for cat in ["overview", "subdomains", "ports", "params", "js", "tech", "auth", "notes", "endpoints"]:
        drv.find_element(By.CSS_SELECTOR, f'.nav-it[data-cat="{cat}"]').click()
        time.sleep(2.5)  # result poll 2s
        txt = drv.find_element(By.ID, "insp" if cat != "endpoints" else "tree").text
        assert len(txt.strip()) > 0, f"empty {cat}"
        if cat in ("overview", "auth"):
            drv.save_screenshot(f"{SHOTS}/04-{cat}.png")


step("nav-9-cats", nav_all)


def notes_diff():
    drv.find_element(By.CSS_SELECTOR, '.nav-it[data-cat="notes"]').click()
    time.sleep(2.5)
    W.until(EC.presence_of_element_located((By.ID, "bDiff")))
    drv.find_element(By.ID, "bMd").click()
    time.sleep(1)
    assert "AUTO_RECON" in drv.find_element(By.ID, "expOut").text
    drv.find_element(By.ID, "bDiff").click()
    time.sleep(1.5)
    assert "NEW" in drv.find_element(By.ID, "diffOut").text


step("notes-export-diff", notes_diff)


def check_session():
    drv.find_element(By.ID, "btnCheck").click()
    W.until(lambda d: "wiener" in d.find_element(By.ID, "sessMsg").text.lower()
            or "login" in d.find_element(By.ID, "sessMsg").text.lower())


step("check-session", check_session)


def auth_fields_per_mode():
    sel = drv.find_element(By.ID, "authMode")
    opts = sel.find_elements(By.TAG_NAME, "option")
    vis = lambda i: drv.find_element(By.ID, i).is_displayed()
    # cookie mode: user + cookie visible, pass/bearer/login-url hidden
    opts[1].click()
    assert vis("authUser") and vis("authCookie"), "cookie fields"
    assert not vis("authPass") and not vis("authBearer") and not vis("loginUrl"), "cookie hides others"
    # login mode: login-url + user + password visible
    opts[3].click()
    assert vis("loginUrl") and vis("authUser") and vis("authPass"), "login fields"
    assert drv.find_element(By.ID, "authPass").get_attribute("type") == "password", "pass masked"
    assert not vis("authCookie") and not vis("authBearer"), "login hides others"
    # bearer mode
    opts[2].click()
    assert vis("authBearer") and not vis("authPass"), "bearer fields"
    opts[1].click()  # back to cookie


step("auth-fields-per-mode", auth_fields_per_mode)

errs = errors() + jserrs()
print("CONSOLE_ERRS:", errs if errs else "none")
if errs:
    fails.append("console-errors")

drv.save_screenshot(f"{SHOTS}/05-final.png")
drv.quit()
stop_server(fsrv)
stop_server(asrv)
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
