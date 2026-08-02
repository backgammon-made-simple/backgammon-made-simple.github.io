# UX testing

UX testing has three explicit layers:

1. `quick.sh` validates browser-helper syntax and source contracts.
2. Browser helpers in `browser/` automate the five-viewport comprehensive route
   matrix against a served `site/_site`.
3. Checklists in `human-instructions/` cover visual and experiential details
   automation cannot establish.

The shell runners do not control a browser. They therefore report browser and
human phases as `NOT RUN`; follow [UX-TESTING-SOP.md](UX-TESTING-SOP.md) to
perform and record those phases.
