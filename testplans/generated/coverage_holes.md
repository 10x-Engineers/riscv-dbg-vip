# Coverage holes

None. Every bin in `coverage_model.yaml` is claimed by at least one testplan
item, or excluded with a stated reason.

Regenerate with:

```bash
python3 ~/.claude/skills/functional-coverage/scripts/reconcile.py \
    testplans/generated/coverage_model.yaml \
    --testplan testplans/riscv_debug_testplan.md --emit-holes testplans/generated/coverage_holes.md
```

The 186 in-scope testplan items that contribute to no bin are the other
direction of the same check: either the coverage model is blind to them, or
they have no verification objective. Most are Stimulate rows whose paired
Check row owns the bin, which is expected; the rest are worth a pass.
