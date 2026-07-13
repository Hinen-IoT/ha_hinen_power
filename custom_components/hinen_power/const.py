"""Constants for hello auth integration."""

import logging

DOMAIN = "hinen_power"
MANUFACTURER = "hinen"

CONF_DEVICES = "devices"
COORDINATOR = "coordinator"
AUTH = "auth"
HOST = "host"

LOGGER = logging.getLogger(__package__)

SERVICE_SET_PERIOD_TIMES2 = "set_period_times2"
SERVICE_SET_POWER_PROTECTION_MODE_TIME_PERIOD = "set_power_protection_mode_time_period"

POWER_PROTECTION_HELPER_SENSOR_KEY = "power_protection_mode_time_period_config"

# Hinen developer portal language codes
HINEN_LANGUAGE_ZH_CN = "zh_CN"
HINEN_LANGUAGE_EN_US = "en_US"
DEFAULT_HINEN_LANGUAGE = HINEN_LANGUAGE_EN_US

# HA language tag (BCP 47) -> Hinen developer portal language code
HA_LANGUAGE_TO_HINEN = {
    "zh-Hans": HINEN_LANGUAGE_ZH_CN,
    "zh-Hant": HINEN_LANGUAGE_ZH_CN,
    "zh": HINEN_LANGUAGE_ZH_CN,
}

# Feedback page URL template
FEEDBACK_URL_TEMPLATE = "https://developer.celinksmart.com/{}/feedback"

ATTR_REGION_CODE = "region_code"
ATTR_CLIENT_SECRET = "client_secret"
ATTR_STATUS = "status"
ATTR_ALERT_STATUS = "alert_status"
ATTR_DEVICE_NAME = "device_name"

REGION_CODE = "regionCode"
CLIENT_SECRET = "clientSecret"

# Work mode constants (values should match hinen_open_api.enum.WorkMode)
WORK_MODE_NONE = 0
WORK_MODE_SELF_CONSUMPTION = 10
WORK_MODE_BATTERY_PRIORITY = 11
WORK_MODE_GRID_PRIORITY = 12
WORK_MODE_TIME_PERIOD = 13
WORK_MODE_POWER_KEEPING = 14

# HA-specific translation keys for work modes
WORK_MODE_OPTIONS = {
    WORK_MODE_NONE: "none",
    WORK_MODE_SELF_CONSUMPTION: "self_consumption",
    WORK_MODE_BATTERY_PRIORITY: "battery_priority",
    WORK_MODE_GRID_PRIORITY: "grid_priority",
    WORK_MODE_TIME_PERIOD: "time_period",
    WORK_MODE_POWER_KEEPING: "power_keeping",
}

WORK_MODE_SETTING = "work_mode_setting"
LOAD_FIRST_STOP_SOC = "load_first_stop_soc"
CHARGE_STOP_SOC = "charge_stop_soc"
GRID_FIRST_STOP_SOC = "grid_first_stop_soc"
CHARGE_POWER_SET = "charge_power_set"
DISCHARGE_POWER_SET = "discharge_power_set"
CD_PERIOD_TIMES2 = "cd_period_times2"
CD_PERIOD_WEEK_SUPPORT = "cd_period_week_support"
POWER_PROTECTION_MODE_TIME_PERIOD = "power_protection_mode_time_period"

# CD Period Times 2 nested property keys (API field names)
PERIOD_ENABLE = "periodEnable"
PERIOD_TIME_START = "periodTimeStart"
PERIOD_TIME_RATE = "periodTimeRate"
PERIOD_TIME_END = "periodTimeEnd"
PERIOD_TIME_STOP_SOC = "periodTimeStopSoc"
PERIOD_WEEK_ENABLE = "PeriodWeekEnable"

# Power Protection Mode Time Period nested property keys (API field names)
PERIOD_SOC = "PeriodSOC"
PERIOD_AC_ENABLE = "PeriodACEnable"
PERIOD_START_TIME = "PeriodStartTime"
PERIOD_POWER = "PeriodPower"

# VPP Type constants (values from hinen_open_api enum)
VPP_TYPE_NONE = 0
VPP_TYPE_EVERGEN = 1
VPP_TYPE_SYNERGY = 3
VPP_TYPE_GBB_OPTIMIZER = 5
VPP_TYPE_TEST = 100

VPP_TYPE_OPTIONS = {
    VPP_TYPE_NONE: "none",
    VPP_TYPE_EVERGEN: "evergen",
    VPP_TYPE_SYNERGY: "synergy",
    VPP_TYPE_GBB_OPTIMIZER: "gbb_optimizer",
    VPP_TYPE_TEST: "test",
}

CUMULATIVE_CONSUMPTION = "cumulative_consumption"
CUMULATIVE_PRODUCTION_ACTIVE = "cumulative_production_active"
CUMULATIVE_GRID_FEED_IN = "cumulative_grid_feed_in"
TOTAL_CHARGING_ENERGY = "total_charging_energy"
TOTAL_DISCHARGING_ENERGY = "total_discharging_energy"
CUMULATIVE_ENERGY_PURCHASED = "cumulative_energy_purchased"
# Power sensors
GENERATION_POWER = "generation_power"
TOTAL_LOAD_POWER = "total_load_power"
BATTERY_POWER = "battery_power"
GRID_TOTAL_POWER = "grid_total_power"
# Battery charge level sensor
SOC = "soc"
# VPP Type sensor
VPP_TYPE = "vpp_type"

PROPERTIES = {
    LOAD_FIRST_STOP_SOC: "LoadFirstStopSOC",
    CHARGE_STOP_SOC: "ChargeStopSOC",
    GRID_FIRST_STOP_SOC: "GridFirstStopSOC",
    CD_PERIOD_TIMES2: "CDPeriodTimes2",
    CD_PERIOD_WEEK_SUPPORT: "CDPeriodWeekSupport",
    POWER_PROTECTION_MODE_TIME_PERIOD: "PowerProtectionModeTimePeriod",
    WORK_MODE_SETTING: "WorkModeSetting",
    CUMULATIVE_CONSUMPTION: "CumulativeConsumption",
    CUMULATIVE_PRODUCTION_ACTIVE: "CumulativeProductionActive",
    CUMULATIVE_GRID_FEED_IN: "CumulativeGridFeedIn",
    TOTAL_CHARGING_ENERGY: "TotalChargingEnergy",
    TOTAL_DISCHARGING_ENERGY: "TotalDischargingEnergy",
    CUMULATIVE_ENERGY_PURCHASED: "CumulativeEnergyPurchased",
    # Power sensors
    GENERATION_POWER: "GenerationPower",
    TOTAL_LOAD_POWER: "TotalLoadPower",
    BATTERY_POWER: "BatteryPower",
    GRID_TOTAL_POWER: "GridTotalPower",
    # Battery charge level sensor
    SOC: "SOC",
    # VPP Type sensor
    VPP_TYPE: "VPPType",
}

ATTR_AUTH_LANGUAGE = "page_language"
ATTR_REDIRECTION_URL = "redirection_url"
SUPPORTED_LANGUAGES = [("en_US", "English"), ("zh_CN", "简体中文")]


