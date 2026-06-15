# Home Assistant Hinen Power

[English](./README.md) | [简体中文](./doc/README_zh.md)

Hinen Power integration is an official Home Assistant integration component provided by Hinen, which allows you to use Hinen IoT smart devices in Home Assistant.

## Installation

> Home Assistant version requirements:
>
> - Core ≥ 2025.8.1
> - Operating System ≥ 13.0

### Method 1: Download from GitHub using git clone command

```bash
cd config
git clone https://github.com/Hinen-IoT/ha_hinen_power.git
cd ha_hinen_power
./install.sh ../
```

It is recommended to use this method to install the Hinen integration. When you want to update to a specific version, you only need to switch to the corresponding Tag.

For example, to update the Hinen integration version to v1.0.0

```bash
cd config/ha_hinen_power
git fetch
git checkout v1.0.0
./install.sh ../
```

Note: The following "config" needs to be replaced with the local HASS configuration directory path.

### Method 2: [HACS](https://hacs.xyz/)

Install the Hinen integration from HACS with one click:

Pending integration

### Method 3: Manual installation via [Samba](https://github.com/home-assistant/addons/tree/master/samba) or [FTPS](https://github.com/hassio-addons/addon-ftp)

Download and copy the `custom_components/hinen_power` folder to the `config/custom_components` folder of Home Assistant.

# Entities
The Hinen Power integration allows you to connect Hinen devices to Home Assistant. For each device you add, the following entities will be created:

- Sensor
  - Alert status
  - Device status
  - Cumulative electricity consumption
  - Cumulative power generation
  - Cumulative grid connection
  - Cumulative energy purchased
  - Cumulative charging
  - Cumulative discharging
  - Generation power
  - Total load power
  - Battery power
  - Grid total power
  - Total Battery SoC
  - VPP Company

- Select
  - Working mode (state options: not enabled, self-consumption, battery priority, grid priority, time period control, power protection mode)

- Number
  - Battery discharge minimum SOC
  - Battery charge cutoff SOC
  - Battery discharge cutoff SOC
  - Time period related control (6: Period 1, Period 2, Period 3, Period 4, Period 5, Period 6, if not set, the default value is 0)
    - Period 1 start time
    - Period 1 charge/discharge power percentage
    - Period 1 end time
    - Period 1 cutoff SOC
  - Power protection time period configuration (6: Period 1, Period 2, Period 3, Period 4, Period 5, Period 6, if not set, the default value is 0)
    - Period 1 SOC
    - Period 1 start time
    - Period 1 power
  
- Switch
  - Time period control (Period 1-6)
    - Period 1 enable
    - Period 2 enable
    - Period 3 enable
    - Period 4 enable
    - Period 5 enable
    - Period 6 enable
  - Power protection AC enable (Period 1-6)
    - Period 1 AC enable
    - Period 2 AC enable
    - Period 3 AC enable
    - Period 4 AC enable
    - Period 5 AC enable
    - Period 6 AC enable

# Prerequisites

To use this integration, you need to have a corresponding Hinen Solar account and one or more devices under your account;

# Configuration

1. Apply for your Client ID and Client Secret on the [Hinen Developer Portal](https://developer.celinksmart.com/en_US/feedback).
2. Add the integration and fill in the configuration form:
   - **Certification page language**: The language of the Hinen authentication page.
   - **Client ID**: The Client ID you obtained from the developer portal.
   - **Client Secret**: The Client Secret you obtained from the developer portal.
   - **Redirect address**: The address of your Home Assistant instance (do not end with "/").
3. You will be redirected to the Hinen OAuth2 authentication page. Select your region and log in to your Hinen Solar account.
4. If everything goes well, you will be redirected back to your Home Assistant instance for authorization, and a list of all available devices under your account will be displayed. Select the device(s) you want to add.

# Custom Cards
Optional: Simply configure custom card examples based on Hinen's related entities to achieve better control of Hinen devices

To set up a custom card, you need to replace the **device identifier** with **your own device identifier**, the steps are as follows

1. Go to "**Home > Developer Tools > Templates**" and put the following yaml configuration into the template.
2. Find any entity to view the entity identifier **to get the corresponding device identifier**. For example: device status entity (sensor.6kw_0048_status), the device identifier is "6kw_0048".
3. Update the **device_name** variable value with your own device identifier
4. Copy the generated yaml configuration
5. Go to "**Home > Overview > Edit > Add Card > Manual Edit**", put the copied yaml configuration into the template and click finish

## VPP Company
```yaml
{% set device_name = "device identifier" %}
type: entities
entities:
  - entity: sensor.{{device_name}}_vpp_company
title: VPP Company
state_color: true
visibility:
  - condition: state
    entity: sensor.{{device_name}}_vpp_company
    state: none
```

## Device Working Mode Settings (Note: Will be hidden when VPP Company exists)

```yaml
{% set device_name = "device identifier" %}

type: entities
entities:
  - entity: select.{{device_name}}_work_mode
title: Working Mode Settings
state_color: true
visibility:
  - condition: state
    entity: sensor.{{device_name}}_vpp_company
    state: none
```

## Device Information

```yaml
{% set device_name = "device identifier" %}

type: entities
entities:
  - entity: sensor.{{device_name}}_status
  - entity: sensor.{{device_name}}_alert_status
  - entity: sensor.{{device_name}}_generation_power
  - entity: sensor.{{device_name}}_total_load_power
  - entity: sensor.{{device_name}}_battery_power
  - entity: sensor.{{device_name}}_grid_total_power
  - entity: sensor.{{device_name}}_total_battery_soc
title: Working Mode Settings
state_color: true
```
## Display attributes associated with each mode according to working mode (Note: Will be hidden when VPP Company exists)

```yaml
{% set device_name = "device identifier" %}

type: vertical-stack
cards:
  - type: conditional
    conditions:
      - condition: state
        entity: select.{{ device_name }}_work_mode
        state: self_consumption
    card:
      type: entities
      title: Self-consumption
      entities:
        - entity: number.{{ device_name }}_load_first_stop_soc
          name: Battery discharge minimum SOC
          secondary_info: last-updated
  
  - type: conditional
    conditions:
      - condition: state
        entity: select.{{ device_name }}_work_mode
        state: battery_priority
    card:
      type: entities
      title: Battery priority
      entities:
        - entity: number.{{ device_name }}_charge_stop_soc
          secondary_info: last-updated
          name: Battery charge cutoff SOC
  
  - type: conditional
    conditions:
      - condition: state
        entity: select.{{ device_name }}_work_mode
        state: grid_priority
    card:
      type: entities
      title: Grid priority
      entities:
        - entity: number.{{ device_name }}_grid_first_stop_soc
          secondary_info: last-updated
          name: Battery discharge cutoff SOC
  
  - type: conditional
    conditions:
      - condition: state
        entity: select.{{ device_name }}_work_mode
        state: time_period
    card:
      type: entities
      title: ⚡Charge/Discharge Period Configuration
      entities:
        {% for period in range(1, 7) %}
        - type: section
          label: Period {{ period }}
        - entity: switch.{{ device_name }}_charge_discharge_period_{{ period }}_enable
          name: Enable
        - entity: number.{{ device_name }}_charge_discharge_period_{{ period }}_rate
          name: Rate (%)
        - entity: number.{{ device_name }}_charge_discharge_period_{{ period }}_stop_soc
          name: Cutoff SOC (%)
        - entity: time.{{ device_name }}_charge_discharge_period_{{ period }}_start_time
          name: Start Time
        - entity: time.{{ device_name }}_charge_discharge_period_{{ period }}_end_time
          name: End Time
        {% endfor %}
      show_header_toggle: false
      state_color: true
  
  - type: conditional
    conditions:
      - condition: state
        entity: select.{{ device_name }}_work_mode
        state: power_keeping
    card:
      type: entities
      title: 🔋Power Protection Mode Configuration
      entities:
        {% for period in range(1, 7) %}
        - type: section
          label: Period {{ period }}
        - entity: switch.{{ device_name }}_power_protection_period_{{ period }}_ac_enable
          name: Enable
        - entity: number.{{ device_name }}_power_protection_period_{{ period }}_power
          name: Power
        - entity: time.{{ device_name }}_power_protection_period_{{ period }}_start_time
          name: Start Time
        - entity: number.{{ device_name }}_power_protection_period_{{ period }}_soc
          name: SOC
        {% endfor %}
      show_header_toggle: false
      state_color: true
visibility:
  - condition: state
    entity: sensor.{{device_name}}_vpp_company
    state: none
```