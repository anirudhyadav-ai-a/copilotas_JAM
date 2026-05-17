import {
    JUDGE_REVIEW_SYSTEM,
    JUDGE_SECURITY_SYSTEM,
    ADVOCATE_ADR_SYSTEM,
    ADVOCATE_DEVIL_SYSTEM,
    MEDIATOR_DESIGN_SYSTEM,
    MEDIATOR_DEPS_SYSTEM,
} from './prompts';

// ─────────────────────────────────────────────────────────────────
//  Prompt content sanity checks
//  These tests verify that each prompt:
//    1. Is a non-empty string
//    2. Contains its required output format markers
//    3. Stays within a sane character length (catch accidental truncation)
// ─────────────────────────────────────────────────────────────────

describe('JUDGE_REVIEW_SYSTEM', () => {
    it('is a non-empty string', () => {
        expect(typeof JUDGE_REVIEW_SYSTEM).toBe('string');
        expect(JUDGE_REVIEW_SYSTEM.length).toBeGreaterThan(100);
    });

    it('contains verdict output marker', () => {
        expect(JUDGE_REVIEW_SYSTEM).toContain('VERDICT:');
    });

    it('contains rubric sections', () => {
        expect(JUDGE_REVIEW_SYSTEM).toContain('Code Quality');
        expect(JUDGE_REVIEW_SYSTEM).toContain('Security');
        expect(JUDGE_REVIEW_SYSTEM).toContain('Testing');
        expect(JUDGE_REVIEW_SYSTEM).toContain('Architecture');
    });

    it('specifies valid verdict options', () => {
        expect(JUDGE_REVIEW_SYSTEM).toContain('APPROVE');
        expect(JUDGE_REVIEW_SYSTEM).toContain('REQUEST_CHANGES');
        expect(JUDGE_REVIEW_SYSTEM).toContain('BLOCK');
    });
});

describe('JUDGE_SECURITY_SYSTEM', () => {
    it('is a non-empty string', () => {
        expect(typeof JUDGE_SECURITY_SYSTEM).toBe('string');
        expect(JUDGE_SECURITY_SYSTEM.length).toBeGreaterThan(100);
    });

    it('contains OWASP reference', () => {
        expect(JUDGE_SECURITY_SYSTEM).toContain('OWASP');
    });

    it('contains risk level output marker', () => {
        expect(JUDGE_SECURITY_SYSTEM).toContain('Risk Level:');
    });

    it('specifies valid verdict options', () => {
        expect(JUDGE_SECURITY_SYSTEM).toContain('PASS');
        expect(JUDGE_SECURITY_SYSTEM).toContain('WARN');
        expect(JUDGE_SECURITY_SYSTEM).toContain('FAIL');
    });
});

describe('ADVOCATE_ADR_SYSTEM', () => {
    it('is a non-empty string', () => {
        expect(typeof ADVOCATE_ADR_SYSTEM).toBe('string');
        expect(ADVOCATE_ADR_SYSTEM.length).toBeGreaterThan(100);
    });

    it('contains ADR section markers', () => {
        expect(ADVOCATE_ADR_SYSTEM).toContain('## Context');
        expect(ADVOCATE_ADR_SYSTEM).toContain('## Decision');
        expect(ADVOCATE_ADR_SYSTEM).toContain('## Rationale');
        expect(ADVOCATE_ADR_SYSTEM).toContain('## Consequences');
    });

    it('includes anticipated objections section', () => {
        expect(ADVOCATE_ADR_SYSTEM).toContain('Anticipated Objections');
    });
});

describe('ADVOCATE_DEVIL_SYSTEM', () => {
    it('is a non-empty string', () => {
        expect(typeof ADVOCATE_DEVIL_SYSTEM).toBe('string');
        expect(ADVOCATE_DEVIL_SYSTEM.length).toBeGreaterThan(100);
    });

    it('contains verdict output marker', () => {
        expect(ADVOCATE_DEVIL_SYSTEM).toContain('Verdict:');
    });

    it('specifies valid verdict options', () => {
        expect(ADVOCATE_DEVIL_SYSTEM).toContain('PROCEED');
        expect(ADVOCATE_DEVIL_SYSTEM).toContain('REVISE');
        expect(ADVOCATE_DEVIL_SYSTEM).toContain('RECONSIDER');
    });

    it('includes gate rules for the engineer', () => {
        expect(ADVOCATE_DEVIL_SYSTEM).toContain('Gate rule');
    });
});

describe('MEDIATOR_DESIGN_SYSTEM', () => {
    it('is a non-empty string', () => {
        expect(typeof MEDIATOR_DESIGN_SYSTEM).toBe('string');
        expect(MEDIATOR_DESIGN_SYSTEM.length).toBeGreaterThan(100);
    });

    it('contains synthesis output marker', () => {
        expect(MEDIATOR_DESIGN_SYSTEM).toContain('Synthesis:');
    });

    it('contains common ground and real disagreement markers', () => {
        expect(MEDIATOR_DESIGN_SYSTEM).toContain('Common Ground:');
        expect(MEDIATOR_DESIGN_SYSTEM).toContain('Real Disagreement:');
    });
});

describe('MEDIATOR_DEPS_SYSTEM', () => {
    it('is a non-empty string', () => {
        expect(typeof MEDIATOR_DEPS_SYSTEM).toBe('string');
        expect(MEDIATOR_DEPS_SYSTEM.length).toBeGreaterThan(100);
    });

    it('contains resolution output marker', () => {
        expect(MEDIATOR_DEPS_SYSTEM).toContain('Resolution:');
    });

    it('contains verification command marker', () => {
        expect(MEDIATOR_DEPS_SYSTEM).toContain('Verification command:');
    });
});
