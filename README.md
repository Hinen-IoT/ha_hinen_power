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
./install.sh /config
```

It is recommended to use this method to install the Hinen integration. When you want to update to a specific version, you only need to switch to the corresponding Tag.

For example, to update the Hinen integration version to v1.0.0

```bash
cd config/ha_hinen_power
git fetch
git checkout v1.0.0
./install.sh /config
```

Note: The following "/config" needs to be replaced with the local HASS configuration directory path.

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
  - Cumulative charging
  - Cumulative discharging

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
  
- Switch (used in conjunction with working mode: time period control)
  - Period 1 enable
  - Period 2 enable
  - Period 3 enable
  - Period 4 enable
  - Period 5 enable
  - Period 6 enable

# Prerequisites

To use this integration, you need to have a corresponding Hinen Solar account and one or more devices under your account;

# Configuration

1. Jump to the Hinen oauth2 authentication page
2. Select your region and log in to your Hinen Solar account
3. If everything is normal, it will jump to the specified redirect address for authorization and display all optional devices under the account

# Custom Cards
Optional: Simply configure custom card examples based on Hinen's related entities to achieve better control of Hinen devices

To set up a custom card, you need to replace the **device identifier** with **your own device identifier**, the steps are as follows

1. Go to "**Home > Developer Tools > Templates**" and put the following yaml configuration into the template.
2. Find any entity to view the entity identifier **to get the corresponding device identifier**. For example: device status entity (sensor.6kw_0048_status), the device identifier is "6kw_0048".
3. Update the **device_name** variable value with your own device identifier
4. Copy the generated yaml configuration
5. Go to "**Home > Overview > Edit > Add Card > Manual Edit**", put the copied yaml configuration into the template and click finish

It is recommended to use this method to install the Hinen integration. When there is a specific version and you want to update to a specific version, you only need to switch to the corresponding Tag.

### Device Working Mode Settings

```yaml
{% set device_name = "device identifier" %}

type: entities
entities:
  - entity: select.{{device_name}}_work_mode
  - entity: sensor.{{device_name}}_status
  - entity: sensor.{{device_name}}_alert_status
title: Working Mode Settings
state_color: true
```
### Display attributes associated with each mode according to working mode

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
        - entity: number.{{ device_name }}_looad_first_stop_soc
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
      title: ⚡Charge/discharge priority time period configuration
      entities:
        {% for period in range(1, 7) %}
        - type: section
          label: Period {{ period }}
        - entity: switch.{{ device_name }}_cd_period_{{ period }}_enable
          name: Enable
        - entity: number.{{ device_name }}_cd_period_{{ period }}_rate
          name: Rate
        - entity: number.{{ device_name }}_cd_period_{{ period }}_stop_soc
          name: Cutoff SOC
        - entity: number.{{ device_name }}_cd_period_{{ period }}_start
          name: Start time
        - entity: number.{{ device_name }}_cd_period_{{ period }}_end
          name: End time
        {% endfor %}
      show_header_toggle: false
      state_color: true
```