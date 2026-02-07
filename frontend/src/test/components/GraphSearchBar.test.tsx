import { describe, it, expect } from "vitest";
import { matchNodeToQuery } from "../../utils/graphSearch";
import type { GraphNode } from "../../types/graph";

function makeNode(overrides: Partial<GraphNode> & { id: string; label: string }): GraphNode {
  return {
    type: "class",
    metadata: {},
    ...overrides,
  };
}

describe("matchNodeToQuery", () => {
  it("returns null for empty query", () => {
    const node = makeNode({ id: "1", label: "Foo" });
    expect(matchNodeToQuery(node, "")).toBeNull();
    expect(matchNodeToQuery(node, "  ")).toBeNull();
  });

  it("matches by label (case-insensitive)", () => {
    const node = makeNode({ id: "1", label: "UserController" });
    const result = matchNodeToQuery(node, "usercontroller");
    expect(result).toEqual({ nodeId: "1", matchType: "label" });
  });

  it("matches by partial label", () => {
    const node = makeNode({ id: "1", label: "UserController" });
    const result = matchNodeToQuery(node, "Control");
    expect(result).toEqual({ nodeId: "1", matchType: "label" });
  });

  it("matches by FQN when label does not match", () => {
    const node = makeNode({
      id: "1",
      label: "UserController",
      metadata: { fqn: "com.example.controllers.UserController" },
    });
    const result = matchNodeToQuery(node, "com.example");
    expect(result).toEqual({ nodeId: "1", matchType: "fqn" });
  });

  it("returns null when nothing matches", () => {
    const node = makeNode({ id: "1", label: "Foo" });
    expect(matchNodeToQuery(node, "zzzzz")).toBeNull();
  });

  describe("annotation filter (@)", () => {
    it("matches node label containing annotation query", () => {
      const node = makeNode({ id: "1", label: "UserController" });
      const result = matchNodeToQuery(node, "@Controller");
      expect(result).toEqual({ nodeId: "1", matchType: "annotation" });
    });

    it("returns null for non-matching annotation", () => {
      const node = makeNode({ id: "1", label: "UserService" });
      expect(matchNodeToQuery(node, "@Controller")).toBeNull();
    });

    it("returns null for bare @", () => {
      const node = makeNode({ id: "1", label: "Foo" });
      expect(matchNodeToQuery(node, "@")).toBeNull();
    });
  });

  describe("type filter (type:)", () => {
    it("matches node type", () => {
      const node = makeNode({ id: "1", label: "Foo", type: "interface" });
      const result = matchNodeToQuery(node, "type:interface");
      expect(result).toEqual({ nodeId: "1", matchType: "type" });
    });

    it("matches partial type prefix", () => {
      const node = makeNode({ id: "1", label: "Foo", type: "endpoint" });
      const result = matchNodeToQuery(node, "type:end");
      expect(result).toEqual({ nodeId: "1", matchType: "type" });
    });

    it("returns null for non-matching type", () => {
      const node = makeNode({ id: "1", label: "Foo", type: "class" });
      expect(matchNodeToQuery(node, "type:interface")).toBeNull();
    });

    it("returns null for empty type query", () => {
      const node = makeNode({ id: "1", label: "Foo" });
      expect(matchNodeToQuery(node, "type:")).toBeNull();
    });
  });

  describe("modifier filter", () => {
    it("matches by modifier", () => {
      const node = makeNode({
        id: "1",
        label: "BaseService",
        metadata: { modifiers: ["public", "abstract"] },
      });
      const result = matchNodeToQuery(node, "abstract");
      expect(result).toEqual({ nodeId: "1", matchType: "modifier" });
    });

    it("is case-insensitive for modifiers", () => {
      const node = makeNode({
        id: "1",
        label: "Foo",
        metadata: { modifiers: ["Abstract"] },
      });
      const result = matchNodeToQuery(node, "abstract");
      expect(result).toEqual({ nodeId: "1", matchType: "modifier" });
    });

    it("returns null when node lacks the modifier", () => {
      const node = makeNode({
        id: "1",
        label: "Foo",
        metadata: { modifiers: ["public"] },
      });
      expect(matchNodeToQuery(node, "abstract")).toBeNull();
    });

    it("returns null when node has no modifiers", () => {
      const node = makeNode({ id: "1", label: "Foo" });
      expect(matchNodeToQuery(node, "abstract")).toBeNull();
    });
  });
});
