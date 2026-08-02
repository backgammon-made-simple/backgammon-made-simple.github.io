const requireActiveTab = (activeTab) => {
  if (!activeTab) {
    throw new Error("Navigate the isolated browser tab before using it.");
  }
  return activeTab;
};

export function createIsolatedBrowserTab(browser) {
  if (!browser?.tabs?.finalize || !browser?.tabs?.new) {
    throw new Error("A browser with tab isolation support is required.");
  }

  let activeTab = null;
  const current = () => requireActiveTab(activeTab);

  return {
    get capabilities() { return current().capabilities; },
    get clipboard() { return current().clipboard; },
    get cua() { return current().cua; },
    get dev() { return current().dev; },
    get dom_cua() { return current().dom_cua; },
    get id() { return current().id; },
    get playwright() { return current().playwright; },
    async back() { return current().back(); },
    async close() {
      activeTab = null;
      await browser.tabs.finalize();
    },
    async forward() { return current().forward(); },
    async getJsDialog() { return current().getJsDialog(); },
    async goto(url) {
      await browser.tabs.finalize();
      activeTab = await browser.tabs.new();
      try {
        return await activeTab.goto(url);
      } catch (error) {
        if (!/Timed out waiting for load in tab/.test(String(error))) {
          throw error;
        }
        const requestedUrl = new URL(url).href;
        const activeUrl = new URL(await activeTab.url()).href;
        if (activeUrl !== requestedUrl) {
          throw error;
        }
        await activeTab.playwright.waitForLoadState({
          state: "domcontentloaded",
          timeoutMs: 30000
        });
        if ((await activeTab.playwright.locator("html").count()) !== 1) {
          throw error;
        }
      }
    },
    async reload() { return current().reload(); },
    async screenshot(options) { return current().screenshot(options); },
    async title() { return current().title(); },
    async url() { return current().url(); }
  };
}

export async function withIsolatedBrowserTab(browser, operation) {
  if (typeof operation !== "function") {
    throw new Error("An isolated browser operation is required.");
  }
  const tab = createIsolatedBrowserTab(browser);
  try {
    return await operation(tab);
  } finally {
    await tab.close();
  }
}
