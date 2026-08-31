# Production readiness boundary

Before executing a real recovery game day:

- Obtain written scope, owner approval and maintenance-window authority.
- Use least-privilege experiment identities with time-bounded access.
- Define blast radius, steady-state hypothesis, abort conditions and rollback.
- Verify backup immutability, isolation, retention and recovery credentials.
- Capture signed detection, failure, recovery and transaction timestamps.
- Validate identity, DNS, secrets, networking, data, messaging and external dependencies.
- Reconcile duplicates, missing transactions, checksums and financial state.
- Exercise backlog recovery and failback, not only initial service availability.
- Protect clean-room recovery from compromised production identity and connectivity.
- Retain raw experiment, restore and validation evidence.

Never begin destructive production experiments from an autonomous agent or an unreviewed pull request.
