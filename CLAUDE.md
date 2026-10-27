# MedSEAS dashboard

Owner: Witold (SneakySquidz). This repo is public: keep everything here free of personal and client details.

## Report back to the Second Brain (every session)
Witold's project register lives in the private repo `SneakySquidz/second-brain`, file `dashboard/data.js`, entry `medseas`. When a session here changes this project's status, next step or a deadline, or finishes something:
1. In `second-brain`, create a branch `claude/medseas-<short-topic>` and edit only the `medseas` entry in `dashboard/data.js` (`status`, `next`, `deadline`, `updated`). Generic wording, no names or amounts.
2. Push the branch; don't merge it. CHIEF, his main assistant on the Mac, reviews and applies it to the master copy, and the nightly build updates everything else.
3. If you can't reach that repo, end your reply with a short block starting `→ CHIEF` (project, what changed, next step, any date) for Witold to paste.
