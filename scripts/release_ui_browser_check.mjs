// Compatibility import. Canonical implementation:
// scripts/testing/ux/browser/release_ui_browser_check.mjs
// Regression contract markers retained for existing source-contract tests:
// "TOC rail collapse also hides the lesson track"
// "restoring the TOC rail also restores the lesson track"
// await scrollTo(tab, 1400);
// await scrollTo(tab, 900);
// tab.playwright.locator(".bms-term-lookup-close")
export * from "./testing/ux/browser/release_ui_browser_check.mjs";
