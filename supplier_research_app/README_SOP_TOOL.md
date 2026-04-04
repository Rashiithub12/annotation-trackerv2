# SOP Supplier Research Tool

This app is now set up for this workflow:

1. Enter one company website.
2. Click research.
3. Wait for the app to research the site automatically.
4. Review the 9 SOP fields.
5. Edit if needed.
6. Export CSV when ready.

Output columns:

1. Company Name
2. Website
3. Generic Email
4. Brands/Products
5. Email Source URL
6. Brands/Products Source URL
7. Brand Categories
8. Duplicate
9. Marketplace

Important:

- The app needs a working `MINIMAX_API_KEY` in Railway or `.env`.
- Live website research also needs internet access when the app is running.
- Marketplace is stricter now and duplicate checks use already researched records.
- Team usage can be controlled with `RESEARCH_QUEUE_WORKERS` (set `3` for three simultaneous researchers).

Run locally from this folder:

```powershell
@'
from app import create_app
app = create_app()
app.run(debug=True)
'@ | python -
```
