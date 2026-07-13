/**
 * Hinen Power Protection Card — custom Lovelace card for power protection mode time period configuration.
 *
 * Supports all 6 periods with: AC enable switch, start time selection, SOC %, and Power (W) inputs,
 * and a bulk save button that calls the `hinen_power.set_power_protection_mode_time_period` service.
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
  type: "hinen-power-protection-card",
  name: "Hinen Power Protection Card",
  description:
    "Power protection mode time-period configuration card (supports PowerProtectionModeTimePeriod bulk save)",
  preview: false,
});

/* ------------------------------------------------------------------ */
/*  i18n helper — resolve labels from hass language                    */
/* ------------------------------------------------------------------ */

const I18N = {
  en: {
    cardTitle: "Power Protection Mode Config",
    period: "Period",
    acEnable: "AC Enable",
    startTime: "Start Time",
    soc: "SOC (%)",
    power: "Power (W)",
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
    errSocRange: "SOC must be between {soc_min} and {soc_max}",
    errPowerRange: "Power must be between {power_min} and {power_max}",
  },
  zh: {
    cardTitle: "保电模式配置",
    period: "时段",
    acEnable: "AC 使能",
    startTime: "开始时间",
    soc: "SOC (%)",
    power: "功率 (W)",
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
    errSocRange: "SOC 必须在 {soc_min} 到 {soc_max} 之间",
    errPowerRange: "功率必须在 {power_min} 到 {power_max} 之间",
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

class HinenPowerProtectionCard extends LitElement {
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

    // Read field specs from sensor attributes (e.g. PeriodSOC: {min:10, max:100})
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

    // The helper sensor exposes power_protection_mode_time_period as a state attribute
    const raw = stateObj.attributes.power_protection_mode_time_period || [];

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
    const required = ["PeriodSOC", "PeriodPower"];
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
      PeriodACEnable: 0,
      PeriodStartTime: 0,
      PeriodSOC: 0,
      PeriodPower: 0,
    };
    // Only keep periods that have actual data (non-empty)
    const result = (periods || [])
      .filter(
        (p) =>
          p &&
          (p.PeriodACEnable === 1 ||
            p.PeriodStartTime > 0 ||
            p.PeriodSOC > 0 ||
            p.PeriodPower !== 0),
      )
      .map((p) => ({ ...empty, ...p }));
    // Ensure at least 1 period
    if (result.length === 0) {
      result.push({ ...empty });
    }
    return result;
  }

  /* -------- mutators -------- */

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
      PeriodACEnable: 0,
      PeriodStartTime: 0,
      PeriodSOC: 0,
      PeriodPower: 0,
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
    minutes = Math.max(0, Math.min(1440, minutes)); // allow 1440 for 24:00
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

      await this._hass.callService(
        "hinen_power",
        "set_power_protection_mode_time_period",
        {
          device_id: this._deviceId,
          periods: this._periods,
        },
      );
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

    // Check each period
    for (let i = 0; i < this._periods.length; i++) {
      const p = this._periods[i];

      // Validate SOC range using device specs
      const socMin = this._spec("PeriodSOC", "min", 0);
      const socMax = this._spec("PeriodSOC", "max", 100);
      if (p.PeriodSOC < socMin || p.PeriodSOC > socMax) {
        throw new Error(
          `${_t.period} ${i + 1}: ${_t.errSocRange.replace("{soc_min}", socMin).replace("{soc_max}", socMax)}`,
        );
      }

      // Validate Power range using device specs
      const powerMin = this._spec("PeriodPower", "min", 0);
      const powerMax = this._spec("PeriodPower", "max", 12000);
      if (p.PeriodPower < powerMin || p.PeriodPower > powerMax) {
        throw new Error(
          `${_t.period} ${i + 1}: ${_t.errPowerRange.replace("{power_min}", powerMin).replace("{power_max}", powerMax)}`,
        );
      }
    }
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
                  <!-- AC enable -->
                  <div class="field">
                    <div class="enable-row">
                      <span class="field-label">${_t.acEnable}</span>
                      <ha-switch
                        .checked=${period.PeriodACEnable === 1}
                        @change=${(e) =>
                          this._updatePeriod(idx, {
                            PeriodACEnable: e.target.checked ? 1 : 0,
                          })}
                      ></ha-switch>
                    </div>
                  </div>

                  <!-- start time -->
                  <div class="time-row">
                    <div class="time-input-wrapper">
                      <label class="time-label">${_t.startTime}</label>
                      <input
                        type="time"
                        class="time-input"
                        min=${this._minutesToTime(
                          this._spec("PeriodStartTime", "min", 0),
                        )}
                        max=${this._minutesToTime(
                          this._spec("PeriodStartTime", "max", 1440),
                        )}
                        .value=${this._minutesToTime(period.PeriodStartTime)}
                        @change=${(e) =>
                          this._updatePeriod(idx, {
                            PeriodStartTime: this._timeToMinutes(
                              e.target.value,
                            ),
                          })}
                      />
                    </div>
                  </div>

                  <!-- SOC / Power -->
                  <div class="field">
                    <div class="number-row">
                      <ha-textfield
                        label="${_t.soc}"
                        type="number"
                        min=${this._spec("PeriodSOC", "min", 0)}
                        max=${this._spec("PeriodSOC", "max", 100)}
                        step=${this._spec("PeriodSOC", "step", 1)}
                        validationMessage="${_t.errSocRange
                          .replace(
                            "{soc_min}",
                            this._spec("PeriodSOC", "min", 0),
                          )
                          .replace(
                            "{soc_max}",
                            this._spec("PeriodSOC", "max", 100),
                          )}"
                        .value=${String(period.PeriodSOC)}
                        @change=${(e) =>
                          this._updatePeriod(idx, {
                            PeriodSOC: parseInt(e.target.value, 10) || 0,
                          })}
                      ></ha-textfield>
                      <ha-textfield
                        label="${_t.power}"
                        type="number"
                        min=${this._spec("PeriodPower", "min", 0)}
                        max=${this._spec("PeriodPower", "max", 12000)}
                        step=${this._spec("PeriodPower", "step", 1)}
                        validationMessage="${_t.errPowerRange
                          .replace(
                            "{power_min}",
                            this._spec("PeriodPower", "min", 0),
                          )
                          .replace(
                            "{power_max}",
                            this._spec("PeriodPower", "max", 12000),
                          )}"
                        .value=${String(period.PeriodPower)}
                        @change=${(e) =>
                          this._updatePeriod(idx, {
                            PeriodPower: parseInt(e.target.value, 10) || 0,
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

customElements.define("hinen-power-protection-card", HinenPowerProtectionCard);
