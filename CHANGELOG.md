# Changelog

All notable changes to this project will be documented in this file.

This changelog is maintained by [python-semantic-release](https://python-semantic-release.readthedocs.io/).

<!-- version list -->

## v1.1.0 (2026-09-07)

Met dank aan @mingoes (login-fix na de IDP-wijziging plus de accountkeuze, #36) en @wienke (paginering via Range-headers #39, Rich-escaping #38 en de afkapbug in mededelingen #37). Zonder #36 werkte inloggen sinds eind augustus niet meer.

### Bug Fixes

- **cli**: Avoid shadowing the --account option in login ([`3ae4b85`](https://github.com/anneschuth/parro-cli/commit/3ae4b85da725b5e118b3da650f59b79724918d41))

- **cli**: Escape user text so Rich doesn't swallow bracketed parts ([`a1ec29f`](https://github.com/anneschuth/parro-cli/commit/a1ec29fc41a52eb0c1af502676e0505b95e405ca))

- **cli**: Show full announcement contents instead of cutting at 500 chars ([`b00abfe`](https://github.com/anneschuth/parro-cli/commit/b00abfe094cdd62de5fda1400ff7796359d41560))

- **login**: Follow IDP form field names and handle the account chooser ([`4ad4d1d`](https://github.com/anneschuth/parro-cli/commit/4ad4d1d6ef2abd730263e5cadcda49dcb5ad4a17))

### Chores

- **deps**: Bump actions/setup-python from 6 to 7 ([#34](https://github.com/anneschuth/parro-cli/pull/34), [`f55f363`](https://github.com/anneschuth/parro-cli/commit/f55f36347c54a2aa9d377778b6082e21058690dc))

- **deps**: Bump click from 8.4.2 to 8.5.0 ([`64284c4`](https://github.com/anneschuth/parro-cli/commit/64284c4e3a2b9f3d4470cdc90e9c09bb8edd5716))

- **deps**: Bump ruff from 0.16.4 to 0.16.5 ([`6724d5d`](https://github.com/anneschuth/parro-cli/commit/6724d5d992f8dad4efbe07096d5e0932aec8c766))

- **deps**: Bump ty from 0.0.73 to 0.0.75 ([`b6d2811`](https://github.com/anneschuth/parro-cli/commit/b6d2811447ee21ce9b12068cb1459c5d81f79900))

### Documentation

- Add contributing section and credit contributors ([`350b651`](https://github.com/anneschuth/parro-cli/commit/350b6514e5f12d8dc58562f083c71ab8669a9744))

### Features

- **client**: Page chat messages and announcements with HTTP Range headers ([`4942a5b`](https://github.com/anneschuth/parro-cli/commit/4942a5b13b76ab7226a266a55b72e070af843a17))

## v1.0.4 (2026-08-21)

### Bug Fixes

- **deps**: Refresh locked dependencies ([#35](https://github.com/anneschuth/parro-cli/pull/35), [`03029e0`](https://github.com/anneschuth/parro-cli/commit/03029e000e839eff35a244d6ff3424d8904673d6))

### Chores

- **deps**: Bump actions/checkout from 6 to 7 ([#33](https://github.com/anneschuth/parro-cli/pull/33), [`7b1cb3b`](https://github.com/anneschuth/parro-cli/commit/7b1cb3b01077de734e04cf3373ff7d837fdccbba))

- **deps**: Bump click from 8.3.1 to 8.3.2 ([#9](https://github.com/anneschuth/parro-cli/pull/9), [`b473960`](https://github.com/anneschuth/parro-cli/commit/b4739604a0f34dc9e0dd79579f31725963169d8b))

- **deps**: Bump click from 8.3.2 to 8.4.1 ([#27](https://github.com/anneschuth/parro-cli/pull/27), [`6b725ac`](https://github.com/anneschuth/parro-cli/commit/6b725ac1e0fbf25387654fd0bc9aecdd2ca5b6e7))

- **deps**: Bump peter-evans/create-pull-request from 7 to 8 ([#4](https://github.com/anneschuth/parro-cli/pull/4), [`52ce548`](https://github.com/anneschuth/parro-cli/commit/52ce548c549516cbb98d28381b99bd9aa955054a))

- **deps**: Bump pre-commit from 4.5.1 to 4.6.0 ([#18](https://github.com/anneschuth/parro-cli/pull/18), [`bb85016`](https://github.com/anneschuth/parro-cli/commit/bb8501662e5f3acf83ac18cf02b9295d15e74e53))

- **deps**: Bump pytest from 9.0.2 to 9.0.3 ([#12](https://github.com/anneschuth/parro-cli/pull/12), [`f298082`](https://github.com/anneschuth/parro-cli/commit/f298082b3391890645723d898fcfb2216b4a26b1))

- **deps**: Bump pytest from 9.0.3 to 9.1.0 ([#30](https://github.com/anneschuth/parro-cli/pull/30), [`f40f970`](https://github.com/anneschuth/parro-cli/commit/f40f97074e1a40f6eae63f5823761dfb3ea854ac))

- **deps**: Bump rich from 14.3.3 to 15.0.0 ([#14](https://github.com/anneschuth/parro-cli/pull/14), [`55a394c`](https://github.com/anneschuth/parro-cli/commit/55a394ce96e4b85a1de7c862473b1762498c2c76))

- **deps**: Bump ruff from 0.15.11 to 0.15.17 ([#32](https://github.com/anneschuth/parro-cli/pull/32), [`1b03192`](https://github.com/anneschuth/parro-cli/commit/1b0319277b55df1b147155d35fcacca3f8a1156d))

- **deps**: Bump ruff from 0.15.6 to 0.15.9 ([#11](https://github.com/anneschuth/parro-cli/pull/11), [`8d914f2`](https://github.com/anneschuth/parro-cli/commit/8d914f2bc1d7aad0cb1935994d2c2f4b9bdf2a2f))

- **deps**: Bump ruff from 0.15.9 to 0.15.11 ([#16](https://github.com/anneschuth/parro-cli/pull/16), [`bf035e1`](https://github.com/anneschuth/parro-cli/commit/bf035e1da34b6812e0435448d4c2a18048d57a40))

- **deps**: Bump ty from 0.0.23 to 0.0.29 ([#10](https://github.com/anneschuth/parro-cli/pull/10), [`83feb3d`](https://github.com/anneschuth/parro-cli/commit/83feb3d110a2010c4751600817a0e2cce8ec9158))

- **deps**: Bump ty from 0.0.29 to 0.0.32 ([#15](https://github.com/anneschuth/parro-cli/pull/15), [`263c0ac`](https://github.com/anneschuth/parro-cli/commit/263c0acdad90554318d34c726369b330f9f13adc))

- **deps**: Bump ty from 0.0.32 to 0.0.49 ([#31](https://github.com/anneschuth/parro-cli/pull/31), [`3ae279d`](https://github.com/anneschuth/parro-cli/commit/3ae279da3272cb3a1a0fea6f4a3fbd5fc9842d08))

## v1.0.3 (2026-03-23)

### Bug Fixes

- **ci**: Add permissions for pre-commit autoupdate workflow ([`eb99c38`](https://github.com/anneschuth/parro-cli/commit/eb99c38c12ec09f78b9410a23c1f45db44b0c095))

### Chores

- Add Dependabot for uv and GitHub Actions updates ([`1251b2f`](https://github.com/anneschuth/parro-cli/commit/1251b2fa66f14a8b39a17e918648b855e4afb857))

- **deps**: Bump actions/checkout from 4 to 6 ([#3](https://github.com/anneschuth/parro-cli/pull/3), [`7818bb7`](https://github.com/anneschuth/parro-cli/commit/7818bb79dcfb6a9805185546922287978bda7355))

- **deps**: Bump actions/setup-python from 5 to 6 ([#1](https://github.com/anneschuth/parro-cli/pull/1), [`023a2c2`](https://github.com/anneschuth/parro-cli/commit/023a2c24049fdaf5002125192bbefa79ce9cc344))

- **deps**: Bump astral-sh/setup-uv from 5 to 7 ([#2](https://github.com/anneschuth/parro-cli/pull/2), [`36a21bb`](https://github.com/anneschuth/parro-cli/commit/36a21bb211683b2c7545102c3060c738a5ceee93))

### Continuous Integration

- Add weekly pre-commit hook autoupdate workflow ([`9ba6e73`](https://github.com/anneschuth/parro-cli/commit/9ba6e731b2347357522100ebc5a40c8e7459edc5))

### Documentation

- Update Homebrew tap from anneschuth/parro to anneschuth/tap ([`dd0300d`](https://github.com/anneschuth/parro-cli/commit/dd0300dd4f3d825d73969d2a5afa0ae7599226fc))

## v1.0.2 (2026-03-17)

### Bug Fixes

- Install uv and deps in pre-commit CI job ([`bf5d32d`](https://github.com/anneschuth/parro-cli/commit/bf5d32d229b19829c6ceda856118b57187a48ec0))

- Resolve type annotation issues found by ty ([`30e1be9`](https://github.com/anneschuth/parro-cli/commit/30e1be9219c39d58e8b1ffd5eedd0d3a1089307c))

- Ty needs project deps for import resolution ([`36f529f`](https://github.com/anneschuth/parro-cli/commit/36f529f94dbabe83fbeebab569445dad02ad014d))

### Continuous Integration

- Integrate ty type checker into toolchain ([`f70b228`](https://github.com/anneschuth/parro-cli/commit/f70b2285e89b9351da36c89014cc5a9e53d05d20))

## v1.0.1 (2026-03-17)

### Bug Fixes

- Use uvx for ruff in CI lint job ([`5419d74`](https://github.com/anneschuth/parro-cli/commit/5419d740c8613af77cc3578c6fe91ced95a80d31))

## v1.0.0 (2026-03-17)

Eerste release op PyPI, vanaf hier beheerd door semantic-release.

### Features

- Add py.typed marker for PEP 561 compliance ([`8ce074a`](https://github.com/anneschuth/parro-cli/commit/8ce074a))

### Bug Fixes

- CI lint and release workflow issues ([`26c2451`](https://github.com/anneschuth/parro-cli/commit/26c2451))

## v0.3.0 (2026-03-17)

### Features

- Click CLI with 12 commands and Rich formatted output
- Shell completion for bash, zsh, and fish
- `--json` flag for machine-readable output on all data commands
- Numbered attachment display with `parro open <n>`
- Cross-group announcement fetching with `parro announcements`

## v0.2.0

### Features

- Click-based CLI with shell completion
- Test suite with pytest
- Dutch README with badges

## v0.1.0

### Features

- Initial release
- OAuth2 authentication with PKCE (headless, no browser)
- Parro REST v2 API client
- Announcements, chatrooms, messages, children, groups, calendar, unread counts
- Clickable attachment links with `parro open <url>`
