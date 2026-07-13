/**
 * Hinen Period Card — custom Lovelace card for charge/discharge time-period configuration.
 *
 * Supports all 20 periods with: enable switch, weekday toggles (Mon–Sun),
 * start/end time selection, power-rate % and stop-SOC % inputs, and a bulk
 * save button that calls the `hinen_power.set_period_times2` service.
 */

import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@3.3.3/lit-element.js?module";

/* ------------------------------------------------------------------ */
/*  Card registration                                                  */
/* ------------------------------------------------------------------ */

window.customCards = window.customCards || [];
window.customCards.push({
  type: "hinen-period-card",
  name: "Hinen Period Card",
  description:
    "Charge/discharge time-period configuration card (supports CDPeriodTimes2 bulk save)",
  preview: false,
});

/* ------------------------------------------------------------------ */
/*  i18n helper — resolve labels from hass language                    */
/* ------------------------------------------------------------------ */

const I18N = {
  en: {
    cardTitle: "Charge/Discharge Period Config",
    period: "Period",
    enable: "Enable",
    weekEnable: "Week Enable",
    weekDays: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    startTime: "Start Time",
    endTime: "End Time",
    to: "to",
    params: "Parameters",
    rate: "Power Rate (%)",
    stopSoc: "Stop SOC (%)",
    saving: "Saving…",
    save: "Save to Device",
    saveOk: "✓ Saved",
    saveFail: "✗ Save failed: ",
    loading: "Loading…",
    noEntity: "Entity not found: ",
    noDeviceId: "Cannot resolve device ID",
    specsUnavailable:
      "Device specs missing for: {fields}. Please restart HA or check device connection.",
    addPeriod: "Add Period",
    delete: "Delete",
    errStartBeforeEnd: "start time must be before end time",
    errOverlap: "overlap with period {other} on {weekday}",
    errRateRange: "must be between {rate_min} and {rate_max}",
    errSocRange: "must be between {soc_min} and {soc_max}",
  },
  zh: {
    cardTitle: "充放电时段配置",
    period: "时段",
    enable: "启用",
    weekEnable: "星期启用",
    weekDays: ["一", "二", "三", "四", "五", "六", "日"],
    startTime: "开始时间",
    endTime: "结束时间",
    to: "至",
    params: "参数",
    rate: "功率百分比 (%)",
    stopSoc: "截止 SOC (%)",
    saving: "保存中…",
    save: "保存到设备",
    saveOk: "✓ 保存成功",
    saveFail: "✗ 保存失败：",
    loading: "加载中…",
    noEntity: "找不到实体：",
    noDeviceId: "无法获取设备 ID",
    specsUnavailable: "设备缺少规格信息：{fields}。请重启 HA 或检查设备连接。",
    addPeriod: "添加时段",
    delete: "删除",
    errStartBeforeEnd: "开始时间必须在结束时间之前",
    errOverlap: "与时段{other}在周{weekday}重叠",
    errRateRange: "必须在 {rate_min} 到 {rate_max} 之间",
    errSocRange: "必须在 {soc_min} 到 {soc_max} 之间",
  },
};

function t(hass) {
  const lang = (hass && hass.language) || "en";
  if (lang.startsWith("zh")) return I18N.zh;
  return I18N.en;
}

/* ------------------------------------------------------------------ */
/*  Card class                                                         */
/* ------------------------------------------------------------------ */

class HinenPeriodCard extends LitElement {
  /* -------- reactive properties -------- */

  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
      _periods: { state: true },
      _saving: { state: true },
      _status: { state: true },
      _error: { state: true },
      _deviceId: { state: true },
      _weekSupport: { state: true },
      _fieldSpecs: { state: true },
    };
  }

  /* -------- constructor -------- */

  constructor() {
    super();
    this.hass = null;
    this.config = null;
    this._periods = null;
    this._saving = false;
    this._status = "";
    this._error = "";
    this._deviceId = "";
    this._weekSupport = true;
  }

  /* -------- lovelace config -------- */

  setConfig(config) {
    if (!config.entity) {
      throw new Error(
        'Missing required "entity" field (must point to the helper sensor)',
      );
    }

    this.config = config;
  }

  getCardSize() {
    return 4;
  }

  /* -------- hass setter (reactive bridge) -------- */

  set hass(hass) {
    this._hass = hass;

    if (!this.config) return;

    const entityId = this.config.entity;
    const stateObj = hass.states[entityId];

    if (!stateObj) {
      this._error = `${t(hass).noEntity}${entityId}`;
      this._periods = null;
      return;
    }

    // Get API device ID from sensor attributes (not HA device registry)
    const deviceId = stateObj.attributes.api_device_id;
    if (!deviceId) {
      this._error = hass.language?.startsWith?.("zh")
        ? t(hass).noDeviceId
        : t(hass).noDeviceId;
      this._periods = null;
      return;
    }

    this._error = this._deviceId !== deviceId ? "" : this._error;
    this._deviceId = deviceId;

    // Check if device supports week configuration
    this._weekSupport = !!stateObj.attributes.cd_period_week_support;

    // Read field specs from sensor attributes (e.g. periodTimeRate: {min:-100, max:100})
    this._fieldSpecs = stateObj.attributes.field_specs || {};

    // Check if required specs are available
    const missingSpecs = this._getMissingSpecs();
    if (missingSpecs.length > 0) {
      const _t = t(hass);
      this._error = _t.specsUnavailable.replace(
        "{fields}",
        missingSpecs.join(", "),
      );
      this._periods = null;
      return;
    }

    // The helper sensor exposes cd_period_times2 as a state attribute
    const raw = stateObj.attributes.cd_period_times2 || [];

    // Only update if API data is actually different from local state
    const newData = this._normalizePeriods(raw);
    if (!this._isSamePeriods(this._periods, newData)) {
      this._periods = newData;
    }
  }

  _isSamePeriods(a, b) {
    if (!a || !b) return false;
    if (a.length !== b.length) return false;
    return JSON.stringify(a) === JSON.stringify(b);
  }

  /** Check which required field specs are missing min/max. Returns array of field names. */
  _getMissingSpecs() {
    const required = ["periodTimeRate", "periodTimeStopSoc"];
    return required.filter((field) => {
      const spec = this._fieldSpecs[field] || {};
      return spec.min == null || spec.max == null;
    });
  }

  /** Read a spec value for a given field, with fallback. */
  _spec(field, key, fallback) {
    return this._fieldSpecs[field]?.[key] ?? fallback;
  }

  /* -------- private helpers -------- */

  /** Normalise the raw periods array - keep actual data only, ensure at least 1. */
  _normalizePeriods(periods) {
    const empty = {
      periodEnable: 0,
      PeriodWeekEnable: "0,0,0,0,0,0,0",
      periodTimeStart: 0,
      periodTimeEnd: 0,
      periodTimeRate: 0,
      periodTimeStopSoc: 0,
    };
    // Only keep periods that have actual data (non-empty)
    const result = (periods || [])
      .filter(
        (p) =>
          p &&
          (p.periodEnable === 1 ||
            p.periodTimeStart > 0 ||
            p.periodTimeEnd > 0),
      )
      .map((p) => ({ ...empty, ...p }));
    // Ensure at least 1 period
    if (result.length === 0) {
      result.push({ ...empty });
    }
    return result;
  }

  /* -------- mutators -------- */

  _toggleWeek(periodIndex, dayIdx) {
    const period = this._periods[periodIndex];
    const arr = period.PeriodWeekEnable.split(",").map(Number);
    arr[dayIdx] = arr[dayIdx] ? 0 : 1;
    this._updatePeriod(periodIndex, { PeriodWeekEnable: arr.join(",") });
  }

  _updatePeriod(index, patch) {
    this._periods = [
      ...this._periods.slice(0, index),
      { ...this._periods[index], ...patch },
      ...this._periods.slice(index + 1),
    ];
  }

  _addPeriod() {
    if (this._periods.length >= 20) {
      return;
    }
    const empty = {
      periodEnable: 0,
      PeriodWeekEnable: "0,0,0,0,0,0,0",
      periodTimeStart: 0,
      periodTimeEnd: 0,
      periodTimeRate: 0,
      periodTimeStopSoc: 0,
    };
    this._periods = [...this._periods, { ...empty }];
  }

  _deletePeriod(index) {
    if (this._periods.length <= 1) {
      return;
    }
    this._periods = [
      ...this._periods.slice(0, index),
      ...this._periods.slice(index + 1),
    ];
  }

  _minutesToTime(minutes) {
    if (typeof minutes !== "number" || Number.isNaN(minutes)) minutes = 0;
    minutes = Math.max(0, Math.min(1439, minutes));
    const h = String(Math.floor(minutes / 60)).padStart(2, "0");
    const m = String(minutes % 60).padStart(2, "0");
    return `${h}:${m}`;
  }

  _timeToMinutes(timeStr) {
    if (!timeStr || !/^\d{1,2}:\d{2}(:\d{2})?$/.test(timeStr)) return 0;
    const parts = timeStr.split(":").map(Number);
    return parts[0] * 60 + (parts[1] || 0);
  }

  async _save() {
    this._saving = true;
    this._status = "";
    this.requestUpdate();

    try {
      // Frontend validation before sending to service
      this._validatePeriods();

      await this._hass.callService("hinen_power", "set_period_times2", {
        device_id: this._deviceId,
        periods: this._periods,
      });
      const _t = t(this._hass);
      this._status = _t.saveOk;
    } catch (err) {
      const _t = t(this._hass);
      this._status = _t.saveFail + (err.message || err);
    } finally {
      this._saving = false;
      this.requestUpdate();
      // Clear status message after 3 s
      setTimeout(() => {
        this._status = "";
        this.requestUpdate();
      }, 3000);
    }
  }

  _validatePeriods() {
    const _t = t(this._hass);

    // Check each enabled period
    for (let i = 0; i < this._periods.length; i++) {
      const p = this._periods[i];
      if (!p.periodEnable) continue;

      // Rate range check using specs
      const rateMin = this._spec("periodTimeRate", "min", -100);
      const rateMax = this._spec("periodTimeRate", "max", 100);
      if (p.periodTimeRate < rateMin || p.periodTimeRate > rateMax) {
        throw new Error(
          `${_t.period} ${i + 1}: Rate ${p.periodTimeRate} ${_t.errRateRange.replace("{rate_min}", rateMin).replace("{rate_max}", rateMax)}`,
        );
      }

      // Stop SOC range check using specs
      const socMin = this._spec("periodTimeStopSoc", "min", 0);
      const socMax = this._spec("periodTimeStopSoc", "max", 100);
      if (p.periodTimeStopSoc < socMin || p.periodTimeStopSoc > socMax) {
        throw new Error(
          `${_t.period} ${i + 1}: Stop SOC ${p.periodTimeStopSoc} ${_t.errSocRange.replace("{soc_min}", socMin).replace("{soc_max}", socMax)}`,
        );
      }

      // Start time must be before end time
      if (p.periodTimeStart >= p.periodTimeEnd) {
        throw new Error(`${_t.period} ${i + 1}: ${_t.errStartBeforeEnd}`);
      }

      // Check overlap with other enabled periods
      for (let j = i + 1; j < this._periods.length; j++) {
        const other = this._periods[j];
        if (!other.periodEnable) continue;

        if (this._weekSupport) {
          // Device supports week configuration, check weekday overlap
          const week1 = p.PeriodWeekEnable.split(",").map(Number);
          const week2 = other.PeriodWeekEnable.split(",").map(Number);

          // Check if any common weekday
          for (let dayIdx = 0; dayIdx < Math.min(week1.length, 7); dayIdx++) {
            if (week1[dayIdx] === 1 && week2[dayIdx] === 1) {
              // Common weekday found, check time overlap
              if (
                this._periodsHaveOverlap(
                  p.periodTimeStart,
                  p.periodTimeEnd,
                  other.periodTimeStart,
                  other.periodTimeEnd,
                )
              ) {
                const errMsg = _t.errOverlap
                  .replace("{other}", String(j + 1))
                  .replace("{weekday}", _t.weekDays[dayIdx]);
                throw new Error(`${_t.period} ${i + 1} ${errMsg}`);
              }
            }
          }
        } else {
          // Device doesn't support week configuration, all periods are always enabled
          // Just check time overlap
          if (
            this._periodsHaveOverlap(
              p.periodTimeStart,
              p.periodTimeEnd,
              other.periodTimeStart,
              other.periodTimeEnd,
            )
          ) {
            const errMsg = _t.errOverlap
              .replace("{other}", String(j + 1))
              .replace("{weekday}", _t.weekDays[0]);
            throw new Error(`${_t.period} ${i + 1} ${errMsg}`);
          }
        }
      }
    }
  }

  _periodsHaveOverlap(start1, end1, start2, end2) {
    // Handle periods that cross midnight
    if (start1 > end1) end1 += 1440;
    if (start2 > end2) end2 += 1440;
    return start1 < end2 && start2 < end1;
  }

  _validatePeriodRealtime(periodIdx) {
    const _t = t(this._hass);
    const p = this._periods[periodIdx];

    // Only check enabled periods
    if (p.periodEnable === 0) {
      return "";
    }

    // Start time must be before end time
    if (p.periodTimeStart >= p.periodTimeEnd && p.periodTimeEnd > 0) {
      return _t.errStartBeforeEnd;
    }

    // Check overlap with other enabled periods
    for (let j = 0; j < this._periods.length; j++) {
      if (j === periodIdx) continue;
      const other = this._periods[j];
      if (other.periodEnable === 0) continue;

      if (this._weekSupport) {
        // Device supports week configuration, check weekday overlap
        const week1 = p.PeriodWeekEnable.split(",").map(Number);
        const week2 = other.PeriodWeekEnable.split(",").map(Number);

        for (let dayIdx = 0; dayIdx < Math.min(week1.length, 7); dayIdx++) {
          if (week1[dayIdx] === 1 && week2[dayIdx] === 1) {
            // Common weekday found, check time overlap
            if (
              this._periodsHaveOverlap(
                p.periodTimeStart,
                p.periodTimeEnd,
                other.periodTimeStart,
                other.periodTimeEnd,
              )
            ) {
              const errMsg = _t.errOverlap
                .replace("{other}", String(j + 1))
                .replace("{weekday}", _t.weekDays[dayIdx]);
              return errMsg;
            }
          }
        }
      } else {
        // No week support, just check time overlap
        if (
          this._periodsHaveOverlap(
            p.periodTimeStart,
            p.periodTimeEnd,
            other.periodTimeStart,
            other.periodTimeEnd,
          )
        ) {
          const errMsg = _t.errOverlap
            .replace("{other}", String(j + 1))
            .replace("{weekday}", _t.weekDays[0]);
          return errMsg;
        }
      }
    }

    return "";
  }

  /* -------- styles -------- */

  static get styles() {
    return css`
      :host {
        display: block;
      }

      ha-card {
        overflow: hidden;
      }

      /* ---- card header ---- */

      .card-header {
        padding: 16px 16px 8px;
        font-size: 18px;
        font-weight: 500;
        color: var(--primary-text-color, #212121);
      }

      /* ---- period card ---- */

      .period-card {
        background: var(--secondary-background-color, #f5f5f5);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
      }

      .period-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }

      .period-title {
        font-size: 14px;
        font-weight: 500;
        color: var(--primary-text-color, #212121);
      }

      .delete-btn {
        width: 24px;
        height: 24px;
        border: none;
        border-radius: 50%;
        background: var(--error-color, #f44336);
        color: #fff;
        font-size: 20px;
        font-weight: bold;
        line-height: 1;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .delete-btn:hover {
        background: var(--error-color-dark, #d32f2f);
      }

      .period-content {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      /* ---- add period button ---- */

      .add-period-btn {
        width: 100%;
        padding: 12px;
        border: 2px dashed var(--divider-color, #e0e0e0);
        border-radius: 8px;
        background: transparent;
        color: var(--primary-color, #03a9f4);
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        margin-top: 8px;
      }
      .add-period-btn:hover {
        background: var(--primary-color-light, rgba(3, 169, 244, 0.08));
        border-color: var(--primary-color, #03a9f4);
      }

      /* ---- content ---- */

      .card-content {
        padding: 4px 16px 8px;
        display: flex;
        flex-direction: column;
        gap: 18px;
      }

      .field {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .field-label {
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--secondary-text-color, #727272);
      }

      /* ---- enable row ---- */

      .enable-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
      }

      /* ---- weekdays ---- */

      .week-days {
        display: flex;
        gap: 6px;
        justify-content: center;
      }
      .wd {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: 1.5px solid var(--divider-color, #e0e0e0);
        background: transparent;
        color: var(--secondary-text-color, #727272);
        font-size: 13px;
        font-weight: 500;
        font-family: var(--ha-font-family-body, Roboto, sans-serif);
        cursor: pointer;
        transition: all 0.18s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        user-select: none;
        -webkit-tap-highlight-color: transparent;
      }
      .wd:hover {
        border-color: var(--primary-color, #03a9f4);
        color: var(--primary-color, #03a9f4);
      }
      .wd.on {
        background: var(--primary-color, #03a9f4);
        border-color: var(--primary-color, #03a9f4);
        color: var(--text-primary-color, #fff);
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.16);
      }

      /* ---- time row ---- */

      .time-row {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
      }
      .time-input-wrapper {
        display: flex;
        flex-direction: column;
        flex: 1;
        min-width: 100px;
      }
      .time-label {
        font-size: 12px;
        color: var(--secondary-text-color, #727272);
        margin-bottom: 4px;
      }
      .time-input {
        padding: 8px;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 4px;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color, #212121);
        font-size: 14px;
      }
      .time-input:focus {
        outline: none;
        border-color: var(--primary-color, #03a9f4);
      }
      .time-divider {
        color: var(--secondary-text-color, #727272);
        font-size: 13px;
        flex-shrink: 0;
        align-self: flex-end;
        padding-bottom: 8px;
      }

      /* ---- number row ---- */

      .number-row {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
      }
      .number-row ha-textfield {
        flex: 1;
        min-width: 120px;
      }

      /* ---- card-actions ---- */

      .card-actions {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
      }
      .card-actions mwc-button {
        --mdc-theme-primary: var(--primary-color, #03a9f4);
      }

      .status {
        font-size: 13px;
        line-height: 1;
      }
      .status.ok {
        color: var(--success-color, #4caf50);
      }
      .status.err {
        color: var(--error-color, #f44336);
      }

      /* ---- misc ---- */

      .error,
      .loading {
        padding: 24px 16px;
        text-align: center;
        font-size: 14px;
      }
      .error {
        color: var(--error-color, #f44336);
      }
      .loading {
        color: var(--secondary-text-color, #727272);
      }

      /* ---- field error ---- */

      .field-error {
        color: var(--error-color, #f44336);
        font-size: 12px;
        margin-top: 8px;
        padding: 4px 8px;
        background: rgba(244, 67, 54, 0.1);
        border-radius: 4px;
      }
    `;
  }

  /* -------- render -------- */

  render() {
    const _t = t(this._hass);

    if (this._error) {
      return html`<ha-card>
        <div class="error">${this._error}</div>
      </ha-card>`;
    }

    if (!this._periods) {
      return html`<ha-card>
        <div class="loading">${_t.loading}</div>
      </ha-card>`;
    }

    const statusOk = this._status.startsWith("✓");
    const canAdd = this._periods.length < 20;
    const canDelete = this._periods.length > 1;

    return html`
      <ha-card>
        <div class="card-header">
          <span>${_t.cardTitle}</span>
        </div>
        <div class="card-content">
          ${this._periods.map(
            (period, idx) => html`
              <div class="period-card">
                <div class="period-header">
                  <span class="period-title">${_t.period} ${idx + 1}</span>
                  ${canDelete
                    ? html`<button
                        class="delete-btn"
                        @click=${() => this._deletePeriod(idx)}
                        title="${_t.delete}"
                      >
                        ×
                      </button>`
                    : ""}
                </div>
                <div class="period-content">
                  <!-- enable -->
                  <div class="field">
                    <div class="enable-row">
                      <span class="field-label">${_t.enable}</span>
                      <ha-switch
                        .checked=${period.periodEnable === 1}
                        @change=${(e) =>
                          this._updatePeriod(idx, {
                            periodEnable: e.target.checked ? 1 : 0,
                          })}
                      ></ha-switch>
                    </div>
                  </div>

                  <!-- weekdays -->
                  ${this._weekSupport
                    ? html`
                        <div class="field">
                          <span class="field-label">${_t.weekEnable}</span>
                          <div class="week-days">
                            ${_t.weekDays.map(
                              (label, i) => html`
                                <button
                                  class="wd ${period.PeriodWeekEnable.split(
                                    ",",
                                  )[i] === "1"
                                    ? "on"
                                    : ""}"
                                  @click=${() => this._toggleWeek(idx, i)}
                                >
                                  ${label}
                                </button>
                              `,
                            )}
                          </div>
                        </div>
                      `
                    : ""}

                  <!-- time range -->
                  <div class="time-row">
                    <div class="time-input-wrapper">
                      <label class="time-label">${_t.startTime}</label>
                      <input
                        type="time"
                        class="time-input"
                        .value=${this._minutesToTime(period.periodTimeStart)}
                        @change=${(e) =>
                          this._updatePeriod(idx, {
                            periodTimeStart: this._timeToMinutes(
                              e.target.value,
                            ),
                          })}
                      />
                    </div>
                    <span class="time-divider">${_t.to}</span>
                    <div class="time-input-wrapper">
                      <label class="time-label">${_t.endTime}</label>
                      <input
                        type="time"
                        class="time-input"
                        .value=${this._minutesToTime(period.periodTimeEnd)}
                        @change=${(e) =>
                          this._updatePeriod(idx, {
                            periodTimeEnd: this._timeToMinutes(e.target.value),
                          })}
                      />
                    </div>
                  </div>
                  ${period.periodEnable === 1
                    ? html`
                        ${(() => {
                          const overlapErr = this._validatePeriodRealtime(idx);
                          return overlapErr
                            ? html`<div class="field-error">
                                ${_t.period} ${idx + 1}: ${overlapErr}
                              </div>`
                            : "";
                        })()}
                      `
                    : ""}

                  <!-- rate / SOC -->
                  <div class="field">
                    <span class="field-label">${_t.params}</span>
                    <div class="number-row">
                      <ha-textfield
                        label="${_t.rate}"
                        type="number"
                        min=${this._spec("periodTimeRate", "min", -100)}
                        max=${this._spec("periodTimeRate", "max", 100)}
                        step=${this._spec("periodTimeRate", "step", 1)}
                        validationMessage="${_t.errRateRange
                          .replace(
                            "{rate_min}",
                            this._spec("periodTimeRate", "min", -100),
                          )
                          .replace(
                            "{rate_max}",
                            this._spec("periodTimeRate", "max", 100),
                          )}"
                        .value=${String(period.periodTimeRate)}
                        @change=${(e) =>
                          this._updatePeriod(idx, {
                            periodTimeRate: parseInt(e.target.value, 10) || 0,
                          })}
                      ></ha-textfield>
                      <ha-textfield
                        label="${_t.stopSoc}"
                        type="number"
                        min=${this._spec("periodTimeStopSoc", "min", 0)}
                        max=${this._spec("periodTimeStopSoc", "max", 100)}
                        step=${this._spec("periodTimeStopSoc", "step", 1)}
                        validationMessage="${_t.errSocRange
                          .replace(
                            "{soc_min}",
                            this._spec("periodTimeStopSoc", "min", 0),
                          )
                          .replace(
                            "{soc_max}",
                            this._spec("periodTimeStopSoc", "max", 100),
                          )}"
                        .value=${String(period.periodTimeStopSoc)}
                        @change=${(e) =>
                          this._updatePeriod(idx, {
                            periodTimeStopSoc:
                              parseInt(e.target.value, 10) || 0,
                          })}
                      ></ha-textfield>
                    </div>
                  </div>
                </div>
              </div>
            `,
          )}

          <!-- add period button -->
          ${canAdd
            ? html`<button
                class="add-period-btn"
                @click=${() => this._addPeriod()}
              >
                + ${_t.addPeriod}
              </button>`
            : ""}
        </div>

        <!-- save bar -->
        <div class="card-actions">
          <mwc-button raised .disabled=${this._saving} @click=${this._save}>
            ${this._saving ? _t.saving : _t.save}
          </mwc-button>
          ${this._status
            ? html`<span class="status ${statusOk ? "ok" : "err"}"
                >${this._status}</span
              >`
            : ""}
        </div>
      </ha-card>
    `;
  }
}

/* ------------------------------------------------------------------ */
/*  Register custom element                                            */
/* ------------------------------------------------------------------ */

customElements.define("hinen-period-card", HinenPeriodCard);
