# Changelog

All notable changes to humanisateur.

## [0.3.0] - 2026-04-11

### Changed
- Repositioned the repo as an authentic-editing skill instead of a detector-evasion skill
- Removed platform-specific packaging and tool references from the skill and README
- Rewrote scorer headers, descriptions, and verdict labels to use neutral editing language
- Added Codex installation guidance to the README

### Fixed
- Example guidance no longer endorses inventing specifics during edits

## [0.2.0] - 2026-04-04

### Changed
- Renamed from `humanizer-pro` to `humanisateur`
- Scorer header updated to match

### Added
- Length-gated protocols (MICRO / LIGHT / STANDARD / FULL)
- Context/register gating (professional, academic, blog, personal, casual)
- Humanizer-tell detection (50+ fake-human patterns that often read as canned or forced)
- Fragment-run detection
- 15-point humanizer penalty added to scorer (now scored /85)
- Preservation rules: no invented content, ±10% length cap

### Fixed
- Over-application of voice injection on short professional text
- Goodhart's Law failure: scorer was gameable by mechanical metric-hitting

## [0.1.0] - 2026-04-03

### Added
- Initial release
- 5-phase rewrite protocol
- Pure-stdlib Python scorer measuring 7 writing-pattern signals
- Banned words, phrases, and openers reference lists
- Worked before/after examples
