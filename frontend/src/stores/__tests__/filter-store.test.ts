import { describe, it, expect, beforeEach } from "vitest";
import { useFilterStore } from "../filter-store";

describe("useFilterStore", () => {
  beforeEach(() => {
    useFilterStore.getState().reset();
  });

  it("has correct initial state", () => {
    const state = useFilterStore.getState();
    expect(state.conditions).toEqual([]);
    expect(state.logic).toBe("and");
    expect(state.primaryKey).toBe("");
  });

  describe("addCondition", () => {
    it("adds a condition with the correct bin and default operator", () => {
      const condition = useFilterStore.getState().addCondition("age", "integer");

      expect(condition.bin).toBe("age");
      expect(condition.binType).toBe("integer");
      expect(condition.operator).toBe("eq");
      expect(condition.id).toBeDefined();

      const state = useFilterStore.getState();
      expect(state.conditions).toHaveLength(1);
      expect(state.conditions[0]).toEqual(condition);
    });

    it("adds multiple conditions", () => {
      useFilterStore.getState().addCondition("age", "integer");
      useFilterStore.getState().addCondition("name", "string");

      expect(useFilterStore.getState().conditions).toHaveLength(2);
    });

    it("uses the first operator for the given bin type", () => {
      const floatCondition = useFilterStore.getState().addCondition("score", "float");
      expect(floatCondition.operator).toBe("eq");

      useFilterStore.getState().reset();
      const strCondition = useFilterStore.getState().addCondition("name", "string");
      expect(strCondition.operator).toBe("eq");
    });
  });

  describe("updateCondition", () => {
    it("updates a condition by id", () => {
      const condition = useFilterStore.getState().addCondition("age", "integer");

      useFilterStore.getState().updateCondition(condition.id, { operator: "gt", value: 18 });

      const updated = useFilterStore.getState().conditions[0];
      expect(updated.operator).toBe("gt");
      expect(updated.value).toBe(18);
      expect(updated.bin).toBe("age");
    });

    it("does not affect other conditions", () => {
      const c1 = useFilterStore.getState().addCondition("age", "integer");
      const c2 = useFilterStore.getState().addCondition("name", "string");

      useFilterStore.getState().updateCondition(c1.id, { value: 25 });

      const state = useFilterStore.getState();
      expect(state.conditions[0].value).toBe(25);
      expect(state.conditions[1].id).toBe(c2.id);
      expect(state.conditions[1].value).toBeUndefined();
    });
  });

  describe("removeCondition", () => {
    it("removes a condition by id", () => {
      const c1 = useFilterStore.getState().addCondition("age", "integer");
      useFilterStore.getState().addCondition("name", "string");

      useFilterStore.getState().removeCondition(c1.id);

      const state = useFilterStore.getState();
      expect(state.conditions).toHaveLength(1);
      expect(state.conditions[0].bin).toBe("name");
    });
  });

  describe("clearAll", () => {
    it("clears conditions and primary key", () => {
      useFilterStore.getState().addCondition("age", "integer");
      useFilterStore.getState().setPrimaryKey("pk-123");

      useFilterStore.getState().clearAll();

      const state = useFilterStore.getState();
      expect(state.conditions).toEqual([]);
      expect(state.primaryKey).toBe("");
    });
  });

  describe("setLogic", () => {
    it("switches logic to or", () => {
      useFilterStore.getState().setLogic("or");
      expect(useFilterStore.getState().logic).toBe("or");
    });

    it("switches logic back to and", () => {
      useFilterStore.getState().setLogic("or");
      useFilterStore.getState().setLogic("and");
      expect(useFilterStore.getState().logic).toBe("and");
    });
  });

  describe("setPrimaryKey", () => {
    it("updates the primary key", () => {
      useFilterStore.getState().setPrimaryKey("my-key");
      expect(useFilterStore.getState().primaryKey).toBe("my-key");
    });
  });

  describe("toFilterGroup", () => {
    it("returns undefined when there are no conditions", () => {
      expect(useFilterStore.getState().toFilterGroup()).toBeUndefined();
    });

    it("returns a FilterGroup with conditions stripped of client-side id", () => {
      useFilterStore.getState().addCondition("age", "integer");
      useFilterStore.getState().setLogic("or");

      const group = useFilterStore.getState().toFilterGroup();

      expect(group).toBeDefined();
      expect(group!.logic).toBe("or");
      expect(group!.conditions).toHaveLength(1);
      expect(group!.conditions[0].bin).toBe("age");
      expect(group!.conditions[0].operator).toBe("eq");
      expect(group!.conditions[0].binType).toBe("integer");
    });

    it("includes multiple conditions", () => {
      useFilterStore.getState().addCondition("age", "integer");
      useFilterStore.getState().addCondition("name", "string");

      const group = useFilterStore.getState().toFilterGroup();

      expect(group!.conditions).toHaveLength(2);
    });
  });

  describe("reset", () => {
    it("restores initial state", () => {
      useFilterStore.getState().addCondition("age", "integer");
      useFilterStore.getState().setLogic("or");
      useFilterStore.getState().setPrimaryKey("pk");

      useFilterStore.getState().reset();

      const state = useFilterStore.getState();
      expect(state.conditions).toEqual([]);
      expect(state.logic).toBe("and");
      expect(state.primaryKey).toBe("");
    });
  });
});
