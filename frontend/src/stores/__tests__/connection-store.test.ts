import { describe, it, expect, vi, beforeEach } from "vitest";
import { useConnectionStore } from "../connection-store";

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  api: {
    getConnections: vi.fn(),
    getConnectionHealth: vi.fn(),
    createConnection: vi.fn(),
    updateConnection: vi.fn(),
    deleteConnection: vi.fn(),
    testConnection: vi.fn(),
  },
}));

import { api } from "@/lib/api/client";
const mockApi = vi.mocked(api);

describe("useConnectionStore", () => {
  beforeEach(() => {
    useConnectionStore.setState({
      connections: [],
      healthStatuses: {},
      checkingHealth: {},
      selectedConnectionId: null,
      loading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it("has correct initial state", () => {
    const state = useConnectionStore.getState();
    expect(state.connections).toEqual([]);
    expect(state.healthStatuses).toEqual({});
    expect(state.checkingHealth).toEqual({});
    expect(state.selectedConnectionId).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("selectConnection sets selectedConnectionId", () => {
    useConnectionStore.getState().selectConnection("conn-1");
    expect(useConnectionStore.getState().selectedConnectionId).toBe("conn-1");
  });

  it("selectConnection sets null", () => {
    useConnectionStore.getState().selectConnection("conn-1");
    useConnectionStore.getState().selectConnection(null);
    expect(useConnectionStore.getState().selectedConnectionId).toBeNull();
  });

  it("fetchConnections sets loading and populates connections", async () => {
    const mockConnections = [
      {
        id: "1",
        name: "Test",
        hosts: ["localhost"],
        port: 3000,
        color: "#000",
        createdAt: "2025-01-01",
        updatedAt: "2025-01-01",
      },
    ];
    mockApi.getConnections.mockResolvedValue(mockConnections as any);

    await useConnectionStore.getState().fetchConnections();

    const state = useConnectionStore.getState();
    expect(state.connections).toEqual(mockConnections);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("fetchConnections sets error on failure", async () => {
    mockApi.getConnections.mockRejectedValue(new Error("Network error"));

    await useConnectionStore.getState().fetchConnections();

    const state = useConnectionStore.getState();
    expect(state.error).toBe("Network error");
    expect(state.loading).toBe(false);
  });

  it("fetchConnectionHealth updates healthStatuses on success", async () => {
    const mockStatus = { connected: true, nodeCount: 1, namespaceCount: 2 };
    mockApi.getConnectionHealth.mockResolvedValue(mockStatus as any);

    await useConnectionStore.getState().fetchConnectionHealth("conn-1");

    const state = useConnectionStore.getState();
    expect(state.healthStatuses["conn-1"]).toEqual(mockStatus);
    expect(state.checkingHealth["conn-1"]).toBe(false);
  });

  it("fetchConnectionHealth sets disconnected on failure", async () => {
    mockApi.getConnectionHealth.mockRejectedValue(new Error("Timeout"));

    await useConnectionStore.getState().fetchConnectionHealth("conn-1");

    const state = useConnectionStore.getState();
    expect(state.healthStatuses["conn-1"]).toEqual({
      connected: false,
      nodeCount: 0,
      namespaceCount: 0,
      error: "Timeout",
      errorType: undefined,
    });
    expect(state.checkingHealth["conn-1"]).toBe(false);
  });

  it("fetchAllHealth checks health for all connections", () => {
    useConnectionStore.setState({
      connections: [
        {
          id: "conn-1",
          name: "A",
          hosts: ["localhost"],
          port: 3000,
          color: "#000",
          createdAt: "",
          updatedAt: "",
        },
        {
          id: "conn-2",
          name: "B",
          hosts: ["localhost"],
          port: 3000,
          color: "#000",
          createdAt: "",
          updatedAt: "",
        },
      ] as any,
    });
    mockApi.getConnectionHealth.mockResolvedValue({
      connected: true,
      nodeCount: 1,
      namespaceCount: 1,
    } as any);

    useConnectionStore.getState().fetchAllHealth();

    expect(mockApi.getConnectionHealth).toHaveBeenCalledWith("conn-1");
    expect(mockApi.getConnectionHealth).toHaveBeenCalledWith("conn-2");
  });

  it("createConnection calls API and refreshes list", async () => {
    mockApi.createConnection.mockResolvedValue({} as any);
    mockApi.getConnections.mockResolvedValue([]);

    await useConnectionStore.getState().createConnection({ name: "New" });

    expect(mockApi.createConnection).toHaveBeenCalledWith({ name: "New" });
    expect(mockApi.getConnections).toHaveBeenCalled();
  });

  it("deleteConnection clears selectedConnectionId if matching", async () => {
    useConnectionStore.setState({ selectedConnectionId: "conn-1" });
    mockApi.deleteConnection.mockResolvedValue(undefined as any);
    mockApi.getConnections.mockResolvedValue([]);

    await useConnectionStore.getState().deleteConnection("conn-1");

    expect(useConnectionStore.getState().selectedConnectionId).toBeNull();
  });

  it("testConnection returns result on success", async () => {
    mockApi.testConnection.mockResolvedValue({ success: true, message: "OK" });

    const testData = { hosts: ["localhost"], port: 3000 };
    const result = await useConnectionStore.getState().testConnection(testData);

    expect(result).toEqual({ success: true, message: "OK" });
    expect(mockApi.testConnection).toHaveBeenCalledWith(testData);
  });

  it("testConnection returns error result on failure", async () => {
    mockApi.testConnection.mockRejectedValue(new Error("Connection refused"));

    const testData = { hosts: ["localhost"], port: 3000 };
    const result = await useConnectionStore.getState().testConnection(testData);

    expect(result).toEqual({ success: false, message: "Connection refused" });
  });
});
