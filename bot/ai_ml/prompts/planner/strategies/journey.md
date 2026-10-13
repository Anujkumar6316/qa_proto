Target QA Strategy: JOURNEY

Generate multi-page JOURNEY test cases spanning 2+ URLs in sequence (e-commerce checkout, booking, auth):
  - E-Commerce Purchase Flow: Product details -> Add to Cart -> Cart View -> Checkout -> Payment -> Order Confirmation.
  - Multi-Step Form: Step 1 Profile -> Step 2 Preferences -> Step 3 Verification -> Finish.
  - Authentication Flow: Home -> Login -> Dashboard redirect -> Profile settings.
Each journey test case must:
  - Set 'type': 'journey', 'category': 'journey', and 'journey_pages' listing the page_ids traversed.
  - Use 'navigate' action steps to transition between URLs (value = target URL).
  - Set 'page_context' on steps to identify which page's @eN refs are being acted on.
  - End with a terminal assertion on the final destination page.

Generate automated QA test cases for the following web page context:

```json
{planner_input}
```

Multi-Page Journey Traversal Context:
```json
{journey_context}
```
When generating journey test cases:
- Set 'type': 'journey' and 'category': 'journey'.
- Use action 'navigate' with value=<url> to navigate between pages.
- Provide 'page_context' on steps to identify which page's components are referenced.
- Embed 'page_registry' mapping page_id -> {url, components} at the root of the plan.

Instructions:
1. Prioritize critical paths matching the 'objective' and 'Target QA Strategy'.
2. For action steps (click, fill, hover), reference target elements using their exact '@eN' handles from the context in 'target_ref', AND copy the component's 'fingerprint' verbatim into 'target_selector' (it is the stable CSS selector used at execution time — never invent or modify it).
3. Include both positive flows and edge-case negative validations.
4. Handle dynamic disclosures (e.g. dropdowns, modals) via hover/click actions.
5. Every test case MUST include an explicit 'id' (e.g. 'TC_001'), 'title', 'category', 'severity', 'target_ref', 'hypothesis', 'steps', and 'expected_outcome'.
6. Every test case MUST have at least 2 steps. Allowed step actions: 'click', 'fill', 'hover', 'press_key', 'navigate'.
7. In steps, use 'target_ref' for element handles (not 'ref'), and 'value' for press_key or navigate (not 'key' or 'url').
8. The final step of every test case MUST be a terminal assertion: 'assert_visible', 'assert_hidden', 'assert_url_contains', 'assert_text', or 'assert_attr'. For dynamic feedback (error messages, confirmation alerts, toast notifications) that appear after action, you can set 'target_ref': null with the expected text in 'value' (e.g. action: 'assert_text', target_ref: null, value: 'Your username is invalid!').
9. The root JSON object MUST contain the exact key: 'plan_version': 'qa-plan-v2', along with 'target_url', 'test_suite', 'thought_analysis', and 'test_cases'.
10. Submit semantics: for live-filter/search inputs that filter client-side without navigating, assert on the filtered results (visible items), NEVER on URL changes. Only assert navigation for controls that actually submit or navigate.
11. Injection probes (XSS): assert ABSENCE of execution — no dialog fires, no script node is injected, input is treated as text. Never assert the payload string appears in page text.
12. assert_text copy: prefer text observed in the page context (component names, headings). Do not invent site-specific messages. assert_attr MUST put the attribute name in 'attribute' (e.g. 'expanded'), never in 'value'.
13. All 'value' fields MUST be plain JSON string literals — never JavaScript expressions, template literals, or concatenation (e.g. forbidden: '"a".repeat(200)', '`text${x}`', '"a" + "b"'). For long inputs, write the literal characters out in full.
