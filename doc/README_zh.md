# Home Assistant Hinen Power

[English](../README.md) | [简体中文](./README_zh.md)

海能集成是一个由海能官方提供支持的 Home Assistant 的集成组件，它可以让您在 Home Assistant 中使用海能 IoT 智能设备。

## 安装

> Home Assistant 版本要求：
>
> - Core $\geq$ 2025.8.1
> - Operating System $\geq$ 13.0

### 方法 1：使用 git clone 命令从 GitHub 下载

```bash
cd config
git clone https://github.com/Hinen-IoT/ha_hinen_power.git
cd ha_hinen_power
./install.sh ../
```

推荐使用此方法安装海能集成。当有特定版本且您想要更新至特定版本时，只需要切换至相应的 Tag 。
例如，更新海能集成版本至 v1.0.0

```bash
cd config/ha_hinen_power
git fetch
git checkout v1.0.0
./install.sh ../
```

注意：以上“/config”需要替换成本地HASS配置目录路径

### 方法 2: [HACS](https://hacs.xyz/)

一键从 HACS 安装海能集成：

待集成

### 方法 3：通过 [Samba](https://github.com/home-assistant/addons/tree/master/samba) 或 [FTPS](https://github.com/hassio-addons/addon-ftp) 手动安装

下载并将 `custom_components/hinen_power` 文件夹复制到 Home Assistant 的 `config/custom_components` 文件夹下。

# 实体

Hinen Power 集成允许您将海能设备接入到Home Assistant，对于你添加的每一个设备，会创建以下实体：

- 传感器

  - 告警状态
  - 设备状态
  - 累计用电量
  - 累计发电量
  - 累计并网量
  - 累计购电量
  - 累计充电量
  - 累计放电量
  - 发电功率
  - 负载功率
  - 电池功率
  - 电网功率
  - 电池剩余容量
  - 电池可设置最小SOC
  - VPP公司
  - 时段配置（用于自定义 Lovelace 卡片的辅助传感器）
  - 保电模式配置（用于自定义 Lovelace 卡片的辅助传感器）
- 选择器

  - 工作模式（状态选项：自发自用、电池优先、并网优先、时间段控制、保电模式）
- 数字

  - 电池放电最小SOC
  - 电池充电最大SOC
  - 电池强充截止SOC
  - 电池强放截止SOC

# 前提条件

为了能够使用该集成，您需要有一个对应的Hinen Solar账号且您的账号下需要有一台或以上设备；

# 配置

1. 前往 [开发者平台](https://developer.celinksmart.com/zh_CN/feedback) 申请您的 Client ID 和 Client Secret。
2. 添加集成并填写配置表单：
   - **认证页面语言**：Hinen 认证页面的显示语言。
   - **Client ID**：从开发者平台获取的 Client ID。
   - **Client Secret**：从开发者平台获取的 Client Secret。
   - **重定向地址**：您的 Home Assistant 实例地址（不以"/"结尾）。
3. 页面将跳转到 Hinen OAuth2 认证页面，选择您的地区并登录您的 Hinen Solar 账号。
4. 如果一切正常，会跳转回您的 Home Assistant 实例进行授权，并显示账号下的所有可选设备。请选择您要添加的设备。

# 自定义 Lovelace 卡片

集成包含了用于高级时段配置的自定义 Lovelace 卡片。这些卡片为用户提供了友好的界面来管理充放电时段和保电模式设置。

## 安装

安装集成后，您需要在 Lovelace 中注册卡片资源：

1. 进入 **设置 → 仪表板**
2. 点击右上角的三个点菜单
3. 选择 **资源**
4. 点击 **添加资源**
5. 添加以下资源：

   **充放电时段卡片：**

   ```
   URL: /hinen_power/static/hinen-period-card.js
   类型: JavaScript 模块
   ```

   **保电模式卡片：**

   ```
   URL: /hinen_power/static/hinen-power-protection-card.js
   类型: JavaScript 模块
   ```

## 卡片配置

设置自定义卡片，需要将卡片配置中的**设备标识**替换成**自己的设备标识**，步骤如下：

1. 进入"**首页 > 开发者工具 > 模板**"，将以下 YAML 配置放到模板中。
2. 找到任意一个实体，查看实体标识**获取对应设备标识**。例如：设备状态实体（`sensor.6kw_0048_status`），设备标识为 `6kw_0048`。
3. 将 **device_name** 变量值更新为自己的设备标识。
4. 复制生成的 YAML 配置。
5. 进入"**首页 > 概览 > 编辑 > 添加卡片 > 手动编辑**"，将复制的 YAML 配置放到模板中点击完成即可。

### 充放电时段卡片

此卡片允许您配置最多 20 个时段，包含：

- 每个时段的启用/禁用
- 星期选择（如果设备支持）
- 开始/结束时间
- 功率速率
- 截止 SOC

### 保电模式卡片

此卡片允许您配置最多 6 个保电模式时段，包含：

- 每个时段的 AC 使能
- 开始时间
- SOC
- 功率

## VPP 公司

```yaml
{% set device_name = "设备标识" %}
type: entities
entities:
  - entity: sensor.{{device_name}}_vpp_company
title: VPP 公司
state_color: true
visibility:
  - condition: state
    entity: sensor.{{device_name}}_vpp_company
    state: none
```

## 设备工作模式设置

此卡片将在 VPP 公司存在时隐藏。

```yaml
{% set device_name = "设备标识" %}
type: entities
entities:
  - entity: select.{{device_name}}_work_mode
title: 工作模式设置
state_color: true
visibility:
  - condition: state
    entity: sensor.{{device_name}}_vpp_company
    state: none
```

## 设备信息

```yaml
{% set device_name = "设备标识" %}
type: entities
entities:
  - entity: sensor.{{device_name}}_status
  - entity: sensor.{{device_name}}_alert_status
  - entity: sensor.{{device_name}}_generation_power
  - entity: sensor.{{device_name}}_total_load_power
  - entity: sensor.{{device_name}}_battery_power
  - entity: sensor.{{device_name}}_grid_total_power
  - entity: sensor.{{device_name}}_total_battery_soc
title: 设备信息
state_color: true
```

## 基础SOC设置

此卡片显示通用的基础SOC设置

```yaml
{% set device_name = "设备标识" %}
type: entities
entities:
  - entity: number.{{device_name}}_load_first_stop_soc
    name: 电池放电最小SOC
  - entity: number.{{device_name}}_charge_max_soc
    name: 电池充电最大SOC
title: 电池SOC设置
state_color: true
```

## 根据工作模式显示各个模式下关联的属性

此卡片将在 VPP 公司存在时隐藏。

```yaml
{% set device_name = "设备标识" %}
type: vertical-stack
cards:

  - type: conditional
    conditions:
      - condition: state
        entity: select.{{device_name}}_work_mode
        state: battery_priority
    card:
      type: entities
      title: 电池优先模式
      entities:
        - entity: number.{{device_name}}_charge_stop_soc
          name: 充电截止 SOC

  - type: conditional
    conditions:
      - condition: state
        entity: select.{{device_name}}_work_mode
        state: grid_priority
    card:
      type: entities
      title: 电网优先模式
      entities:
        - entity: number.{{device_name}}_grid_first_stop_soc
          name: 电网优先截止 SOC

  - type: conditional
    conditions:
      - condition: state
        entity: select.{{device_name}}_work_mode
        state: time_period
    card:
      type: custom:hinen-period-card
      entity: sensor.{{device_name}}_period_configuration
      title: ⚡充放电优先时段配置

  - type: conditional
    conditions:
      - condition: state
        entity: select.{{device_name}}_work_mode
        state: power_keeping
    card:
      type: custom:hinen-power-protection-card
      entity: sensor.{{device_name}}_power_protection_mode_configuration
      title: 🔋保电模式配置
visibility:
  - condition: state
    entity: sensor.{{device_name}}_vpp_company
    state: none
```
