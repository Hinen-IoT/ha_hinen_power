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

- 选择器
  - 工作模式（状态选项：不启用、自发自用、电池优先、并网优先、时间段控制、保电模式）

- 数字
  - 电池放电最小SOC
  - 电池强充截止SOC
  - 电池强放截止SOC
  - 时段相关控制（6个：时段1，时段2，时段3，时段4，时段5，时段6，若无设置则默认值都是0）
    - 时段1起始时间
    - 时段1充放电功率百分比
    - 时段1结束时间
    - 时段1截止SOC
  - 保电模式时段配置（6个：时段1，时段2，时段3，时段4，时段5，时段6，若无设置则默认值都是0）
    - 时段1SOC
    - 时段1起始时间
    - 时段1功率
  
- 开关
  - 时间段控制（时段1-6）
    - 时段1使能
    - 时段2使能
    - 时段3使能
    - 时段4使能
    - 时段5使能
    - 时段6使能
  - 保电模式交流使能（时段1-6）
    - 时段1交流使能
    - 时段2交流使能
    - 时段3交流使能
    - 时段4交流使能
    - 时段5交流使能
    - 时段6交流使能

# 前提条件

为了能够使用该集成，您需要有一个对应的Hinen Solar账号且您的账号下需要有一台或以上设备；

# 配置
1. 添加集成并按配置页面配置重定向地址(注意：重定向地址就是您的Home Assistant实例地址，不以”/“结尾)
2. 跳转到Hinen oauth2认证页面
3. 选择您的地区以及登录您的Hinen Solar账号
4. 如果一切正常，会跳转到您的Home Assistant实例进行授权并显示账号下的所有可选设备

# 自定义卡片
可选：根据hinen的相关实体简单配置自定义卡片示例，以达到更好对Hinen设备控制的效果

设置自定义卡片，需要将卡片配置中的**设备标识**替换成**自己的设备标识**，步骤如下
1. 进入"**首页>开发者工具>模板**"，将以下yaml配置放到模板中。
2. 找到任意一个实体，查看实体标识**获取对应设备标识**。例如：设备状态实体（sensor.6kw_0048_status），设备标识为“6kw_0048” 
3. 将**device_name**变量值更新为自己设备标识
4. 复制生成的yaml配置
5. 进入"**首页>概览>编辑>添加卡片>手动编辑**"，将复制的yaml配置放到模板中点击完成即可

## 设备工作模式设置

```yaml
{% set device_name = "你的设备标识" %}

type: entities
entities:
  - entity: select.{{device_name}}_work_mode
  - entity: sensor.{{device_name}}_status
  - entity: sensor.{{device_name}}_alert_status
  - entity: sensor.{{device_name}}_generation_power
  - entity: sensor.{{device_name}}_total_load_power
  - entity: sensor.{{device_name}}_battery_power
  - entity: sensor.{{device_name}}_grid_total_power
  - entity: sensor.{{device_name}}_total_battery_soc
title: 工作模式设置
state_color: true
```
## 根据工作模式显示各个模式下关联的属性

```yaml
{% set device_name = "你的设备标识" %}

type: vertical-stack
cards:
  - type: conditional
    conditions:
      - condition: state
        entity: select.{{ device_name }}_work_mode
        state: self_consumption
    card:
      type: entities
      title: 自发自用
      entities:
        - entity: number.{{ device_name }}_load_first_stop_soc
          name: 电池放电最小SOC
          secondary_info: last-updated
  
  - type: conditional
    conditions:
      - condition: state
        entity: select.{{ device_name }}_work_mode
        state: battery_priority
    card:
      type: entities
      title: 电池优先
      entities:
        - entity: number.{{ device_name }}_charge_stop_soc
          secondary_info: last-updated
          name: 电池强充截止SOC
  
  - type: conditional
    conditions:
      - condition: state
        entity: select.{{ device_name }}_work_mode
        state: grid_priority
    card:
      type: entities
      title: 并网优先
      entities:
        - entity: number.{{ device_name }}_grid_first_stop_soc
          secondary_info: last-updated
          name: 电池强放截止SOC
  
  - type: conditional
    conditions:
      - condition: state
        entity: select.{{ device_name }}_work_mode
        state: time_period
    card:
      type: entities
      title: ⚡充放电优先时段配置
      entities:
        {% for period in range(1, 7) %}
        - type: section
          label: 时段{{ period }}
        - entity: switch.{{ device_name }}_cd_period_{{ period }}_enable
          name: 启用
        - entity: number.{{ device_name }}_cd_period_{{ period }}_rate
          name: 速率
        - entity: number.{{ device_name }}_cd_period_{{ period }}_stop_soc
          name: 截止SOC
        - entity: number.{{ device_name }}_cd_period_{{ period }}_start
          name: 开始时间
        - entity: number.{{ device_name }}_cd_period_{{ period }}_end
          name: 结束时间
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
      title: 🔋保电模式配置
      entities:
        {% for period in range(1, 7) %}
        - type: section
          label: 时段{{ period }}
        - entity: switch.{{ device_name }}_power_protection_period_{{ period }}_ac_enable
          name: 启用
        - entity: number.{{ device_name }}_power_protection_period_{{ period }}_power
          name: 功率
        - entity: number.{{ device_name }}_power_protection_period_{{ period }}_start_time
          name: 开始时间
        - entity: number.{{ device_name }}_power_protection_period_{{ period }}_soc
          name: SOC
        {% endfor %}
      show_header_toggle: false
      state_color: true
```