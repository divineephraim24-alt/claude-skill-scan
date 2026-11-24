# claude-skill-scan

Private settings for the automatic skill safety check in Claude Code cloud sessions.

- `reviewed.json`: skills and plugins already reviewed, with the verdict (APPROVE, CAUTION or REJECT),
  a short note, and the fingerprint of the exact version that was reviewed. If a skill changes,
  its fingerprint changes and it is flagged for review again.
- `scan.py`: runs SkillSpector on user-added skills at session start and reports the results.

The cloud environment's setup script copies both files into `~/.claude/skill-scan/` when a
session starts. If this repo isn't loaded, the check still runs but warns that nothing has
been reviewed.

No passwords, keys or tokens belong in this repo.
