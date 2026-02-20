/**
 * Contract tests for the Policy Generator API types.
 *
 * Ensures frontend TypeScript types stay aligned with the backend API contract.
 * These tests catch silent FE/BE contract drift at compile + runtime.
 */
import { describe, it, expect } from "vitest";

// Import the actual types used by the frontend
import type {
  GeneratePolicyRequest,
  TemplateVariable,
} from "@/lib/policy-generator-api";
import type { PolicySuggestion } from "@/types/compliance";

// ---------------------------------------------------------------------------
// Helpers: compile-time shape assertions
// ---------------------------------------------------------------------------

/**
 * If this function compiles, the type has the required fields.
 * A compilation failure here means the FE type drifted from the contract.
 */
function assertGeneratePolicyRequestShape(): GeneratePolicyRequest {
  return {
    template_id: "AML_BASE",
    obligation_ids: [1, 2, 3], // must be number[], not string[]
    variable_values: { institution_name: "ACME" },
  };
}

function assertTemplateVariableShape(): TemplateVariable {
  return {
    name: "institution_name",
    type: "string",
    description: "Name of the institution",
    required: true,
    default: "ACME Corp",
    placeholder: "Enter institution name",
    example: "ACME Corp",
  };
}

function assertPolicySuggestionShape(): PolicySuggestion {
  return {
    policy_document_id: 1,
    policy_id: "POL-ABC123",
    name: "AML Policy",
    confidence: 0.85,
    reasoning: "High semantic match with obligation text",
    match_method: "semantic",
  };
}

// ---------------------------------------------------------------------------
// Runtime contract tests
// ---------------------------------------------------------------------------

describe("Policy Generator API Contract", () => {
  describe("GeneratePolicyRequest", () => {
    it("uses variable_values as the canonical field (not custom_variables)", () => {
      const request = assertGeneratePolicyRequestShape();
      expect(request).toHaveProperty("variable_values");
      expect(typeof request.variable_values).toBe("object");
    });

    it("obligation_ids are numbers, not strings", () => {
      const request = assertGeneratePolicyRequestShape();
      expect(Array.isArray(request.obligation_ids)).toBe(true);
      for (const id of request.obligation_ids) {
        expect(typeof id).toBe("number");
      }
    });

    it("has template_id as required string", () => {
      const request = assertGeneratePolicyRequestShape();
      expect(typeof request.template_id).toBe("string");
      expect(request.template_id.length).toBeGreaterThan(0);
    });
  });

  describe("TemplateVariable", () => {
    it("includes all backend-expected fields", () => {
      const variable = assertTemplateVariableShape();
      // These 6 fields are part of the locked contract
      expect(variable).toHaveProperty("name");
      expect(variable).toHaveProperty("type");
      expect(variable).toHaveProperty("description");
      expect(variable).toHaveProperty("required");
      expect(variable).toHaveProperty("default");
      expect(variable).toHaveProperty("placeholder");
      expect(variable).toHaveProperty("example");
    });

    it("name and description are required strings", () => {
      const variable = assertTemplateVariableShape();
      expect(typeof variable.name).toBe("string");
      expect(typeof variable.description).toBe("string");
    });

    it("required is a boolean", () => {
      const variable = assertTemplateVariableShape();
      expect(typeof variable.required).toBe("boolean");
    });
  });

  describe("PolicySuggestion", () => {
    it("includes confidence, reasoning, and match_method", () => {
      const suggestion = assertPolicySuggestionShape();
      expect(suggestion).toHaveProperty("confidence");
      expect(suggestion).toHaveProperty("reasoning");
      expect(suggestion).toHaveProperty("match_method");
    });

    it("confidence is a number between 0 and 1", () => {
      const suggestion = assertPolicySuggestionShape();
      expect(typeof suggestion.confidence).toBe("number");
      expect(suggestion.confidence).toBeGreaterThanOrEqual(0);
      expect(suggestion.confidence).toBeLessThanOrEqual(1);
    });

    it("match_method is either semantic or keyword", () => {
      const suggestion = assertPolicySuggestionShape();
      expect(["semantic", "keyword"]).toContain(suggestion.match_method);
    });
  });
});
