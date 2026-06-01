---
name: get-latest-google-sheet
description: Retrieves the most recently modified Google Sheet from the user's connected Google Sheets account and returns its link.
---
# Get the Latest Google Sheet

Use this pattern when a user asks for their "latest" or "most recent" Google Sheet.

## Prerequisites

- Google Sheets must be connected (verify with `composio_list_apps` or a pre‑existing access check skill).

## Steps

1. **Find the search action**  
   Use `composio_find_actions` with app name `GOOGLESHEETS` to discover the available actions. Look for `GOOGLESHEETS_SEARCH_SPREADSHEETS`.

2. **Search for the latest sheet**  
   Execute `composio_execute` with:
   - `action`: `GOOGLESHEETS_SEARCH_SPREADSHEETS`
   - `params`:
     ```json
     {
       "q": "mimeType='application/vnd.google-apps.spreadsheet' and trashed = false",
       "orderBy": "modifiedTime desc",
       "pageSize": 1
     }
     ```

   *Note:* If the initial search returns no results, try removing the `orderBy` or `pageSize` parameters, or check that the user has any spreadsheets.

3. **Return the result**  
   From the response, extract the `spreadsheetUrl` field (or `link`) of the first file. Present it to the user in a clear format (e.g., markdown link or plain URL).

## Example

**User:** Can you pull up a sheet link of my latest saved sheet?

**Agent:**  
1. `composio_list_apps` → confirms `googlesheets` is connected.  
2. `composio_find_actions(app="GOOGLESHEETS")` → finds `GOOGLESHEETS_SEARCH_SPREADSHEETS`.  
3. Executes search with `q` and `orderBy` → gets the most recently modified spreadsheet.  
4. Returns: "Your latest sheet is **[H-1B Sponsors - FY2026](<url>)** (modified ~6 hours ago)."

## Troubleshooting

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| 400 Bad Request | Incorrect query syntax or missing permissions | Double‑check the `q` string and ensure the app is authorised. |
| Empty response | No spreadsheets exist | Inform the user that no sheets were found. |
| Action not found | App not connected or action misnamed | Re‑run `composio_list_apps` and verify the action name. |