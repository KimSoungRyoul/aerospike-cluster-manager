import { describe, it, expect, vi } from "vitest";
import {
  formatBytes,
  formatNumber,
  formatUptime,
  formatDuration,
  formatPercent,
  formatTTLAsExpiry,
  truncateMiddle,
} from "../formatters";

describe("formatBytes", () => {
  it("returns '0 B' for zero bytes", () => {
    expect(formatBytes(0)).toBe("0 B");
  });

  it("formats bytes", () => {
    expect(formatBytes(512)).toBe("512 B");
  });

  it("formats kilobytes", () => {
    expect(formatBytes(1024)).toBe("1 KB");
  });

  it("formats megabytes", () => {
    expect(formatBytes(1048576)).toBe("1 MB");
  });

  it("formats gigabytes", () => {
    expect(formatBytes(1073741824)).toBe("1 GB");
  });

  it("formats terabytes", () => {
    expect(formatBytes(1099511627776)).toBe("1 TB");
  });

  it("respects decimals parameter", () => {
    expect(formatBytes(1536, 1)).toBe("1.5 KB");
  });
});

describe("formatNumber", () => {
  it("returns number as string for small numbers", () => {
    expect(formatNumber(42)).toBe("42");
    expect(formatNumber(999)).toBe("999");
  });

  it("formats thousands with K suffix", () => {
    expect(formatNumber(1000)).toBe("1.0K");
    expect(formatNumber(1500)).toBe("1.5K");
  });

  it("formats millions with M suffix", () => {
    expect(formatNumber(1000000)).toBe("1.0M");
    expect(formatNumber(2500000)).toBe("2.5M");
  });
});

describe("formatUptime", () => {
  it("formats minutes only", () => {
    expect(formatUptime(120)).toBe("2m");
    expect(formatUptime(0)).toBe("0m");
  });

  it("formats hours and minutes", () => {
    expect(formatUptime(3660)).toBe("1h 1m");
  });

  it("formats days and hours", () => {
    expect(formatUptime(90000)).toBe("1d 1h");
  });
});

describe("formatDuration", () => {
  it("formats microseconds", () => {
    expect(formatDuration(0.5)).toBe("500µs");
  });

  it("formats milliseconds", () => {
    expect(formatDuration(42.3)).toBe("42.3ms");
  });

  it("formats seconds", () => {
    expect(formatDuration(1500)).toBe("1.50s");
  });
});

describe("formatPercent", () => {
  it("returns 0 for zero total", () => {
    expect(formatPercent(50, 0)).toBe(0);
  });

  it("calculates percentage correctly", () => {
    expect(formatPercent(50, 100)).toBe(50);
    expect(formatPercent(1, 3)).toBe(33);
  });
});

describe("formatTTLAsExpiry", () => {
  it("returns 'Never' for -1", () => {
    expect(formatTTLAsExpiry(-1)).toBe("Never");
  });

  it("returns 'Never' for 4294967295 (UINT32_MAX)", () => {
    expect(formatTTLAsExpiry(4294967295)).toBe("Never");
  });

  it("returns 'Default' for 0", () => {
    expect(formatTTLAsExpiry(0)).toBe("Default");
  });

  it("returns yyyy-mm-dd hh:mm format (no seconds) by default", () => {
    const result = formatTTLAsExpiry(3600);
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
  });

  it("returns yyyy-mm-dd hh:mm:ss when includeSeconds=true", () => {
    const result = formatTTLAsExpiry(3600, true);
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
  });

  it("calculates correct expiry date (short form)", () => {
    vi.setSystemTime(new Date("2026-03-01T12:00:00"));
    expect(formatTTLAsExpiry(86400)).toBe("2026-03-02 12:00");
    vi.useRealTimers();
  });

  it("calculates correct expiry date (long form)", () => {
    vi.setSystemTime(new Date("2026-03-01T12:00:00"));
    expect(formatTTLAsExpiry(86400, true)).toBe("2026-03-02 12:00:00");
    vi.useRealTimers();
  });
});

describe("truncateMiddle", () => {
  it("returns short strings unchanged", () => {
    expect(truncateMiddle("hello", 10)).toBe("hello");
  });

  it("truncates long strings with ellipsis in the middle", () => {
    const result = truncateMiddle("abcdefghijklmnopqrstuvwxyz", 10);
    expect(result).toContain("...");
    expect(result.length).toBeLessThanOrEqual(10);
  });

  it("handles exact length", () => {
    expect(truncateMiddle("12345", 5)).toBe("12345");
  });
});
