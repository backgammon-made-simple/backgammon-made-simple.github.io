import {
  DEFAULT_MANIFEST,
  runReleaseUiChecks,
  summarizeReport
} from "./release_ui_browser_check.mjs";

export { DEFAULT_MANIFEST, summarizeReport };

export async function runComprehensiveBrowserBaseline(options) {
  const manifest = options?.manifest || DEFAULT_MANIFEST;
  if (manifest.version !== 2) {
    throw new Error("The comprehensive browser baseline requires manifest version 2.");
  }
  return runReleaseUiChecks({ ...options, manifest });
}
