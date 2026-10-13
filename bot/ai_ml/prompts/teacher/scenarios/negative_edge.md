Focus: Input Validation, Boundary Conditions, and Error Recovery (P1/P2)
- Empty Submissions: Attempt to submit required forms without filling fields -> assert validation error text is displayed and URL does not change.
- Format Violations: Input invalid email formats (e.g., 'user@', 'user.com') -> assert specific inline error feedback.
- Boundary Limits: Input extreme boundary strings (200+ characters) -> assert UI handles gracefully without 500 error.
