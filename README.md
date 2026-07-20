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
  - Battery Settable Min SOC Level
  - VPP Company
  - Period Configuration (helper sensor for custom Lovelace card)
  - Power Protection Mode Configuration (helper sensor for custom Lovelace card)
- Select

  - Working mode (state options: self-consumption, battery priority, grid priority, time period control, power protection mode)
- Number

  - Battery discharge minimum SOC
  - Battery charge maximum SOC
  - Battery charge cutoff SOC
  - Battery discharge cutoff SOC

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

# Custom Lovelace Cards

The integration includes custom Lovelace cards for advanced configuration of time-period settings. These cards provide a user-friendly interface for managing charge/discharge periods and power protection mode settings.

## Installation

After installing the integration, you need to register the card resources in Lovelace:

1. Go to **Settings → Dashboards**
2. Click the three-dot menu in the top right
3. Select **Resources**
4. Click **Add Resource**
5. Add the following resources:

   **For Charge/Discharge Period Card:**

   ```
   URL: /hinen_power/static/hinen-period-card.js
   Type: JavaScript Module
   ```

   **For Power Protection Card:**

   ```
   URL: /hinen_power/static/hinen-power-protection-card.js
   Type: JavaScript Module
   ```

## Card Configuration

To configure custom cards, you need to replace the **device identifier** in the YAML configuration below with **your own device identifier**. Follow these steps:

1. Go to **Home > Developer Tools > Templates**, and paste the following YAML configuration into the template editor.
2. Find any entity and check its entity ID to **get the corresponding device identifier**. For example: for the device status entity `sensor.6kw_0048_status`, the device identifier is `6kw_0048`.
3. Update the **device_name** variable value with your device identifier.
4. Copy the generated YAML configuration.
5. Go to **Home > Overview > Edit > Add Card > Manual**, paste the copied YAML configuration into the template, and click Done.

### Charge/Discharge Period Card

This card allows you to configure up to 20 time periods with:

- Enable/disable for each period
- Weekday selection (if supported by device)
- Start/end time
- Power rate
- Stop SOC

### Power Protection Card

This card allows you to configure up to 6 time periods for power protection mode with:

- AC enable for each period
- Start time
- SOC
- Power

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

## Device Working Mode Settings

This card will be hidden when VPP Company exists.

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
title: Device Information
state_color: true
```

## Base SOC Settings

This card shows common base SOC settings, with lower limits dynamically determined by the Battery Settable Min SOC Level sensor.

```yaml
{% set device_name = "device identifier" %}
type: entities
entities:
  - entity: number.{{device_name}}_load_first_stop_soc
    name: Load First Stop SOC
  - entity: number.{{device_name}}_battery_charge_max_soc
    name: Battery Charge Max SOC
title: Base SOC Settings
state_color: true
```

## Display attributes associated with each mode according to working mode (Note: Will be hidden when VPP Company exists)

This card will be hidden when VPP Company exists.

```yaml
{% set device_name = "device identifier" %}
type: vertical-stack
cards:

  - type: conditional
    conditions:
      - condition: state
        entity: select.{{device_name}}_work_mode
        state: battery_priority
    card:
      type: entities
      title: Battery Priority Mode
      entities:
        - entity: number.{{device_name}}_charge_stop_soc
          name: Charge Stop SOC

  - type: conditional
    conditions:
      - condition: state
        entity: select.{{device_name}}_work_mode
        state: grid_priority
    card:
      type: entities
      title: Grid Priority Mode
      entities:
        - entity: number.{{device_name}}_grid_first_stop_soc
          name: Grid First Stop SOC

  - type: conditional
    conditions:
      - condition: state
        entity: select.{{device_name}}_work_mode
        state: time_period
    card:
      type: custom:hinen-period-card
      entity: sensor.{{device_name}}_period_configuration
      title: ⚡ Charge/Discharge Period Configuration

  - type: conditional
    conditions:
      - condition: state
        entity: select.{{device_name}}_work_mode
        state: power_keeping
    card:
      type: custom:hinen-power-protection-card
      entity: sensor.{{device_name}}_power_protection_mode_configuration
      title: 🔋 Power Protection Mode Configuration
visibility:
  - condition: state
    entity: sensor.{{device_name}}_vpp_company
    state: none
```
