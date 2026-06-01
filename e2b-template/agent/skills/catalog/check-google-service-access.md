---
name: check-google-service-access
description: Use Composio integrations to check which Google services (Gmail, Google Sheets, Google Drive) are connected and list available actions for each.
---

# Checking Google Service Access via Composio

When a user asks whether you have access to their Gmail, Google Sheets, or Google Drive, follow this pattern to discover what is available.

## Steps

1. **Check connected apps**  
   Use the `composio_list_connected_apps` tool (or similar) to see which Google services are already linked.

   Example:
   ```
   tool_call(tool="composio_list_connected_apps")
   ```
   Response: `Connected apps: gmail, googledrive, googlesheets`

2. **Find actions for each app**  
   For each connected app, use `composio_find_actions` with the `toolkit` parameter set to the app name (e.g., `"gmail"`, `"googledrive"`, `"googlesheets"`).

   **Important:** The correct parameter is `toolkit`, not `app`. If you get a `wrong arguments` error, use `tool_describe` on the function to view the full schema.

   Example:
   ```
   tool_call(tool="composio_find_actions", toolkit="gmail")
   tool_call(tool="composio_find_actions", toolkit="googledrive")
   tool_call(tool="composio_find_actions", toolkit="googlesheets")
   ```

3. **Summarize the results**  
   Inform the user that all three are connected and briefly mention the number of actions available for each (e.g., 23 for Gmail, 30 for Drive, 30 for Sheets).

## Full Example Trajectory

```
User: do you have access to my gmail, gsheets and gdrive
Agent: [check connected apps via composio_list_connected_apps]
       → Connected apps: gmail, googledrive, googlesheets
Agent: [for each app, call composio_find_actions with toolkit parameter]
       → Lists of actions returned
Agent: "Yes — all three are connected! Here’s what I can do..."
```

## Notes

- Always verify the function signature using `tool_describe` if a call fails.
- The `composio_find_actions` function's parameter is `toolkit` (string), not `app`.
- Multiple apps can be queried in parallel (e.g., three simultaneous calls).