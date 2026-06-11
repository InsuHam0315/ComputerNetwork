# Design

## Source of truth
- Status: Active
- Last refreshed: 2026-06-11
- Primary product surfaces: Tkinter desktop GUI, Windows executable icon, header logo, transfer progress/log panels.
- Evidence reviewed: `README.md`, `gui/connectbox_gui.py`, `assets/connectbox_logo.png`, `assets/connectbox_icon.png`, `assets/connectbox_icon.ico`, `scripts/build_exe.py`.

## Brand
- Personality: modern, practical, trustworthy Windows desktop utility.
- Trust signals: clear status badge, explicit receive/send modes, visible progress, readable console log.
- Avoid: default gray Tkinter look, crowded controls, ambiguous transfer state, tiny or broken app identity.

## Product goals
- Goals: make ConnectBox look final-presentation ready while preserving existing LAN file/folder transfer behavior.
- Non-goals: changing protocol, server/client transfer logic, smoke test logic, or adding new transfer features.
- Success signals: logo is visible at header size, app/exe icon is valid, GUI imports/launches, smoke tests pass.

## Personas and jobs
- Primary personas: course evaluators, presenter, students testing LAN transfer.
- User jobs: start receive mode, select files/folders, send over LAN, monitor progress, confirm completion.
- Key contexts of use: Windows laptop/desktop during final presentation and LAN demo.

## Information architecture
- Primary navigation: segmented `받기` / `보내기` control.
- Core routes/screens: receive mode, send mode.
- Content hierarchy: brand header -> mode switch -> settings/selection card -> progress card -> console log.

## Design principles
- Principle 1: presentation clarity over visual complexity.
- Principle 2: state must be visible without reading logs.
- Tradeoffs: Tkinter-native implementation with no new runtime dependencies; use flat colors and spacing instead of custom canvas-heavy effects.

## Visual language
- Color: background `#F5F7FB`, card `#FFFFFF`, border `#E5E7EB`, primary `#2563EB`, accent `#3B82F6`, success `#22C55E`, console `#111827`.
- Typography: Segoe UI for app chrome, Consolas for logs.
- Spacing/layout rhythm: 22-24px outer padding, 14-18px card padding, 36-42px buttons.
- Shape/radius/elevation: flat Windows 11-like cards with subtle borders.
- Motion: none required.
- Imagery/iconography: 56px header logo from `connectbox_logo.png`; true ICO container from `connectbox_icon.png` for Windows/exe icon.

## Components
- Existing components to reuse: Tkinter/Ttk widgets, current GUI callbacks, current progress event shape.
- New/changed components: card sections, segmented tabs, status badges, typed button variants, console log panel.
- Variants and states: primary, success, secondary, danger buttons; ready/receiving/sending/complete/error badges.
- Token/component ownership: `gui/connectbox_gui.py` constants.

## Accessibility
- Target standard: readable contrast and keyboard focus preservation within Tkinter constraints.
- Keyboard/focus behavior: buttons and entries remain standard focusable controls.
- Contrast/readability: dark console with light text; high-contrast primary/success/danger states.
- Screen-reader semantics: standard Tkinter controls retained.
- Reduced motion and sensory considerations: no animation.

## Responsive behavior
- Supported breakpoints/devices: Windows desktop window, default 1100x760, minimum 980x700.
- Layout adaptations: content resizes horizontally; log panel owns scrolling.
- Touch/hover differences: not optimized for touch; hover uses native active button states.

## Interaction states
- Loading: active badge shows Receiving/Sending.
- Empty: send list shows `선택된 항목 없음`.
- Error: error badge and highlighted console line.
- Success: Complete badge, highlighted console line, completion messagebox.
- Disabled: active transfer disables its start button.
- Offline/slow network, if applicable: progress and log continue to expose transfer state.

## Content voice
- Tone: concise, presentation-friendly, mixed Korean labels with English product subtitle.
- Terminology: `받기`, `보내기`, `수신 시작`, `전송 시작`, `전송 속도`.
- Microcopy rules: explain LAN/IP context only where it prevents demo mistakes.

## Implementation constraints
- Framework/styling system: Python Tkinter only.
- Design-token constraints: keep colors as module constants in `gui/connectbox_gui.py`.
- Performance constraints: no heavy image processing at runtime; pre-normalize assets.
- Compatibility constraints: PyInstaller onefile build must include assets and use `assets/connectbox_icon.ico`.
- Test/screenshot expectations: compile/import/launch smoke, geometry manager check, existing smoke tests.

## Open questions
- [ ] Add a polished post-transfer action such as `저장 폴더 열기` after completion / owner: project team / impact: optional demo convenience.
