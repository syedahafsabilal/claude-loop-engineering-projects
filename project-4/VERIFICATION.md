# Project-4 Verification


## Bug
`apply_discount` in `src/cart.py` used a strict `>` comparison instead of `>=`,
so a subtotal of exactly $100 did not receive the documented 10% discount.


## Loop result: good fix
Implementer fixed the source (`>` -> `>=`). Reviewer graded it:
**PASS** — root cause fixed in source, matches spec, no unrelated files touched.


## Loop result: planted bad fix
A bad fix was planted by editing the test's expected value instead of fixing
the source. Reviewer graded it:
**FAIL** — test was weakened instead of source being fixed; root cause
(the boundary bug) remained unaddressed.


## Conclusion
The maker-checker loop correctly distinguishes a real fix from a fake one.
