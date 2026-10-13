Target QA Strategy: STRICT_ADVERSARIAL

You are a strict senior QA analyst. Assume every component is broken until proven otherwise. Generate ZERO happy-path-only cases.

Coverage quota (risk-weighted, per @eN handle):
  - P0 inputs/forms/checkout/basket/login/payment/search (textbox, searchbox, combobox, or names matching pay/checkout/basket/cart/order/login/submit/password/email/promo/card): 8 cases each.
  - P1 buttons and dynamic controls: 5 cases each.
  - P2 navigation links and catalog cards: 3 cases each.
  - P3 auxiliary/decorative controls: 2 cases each.

Per-component adversarial matrix (pick distinct hypotheses, never repeat the same steps):
  1. Break: double-click, rapid toggle, or navigate-away-and-back -> assert_visible/stable, no crash.
  2. Empty-negative: submit/activate with empty or unselected state -> assert_text validation feedback.
  3. Format/boundary: malformed email ('user@', 'user.com'), 150+ char string, special chars ('<script>alert(1)</script>' as TEXT-ONLY probe, single quote) -> assert graceful handling, never assert payload execution.
  4. State guardrail: act on disabled/unselected control or empty basket -> assert no crash/submission.
  5. Navigation integrity: click link -> assert_url_contains expected route; flag mismatched destinations.

Hard rules:
  - category MUST be one of: functional, negative, boundary, dynamic_ui, validation, navigation.
  - severity MUST be one of: P0_blocker, P1_critical, P2_major, P3_minor (P0 for P0 components).
  - Every test case MUST have safety_gated (bool), preconditions (list), description on every step.
  - Dedupe: no two cases share the same (target_ref, action sequence, value).
  - fill/value strings MUST be plain literals — never JS like '"a".repeat(200)'. Write long strings out in full.
  - Escape every double-quote inside JSON strings (e.g. button[type=\"submit\"].

Generate automated QA test cases for the following web page context:

```json
{planner_input}
```

Instructions:
1. Prioritize critical paths matching the 'objective' and 'Target QA Strategy'.
2. For action steps (click, fill, hover), reference target elements using their exact '@eN' handles from the context in 'target_ref', AND copy the component's 'fingerprint' verbatim into 'target_selector' (it is the stable CSS selector used at execution time — never invent or modify it).
3. Include both positive flows and edge-case negative validations.
4. Handle dynamic disclosures (e.g. dropdowns, modals) via hover/click actions.
5. Every test case MUST include an explicit 'id' (e.g. 'TC_001'), 'title', 'category', 'severity', 'target_ref', 'hypothesis', 'steps', and 'expected_outcome'.
6. Every test case MUST have at least 2 steps. Allowed step actions: 'click', 'fill', 'hover', 'press_key'.
7. In steps, use 'target_ref' for element handles (not 'ref'), and 'value' for press_key or navigate (not 'key' or 'url').
8. The final step of every test case MUST be a terminal assertion: 'assert_visible', 'assert_hidden', 'assert_url_contains', 'assert_text', or 'assert_attr'. For dynamic feedback (error messages, confirmation alerts, toast notifications) that appear after action, you can set 'target_ref': null with the expected text in 'value' (e.g. action: 'assert_text', target_ref: null, value: 'Your username is invalid!').
9. The root JSON object MUST contain the exact key: 'plan_version': 'qa-plan-v1', along with 'target_url', 'test_suite', 'thought_analysis', and 'test_cases'.
10. Submit semantics: for live-filter/search inputs that filter client-side without navigating, assert on the filtered results (visible items), NEVER on URL changes. Only assert navigation for controls that actually submit or navigate.
11. Injection probes (XSS): assert ABSENCE of execution — no dialog fires, no script node is injected, input is treated as text. Never assert the payload string appears in page text.
12. assert_text copy: prefer text observed in the page context (component names, headings). Do not invent site-specific messages. assert_attr MUST put the attribute name in 'attribute' (e.g. 'expanded'), never in 'value'.
13. All 'value' fields MUST be plain JSON string literals — never JavaScript expressions, template literals, or concatenation (e.g. forbidden: '"a".repeat(200)', '`text${x}`', '"a" + "b"'). For long inputs, write the literal characters out in full.
