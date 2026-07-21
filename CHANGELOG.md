## v1.1.1

Important update: Time-period and power protection configuration migrated from entity-based controls to custom Lovelace cards with dedicated services

### Added

- Add custom Lovelace card: hinen-period-card for charge/discharge period configuration
- Add custom Lovelace card: hinen-power-protection-card for power protection mode configuration
- Add services: set_period_times2 and set_power_protection_mode_time_period
- Add Battery Settable Min SOC Level sensor
- Add Battery Charge Max SOC number entity
- Add PeriodConfiguration and PowerProtectionModeConfiguration helper sensors

### Changed

- Refactor time-period and power protection configuration from entity-based controls to custom cards + services
- Implement dynamic SOC validation based on device specifications
- Add cross-entity validation: discharge min SOC must be less than or equal to charge max SOC
- Update README and Chinese documentation with card installation and configuration

### Removed

- Remove switch.py platform (PlatformSwitchEntity)
- Remove time.py platform (PlatformTimeEntity)
- Remove per-period number entities

## v1.1.0

Important update: Default credentials removed; integration requires applying for Client ID/Client Secret (see README for details)

### Added

- Add Client ID and Client Secret to config flow
- Add VPP Company
- Add Power protection

### Changed

- Update Readme documentation
- Require hinen-open-api==1.0.3
- Optimization time display

## v1.0.1

### Added

- New power sensors: generation power, total load power, battery power, grid total power
- Battery state of charge sensor: Total Battery SoC

### Changed

- Abstract the common part requests into PyPi
- Related document modifications

### Fixed

## v1.0.0

### Added

- First version

### Changed

### Fixed
