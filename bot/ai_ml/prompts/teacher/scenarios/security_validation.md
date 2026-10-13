Focus: Form Hardening, Input Sanitization, and State Guardrails (P0/P1)
- XSS Sanitization: Input probe payloads (e.g., '<script>alert(1)</script>' or '" onfocus="alert(1)') -> submit -> assert characters are safely escaped as plain text.
- Disabled Element Gating: Target disabled controls ('disabled: true') -> assert element cannot receive focus or trigger actions.
- Gated Navigation: Verify restricted administrative or account links require an active session.
