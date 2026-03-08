import { describe, it, expect } from "vitest";
import { ApiError, isApiError } from "../errors";

describe("ApiError", () => {
  it("creates an error with message, status, and name", () => {
    const error = new ApiError("Not found", 404);

    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe("Not found");
    expect(error.status).toBe(404);
    expect(error.name).toBe("ApiError");
    expect(error.code).toBeUndefined();
  });

  it("stores an optional error code", () => {
    const error = new ApiError("Validation failed", 422, "VALIDATION_ERROR");

    expect(error.code).toBe("VALIDATION_ERROR");
    expect(error.status).toBe(422);
  });

  it("has a proper stack trace", () => {
    const error = new ApiError("Server error", 500);
    expect(error.stack).toBeDefined();
  });
});

describe("isApiError", () => {
  it("returns true for ApiError instances", () => {
    const error = new ApiError("fail", 500);
    expect(isApiError(error)).toBe(true);
  });

  it("returns false for regular Error instances", () => {
    const error = new Error("fail");
    expect(isApiError(error)).toBe(false);
  });

  it("returns false for plain objects", () => {
    expect(isApiError({ message: "fail", status: 500, name: "ApiError" })).toBe(false);
  });

  it("returns false for null and undefined", () => {
    expect(isApiError(null)).toBe(false);
    expect(isApiError(undefined)).toBe(false);
  });

  it("returns false for strings", () => {
    expect(isApiError("error")).toBe(false);
  });
});
