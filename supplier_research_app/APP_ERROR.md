# Supplier Research App Error Recovery

Use this when the supplier research app crashes, returns HTML instead of JSON, or behaves like old code is still running.

## 1. Open PowerShell

Start a new PowerShell window.

## 2. Go to the app folder

```powershell
cd "c:\Users\lenovo\Desktop\Claude work\supplier_research_app"
```

## 3. Check for old Flask or Python processes

```powershell
Get-Process python, flask -ErrorAction SilentlyContinue
```

If this shows old processes, stop them.

## 4. Kill old processes

```powershell
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Stop-Process -Name flask -Force -ErrorAction SilentlyContinue
```

## 5. Confirm all old processes are gone

```powershell
Get-Process python, flask -ErrorAction SilentlyContinue
```

If nothing is returned, the old processes are cleared.

## 6. Activate the virtual environment

```powershell
& "c:\Users\lenovo\Desktop\Claude work\.venv\Scripts\Activate.ps1"
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Then activate again:

```powershell
& "c:\Users\lenovo\Desktop\Claude work\.venv\Scripts\Activate.ps1"
```

## 7. Start the app

Use the normal startup command:

```powershell
python wsgi.py
```

If your setup uses Flask directly instead, use:

```powershell
$env:FLASK_APP="wsgi.py"
flask run
```

## 8. Wait for the server startup message

Look for output like:

```text
Running on http://127.0.0.1:5000
```

## 9. Test in a fresh browser session

Open an Incognito or Private window and go to:

```text
http://127.0.0.1:5000
```

Log in and test the supplier research flow.

## 10. Test simultaneous searches

To confirm the concurrency fix:

1. Start one supplier search in the first tab.
2. Open a second tab and start another search.
3. Open a third tab if needed and start one more.

If all complete, the queue and retry handling are working.

## 11. If an error happens

Do not close the PowerShell window.

Copy:

- The browser error message
- The PowerShell error output

Share both so the issue can be traced.

## Common Symptoms

### Error: `Unexpected token '<'`

This usually means the browser received HTML instead of JSON.

Possible causes:

- Old Flask process still running
- Server crashed and returned an error page
- Rate limiting or Cloudflare returned HTML
- Browser loaded stale JavaScript

### App looks unchanged after code updates

Possible causes:

- Old Python process still running
- Browser cache still serving old JavaScript

Fix:

- Kill all Python and Flask processes
- Restart the app
- Test again in Incognito

## Email Search Behavior

The app is expected to find the generic email in this order:

1. Official website pages first
2. Contact, contact-us, support, about, and similar pages
3. Rendered pages for sites that inject email text with JavaScript
4. Official Facebook page linked from the website, only if the website did not yield a valid generic email

Accepted generic emails are same-domain emails such as:

- `info@`
- `sales@`
- `contact@`
- `support@`
- `admin@`
- `hello@`

The Facebook fallback should still return a company-domain email, not an unrelated personal address.

## Quick Recovery Checklist

```powershell
cd "c:\Users\lenovo\Desktop\Claude work\supplier_research_app"
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Stop-Process -Name flask -Force -ErrorAction SilentlyContinue
& "c:\Users\lenovo\Desktop\Claude work\.venv\Scripts\Activate.ps1"
python wsgi.py
```
