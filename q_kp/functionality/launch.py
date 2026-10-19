from __future__ import annotations

from playwright.async_api import Error as PlaywrightError, Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from q_haderslev_vbo.playwright.browser_session import BrowserSession
from q_haderslev_vbo.playwright.faelles_kommunal_login_idp import login_via_faelles_kommunal_idp
from q_kp.configuration import (
    KP_ACTION_TIMEOUT_MS, KP_CREDENTIAL_NAME, KP_DOMAIN, KP_LOGIN_TIMEOUT_MS,
    KP_MUNICIPALITY, KP_NAVIGATION_TIMEOUT_MS, KP_OPGAVEINDBAKKE_PATH,
    KP_PATH, KP_POLL_INTERVAL_MS, KP_START_URL,
)

AUTH_DROPDOWN = "select#SelectedAuthenticationUrl"
OK_BUTTON = (
    "input[type='button'][value='OK'], input[type='submit'][value='OK'], "
    "input[type='button'][value='Vælg'], input[type='submit'][value='Vælg'], "
    "button:has-text('OK'), button:has-text('Vælg')"
)


class KpLaunchError(RuntimeError):
    """Fejl under launch eller login i KP."""


async def wait_for_page_ready(page: Page, timeout_ms: int = KP_NAVIGATION_TIMEOUT_MS) -> None:
    if page.is_closed():
        raise KpLaunchError("Browserens side er lukket.")
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        try:
            ready = await page.evaluate("() => Boolean(document && document.documentElement)")
        except PlaywrightError as error:
            raise KpLaunchError("KP-siden blev ikke klar.") from error
        if not ready:
            raise KpLaunchError("KP-siden blev ikke klar.")


def is_kp_url(page: Page) -> bool:
    return not page.is_closed() and KP_DOMAIN.casefold() in page.url.casefold() and KP_PATH.casefold() in page.url.casefold()


def is_kp_opgaveindbakke_url(page: Page) -> bool:
    return is_kp_url(page) and KP_OPGAVEINDBAKKE_PATH.casefold() in page.url.casefold()


async def has_jsessionid(page: Page) -> bool:
    if page.is_closed():
        return False
    try:
        cookies = await page.context.cookies()
    except PlaywrightError:
        return False
    return any(cookie.get("name", "").casefold() == "jsessionid" and bool(cookie.get("value")) for cookie in cookies)


async def is_logged_in(page: Page) -> bool:
    return is_kp_url(page) and await has_jsessionid(page)


async def select_municipality_and_continue(page: Page) -> None:
    try:
        await page.wait_for_selector(AUTH_DROPDOWN, state="visible", timeout=KP_ACTION_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        return
    municipality = page.locator(AUTH_DROPDOWN)
    try:
        await municipality.select_option(label=KP_MUNICIPALITY)
    except PlaywrightError as error:
        raise KpLaunchError(f"Kunne ikke vælge {KP_MUNICIPALITY!r}.") from error
    button = await _find_visible_enabled_button(page, KP_ACTION_TIMEOUT_MS)
    await button.click(timeout=KP_ACTION_TIMEOUT_MS)
    await wait_for_page_ready(page)


async def wait_for_kp_ready(page: Page, timeout_ms: int = KP_LOGIN_TIMEOUT_MS) -> None:
    elapsed_ms = 0
    while elapsed_ms < timeout_ms:
        if page.is_closed():
            raise KpLaunchError("Browserfanen blev lukket under login.")
        if await is_logged_in(page):
            await wait_for_page_ready(page, timeout_ms)
            return
        await page.wait_for_timeout(KP_POLL_INTERVAL_MS)
        elapsed_ms += KP_POLL_INTERVAL_MS
    raise KpLaunchError(f"KP blev ikke klar efter login. Aktuel URL: {page.url}")


async def launch_kp(page: Page, session: BrowserSession, credential_name: str = KP_CREDENTIAL_NAME) -> None:
    if page.is_closed():
        raise KpLaunchError("Playwright-siden er lukket.")
    if not isinstance(credential_name, str) or not credential_name.strip():
        raise KpLaunchError("credential_name skal være en ikke-tom tekst.")
    recorder = getattr(session, "recorder", None)
    set_page = getattr(recorder, "set_page", None)
    if callable(set_page):
        set_page(page)
    page.set_default_timeout(KP_ACTION_TIMEOUT_MS)
    page.set_default_navigation_timeout(KP_NAVIGATION_TIMEOUT_MS)
    try:
        if await is_logged_in(page):
            if not is_kp_opgaveindbakke_url(page):
                await page.goto(KP_START_URL, wait_until="domcontentloaded")
            return
        await page.goto(KP_START_URL, wait_until="domcontentloaded")
        await wait_for_page_ready(page)
        if not await is_logged_in(page):
            await select_municipality_and_continue(page)
        if not await is_logged_in(page):
            await login_via_faelles_kommunal_idp(
                page=page,
                session=session,
                credential_name=credential_name.strip(),
            )
            await wait_for_kp_ready(page)
        if not is_kp_opgaveindbakke_url(page):
            await page.goto(KP_START_URL, wait_until="domcontentloaded")
            await wait_for_page_ready(page)
    except KpLaunchError:
        raise
    except (PlaywrightTimeoutError, PlaywrightError) as error:
        raise KpLaunchError(f"KP-launch fejlede: {type(error).__name__}: {error}. Aktuel URL: {page.url}") from error


async def _find_visible_enabled_button(page: Page, timeout_ms: int) -> Locator:
    elapsed_ms = 0
    while elapsed_ms < timeout_ms:
        for frame in page.frames:
            try:
                buttons = frame.locator(OK_BUTTON)
                for index in range(await buttons.count()):
                    candidate = buttons.nth(index)
                    if await candidate.is_visible() and await candidate.is_enabled():
                        return candidate
            except PlaywrightError:
                continue
        await page.wait_for_timeout(250)
        elapsed_ms += 250
    raise KpLaunchError("En synlig og aktiv OK/Vælg-knap blev ikke fundet.")
