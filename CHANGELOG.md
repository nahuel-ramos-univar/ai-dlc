# Changelog

## 0.6.0 — 2026-10-05

Bump: `minor`
Compare: [v0.5.2...v0.6.0](https://github.com/nahuel-ramos-univar/ai-dlc/compare/v0.5.2...v0.6.0)

### Added

- feat: preserve architectural discovery in generated module context ([`4bdc51b`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/4bdc51bb43e1abda4a84026352051f749300c233))
- feat: close planning and context runs in a canvas, with a story template ([`3c4379c`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/3c4379cd61758855622a1dc2eae416052d414e1e))
- feat: turn plan-work into a Product Owner planning skill ([`87d3ce7`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/87d3ce7007c40fdd541bbf69e6bf487bf79066d0))

### Fixed

- fix: require a module-context envelope and honest review fallback ([`7b322d3`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/7b322d3ab5826c19420581f4572bf89369d67362))
- fix: fail closed on plan validation and align plan-work contracts ([`e085c14`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/e085c14bb9e0c7681c6f5c5fa8350752c358d6ee))

### Other

- Merge pull request #10 from nahuel-ramos-univar/CTY-303 ([`4088dfb`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/4088dfb0c09e6edf00f5bd1ea1f408d0893efeae))

## 0.5.2 — 2026-10-05

Bump: `patch`
Compare: [v0.5.1...v0.5.2](https://github.com/nahuel-ramos-univar/ai-dlc/compare/v0.5.1...v0.5.2)

### Fixed

- fix: reuse one Jira confirmation across a migration and keep debug output out of the report ([`edc4c17`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/edc4c17d99b899449ff5d84d7570b709d2d3f36d))
- fix: reject pending as a migration disposition and surface missing Jira during migration ([`eb0c1de`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/eb0c1de108edde547f6264f6210dcdce788218bc))

### Other

- Merge pull request #9 from nahuel-ramos-univar/CTY-321-improvements ([`32bd875`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/32bd875412270abfda3543c6f0be59c97f05fc1d))

## 0.5.1 — 2026-10-02

Bump: `patch`
Compare: [v0.5.0...v0.5.1](https://github.com/nahuel-ramos-univar/ai-dlc/compare/v0.5.0...v0.5.1)

### Fixed

- fix: shared-methodology checkouts can't be classified as coordinator; reject distributed+retained ([`d4060c0`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/d4060c085499bf44cc608831fabe9ca7863c7672))
- fix: close migration safety gaps in sync-context legacy migration ([`a8c82c9`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/a8c82c963411eabc788adbf17ef2308a74d3b3bf))

### Other

- Merge pull request #8 from nahuel-ramos-univar/CTY-311 ([`1bfaeef`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/1bfaeef4233761dd2f32a330360dea24a01be41b))
- Merge pull request #7 from nahuel-ramos-univar/chore/pull-request-template ([`bcfc866`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/bcfc8662a3060bc338da60e0c4abfd499393765f))
- docs: add a default pull request template ([`fdbe840`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/fdbe8407e80ce6e4865029dbbe2fc0b98d81fd91))

## 0.5.0 — 2026-10-01

Bump: `minor`
Compare: [v0.4.0...v0.5.0](https://github.com/nahuel-ramos-univar/ai-dlc/compare/v0.4.0...v0.5.0)

### Added

- feat: add shared project onboarding and harden project references ([`4ccd1f8`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/4ccd1f844c3ec1ddcc8146f7facad9ab252c0597))

### Fixed

- fix: reject malformed hostnames, empty fields, and empty sections ([`fc6aa94`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/fc6aa9495db5d6cf9491024b7e862736bf846c11))

### Other

- Merge pull request #6 from nahuel-ramos-univar/CTY-321-sync-onboarding ([`900ad4d`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/900ad4dc1fdfb36c41685ba5ff11b609c8e13b81))

## 0.4.0 — 2026-10-01

Bump: `minor`
Compare: [v0.3.0...v0.4.0](https://github.com/nahuel-ramos-univar/ai-dlc/compare/v0.3.0...v0.4.0)

### Added

- feat: harden sync-context fingerprinting and candidate validation ([`b0da18f`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/b0da18fc1952685172b112a9d61800d96f4ac06d))

### Fixed

- fix: raise GitDiscoveryError when staged-diff comparison fails ([`6c9ae2b`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/6c9ae2b59405a058cab53c31114dcb88e1a1c5cc))

### Other

- Merge pull request #5 from nahuel-ramos-univar/CTY-321 ([`8405dc9`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/8405dc9242160f08bc8b139fb5f57437480eda62))

## 0.3.0 — 2026-09-29

Bump: `minor`
Compare: [v0.2.0...v0.3.0](https://github.com/nahuel-ramos-univar/ai-dlc/compare/v0.2.0...v0.3.0)

### Added

- feat: review generated context after sync ([`0d4f15d`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/0d4f15d32519caa0257dc9d1e18e91eae43abe58))

### Fixed

- fix: require local Context targets and reject duplicate canonical sections ([`c1e8c0c`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/c1e8c0c32167b1c2da3e06e81021bb87bae518bd))
- fix: validate declared context identity and align the skill catalog ([`dd4ff14`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/dd4ff149f9d94361c646b0444c982189850b7ae4))
- fix: validate context links against authorized repository roots ([`b3f4df9`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/b3f4df9b023878ca10d59d33c8b6d1db5246b980))

### Other

- Merge pull request #4 from nahuel-ramos-univar/feat/sync-context-review ([`5498a23`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/5498a2361ea6d1474bf5025366c5c0f144f98b4c))

## 0.2.0 — 2026-09-28

Bump: `minor`
Compare: [v0.1.1...v0.2.0](https://github.com/nahuel-ramos-univar/ai-dlc/compare/v0.1.1...v0.2.0)

### Added

- feat: add scaffold-project and drop dedicated governance and defect skills ([`8c42383`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/8c423831fd23d438185b158836bb24d5e33b63c1))
- feat: classify source scopes and fingerprint context without parent SHAs ([`0e1ec91`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/0e1ec9152623b57ea574f3e0cf582f0b1a85e67b))

### Fixed

- fix: fail unavailable fingerprints and include env templates ([`232cda4`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/232cda42047da44469486ca193220ced09ffe516))
- fix: keep context fingerprints stable and repository IDs unique ([`c3750d9`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/c3750d95d539c2727b9e1ecec2a1a0260a388cac))
- fix: block non-git-root writes and keep compact replies chat-only ([`d2193d0`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/d2193d0c93794e8f1f5ebac1e41d3bebfa1bcc81))

### Other

- Merge pull request #3 from nahuel-ramos-univar/feat/sync-context-quality ([`8114e6c`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/8114e6c51f241506ca6ebbd3fabb5bf52269bb85))

## 0.1.1 — 2026-09-23

Bump: `patch`
Compare: [v0.1.0...v0.1.1](https://github.com/nahuel-ramos-univar/ai-dlc/compare/v0.1.0...v0.1.1)

### Fixed

- fix: restore changelog intro after the baseline 0.1.0 entry ([`ca7f95e`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/ca7f95e4dd45038bb0c4af8c92befe976344b8a3))

### Other

- Merge pull request #2 from nahuel-ramos-univar/feat/plugin-version-bump ([`e2ecdd5`](https://github.com/nahuel-ramos-univar/ai-dlc/commit/e2ecdd53808d24413188b176838b03d829f1f37d))

Plugin versions after each releasable merge to `main`. Cursor Team Marketplace updates still require an admin or developer to refresh or reinstall the plugin; this file shows what changed in that version.

Unreleased work is not listed here until the release workflow runs.

## 0.1.0 — 2026-09-23

Initial tagged version matching `.cursor-plugin/plugin.json`. History before this tag is not replayed.
