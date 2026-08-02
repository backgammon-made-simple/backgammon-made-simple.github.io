import assert from "node:assert/strict";

import {
  createIsolatedBrowserTab,
  withIsolatedBrowserTab
} from "../scripts/testing/quality/browser/isolated_browser_tab.mjs";

const events = [];
let tabNumber = 0;
const browser = {
  tabs: {
    async finalize() { events.push("finalize"); },
    async new() {
      tabNumber += 1;
      const id = `tab-${tabNumber}`;
      events.push(`new:${id}`);
      return {
        id,
        playwright: { id: `playwright-${id}` },
        async goto(url) { events.push(`goto:${id}:${url}`); },
        async screenshot() { return id; },
        async url() { return `https://example.test/${id}`; }
      };
    }
  }
};

const isolated = createIsolatedBrowserTab(browser);
await assert.rejects(async () => isolated.url(), /Navigate the isolated/);
await isolated.goto("https://example.test/one");
assert.equal(isolated.id, "tab-1");
assert.equal(isolated.playwright.id, "playwright-tab-1");
await isolated.goto("https://example.test/two");
assert.equal(isolated.id, "tab-2");
assert.equal(await isolated.screenshot(), "tab-2");
await isolated.close();

assert.deepEqual(events, [
  "finalize",
  "new:tab-1",
  "goto:tab-1:https://example.test/one",
  "finalize",
  "new:tab-2",
  "goto:tab-2:https://example.test/two",
  "finalize"
]);

await assert.rejects(
  withIsolatedBrowserTab(browser, null),
  /isolated browser operation/
);

console.log("isolated browser tab contracts passed");
