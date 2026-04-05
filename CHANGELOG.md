# Changelog

All notable changes to humanisateur.

## [0.2.0] - 2026-04-04

### Changed
- Renamed from `humanizer-pro` to `humanisateur`
- Scorer header updated to match

### Added
- Length-gated protocols (MICRO / LIGHT / STANDARD / FULL)
- Context/register gating (professional, academic, blog, personal, casual)
- Humanizer-tell detection (50+ fake-human patterns that now flag AS AI)
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
- Pure-stdlib Python scorer measuring 7 detection signals
- Banned words, phrases, and openers reference lists
- Worked before/after examples
