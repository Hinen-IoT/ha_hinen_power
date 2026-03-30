# Hinen Power Integration - Project Knowledge Base

**Project**: Home Assistant Custom Integration for Hinen IoT Power Devices  
**Language**: Python  
**Framework**: Home Assistant  
**Style**: Google Python Style Guide  
**Version**: 1.0.1

## OVERVIEW

Official Home Assistant custom integration for Hinen IoT smart power devices. Supports battery management systems with multiple working modes, time-period controls, and real-time power monitoring.

**Key Features**:
- OAuth2 authentication with Hinen Cloud API
- Multi-platform support: Sensor, Select, Number, Switch
- 5 working modes: self-consumption, battery priority, grid priority, time period, power protection
- 6 configurable time periods for charge/discharge control
- Real-time power monitoring (generation, load, battery, grid)

## STRUCTURE

```
.
├── custom_components/hinen_power/    # Integration source (12 files)
│   ├── __init__.py                   # Entry point, OAuth setup
│   ├── manifest.json                 # Integration metadata
│   ├── config_flow.py                # Configuration UI flow
│   ├── coordinator.py                # Data update coordinator
│   ├── entity.py                     # Base entity class
│   ├── const.py                      # Constants, property mappings
│   ├── auth_config.py                # OAuth2 token management
│   ├── application_credentials.py    # HA credentials integration
│   ├── sensor.py                     # 13 sensor entities
│   ├── number.py                     # 43 number entities (largest file)
│   ├── select.py                     # Working mode selector
│   ├── switch.py                     # 12 switch entities
│   └── translations/                 # UI strings (en, zh-Hans)
├── .github/workflows/                # CI/CD
│   ├── validate.yaml                 # HACS + hassfest validation
│   └── release.yaml                  # Auto-release on tag
├── doc/                              # Documentation (zh)
├── install.sh                        # Installation script
├── hacs.json                         # HACS metadata
└── .pylintrc                         # Google style linting
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new entity type | `sensor.py`, `number.py`, etc. | Follow platform pattern |
| OAuth/Auth changes | `auth_config.py`, `__init__.py` | Uses HA's OAuth2 flow |
| New device properties | `const.py` → platform files | Map API names in PROPERTIES |
| UI strings | `translations/*.json` | Both English and Chinese |
| Config flow | `config_flow.py` | OAuth2 redirect handling |
| Data updates | `coordinator.py` | Cloud polling pattern |

## CODE MAP

**Core Classes**:

| Class | File | Purpose |
|-------|------|---------|
| `HinenDataUpdateCoordinator` | `coordinator.py` | Manages API polling, device data cache |
| `HinenDeviceEntity` | `entity.py` | Base entity with device info |
| `AsyncConfigEntryAuth` | `auth_config.py` | OAuth2 token refresh |
| `HinenSelect` | `select.py` | Working mode selector entity |

**Platform Entry Points**:
- `async_setup_entry` in each platform file
- Registers entities via `async_add_entities`

## CONVENTIONS

### Import Order
1. `__future__` annotations
2. Third-party (hinen_open_api)
3. homeassistant.* imports
4. Relative imports (`.const`, `.coordinator`)

### Naming
- **Constants**: `UPPER_SNAKE_CASE` in `const.py`
- **Classes**: `PascalCase`
- **Functions/Methods**: `snake_case`
- **Private**: `_leading_underscore`

### Entity Pattern
```python
class HinenSensor(HinenDeviceEntity, SensorEntity):
    """Sensor for Hinen device."""
    
    def __init__(self, coordinator, api, description, device_id):
        super().__init__(coordinator, api, description, device_id)
        # Set entity-specific attributes
    
    @property
    def native_value(self):
        return self.coordinator.data[self._device_id].get(self.entity_description.key)
```

### Property Mapping
- API uses PascalCase: `"WorkModeSetting"`, `"GenerationPower"`
- Constants use snake_case mapped in `PROPERTIES` dict in `const.py`

## ANTI-PATTERNS

**DO NOT**:
- Hardcode API endpoints - use `hinen-open-api` library
- Skip OAuth2 flow - must use HA's `AbstractOAuth2Implementation`
- Block in async methods - always use `await`
- Modify manifest without version bump
- Skip translations for new entities

**NEVER**:
- Import from `homeassistant.core` directly - use typed imports
- Use f-strings for translations - use string keys
- Commit `__pycache__` or `.pyc` files

## COMMANDS

```bash
# Install to HA config
./install.sh /path/to/homeassistant/config

# Lint (requires pylint)
pylint custom_components/hinen_power/ --rcfile=.pylintrc

# Local HA test (requires HA installed)
hass -c /path/to/test_config

# Git workflow
git checkout -b feature/name
# ... changes ...
git commit -m "feat: add new sensor"
git push origin feature/name
```

### Commit Format
```
type: subject

body

footer
```
Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

## VALIDATION

CI runs on push/PR to `main`:
- **hassfest**: Home Assistant official validation
- **HACS**: Community store validation
- **setup**: Tests install script + HA startup

Release creates `hinen_power.zip` automatically on GitHub release.

## NOTES

- **HA Version**: Requires Core ≥ 2025.8.1
- **Quality Scale**: Bronze
- **IoT Class**: Cloud polling
- **External API**: `hinen-open-api==1.0.0`
- **No tests**: Project currently lacks test suite
- **No pre-commit**: Lint manually with pylint
- **Bilingual**: All UI strings in `en.json` and `zh-Hans.json`

## WORKING MODES

| Mode | Value | Key Constants |
|------|-------|---------------|
| None | 0 | `WORK_MODE_NONE` |
| Self Consumption | 10 | `WORK_MODE_SELF_CONSUMPTION` |
| Battery Priority | 11 | `WORK_MODE_BATTERY_PRIORITY` |
| Grid Priority | 12 | `WORK_MODE_GRID_PRIORITY` |
| Time Period | 13 | `WORK_MODE_TIME_PERIOD` |
| Power Keeping | 14 | `WORK_MODE_POWER_KEEPING` |
