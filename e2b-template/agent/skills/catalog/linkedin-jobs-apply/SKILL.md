---
name: linkedin-jobs-apply
description: Apply for jobs on LinkedIn via Easy Apply, external ATS, or Gmail outreach. Covers Shadow DOM traversal, file upload, connection invites, DMs, and hiring post harvesting. Use for any LinkedIn task.
---

## ⛔ HARD BANS — THESE SLOW YOU DOWN BY MINUTES, NOT SECONDS

```
BANNED: take_screenshot twice in a row — you just got the image, use it. Never screenshot again until at least 3 other tool calls have happened.
BANNED: take_snapshot after every single click — only snapshot when you need element IDs you don't already have.
BANNED: fill() one field at a time for 3+ fields — use one evaluate_script with native setter to fill all text fields in a single call.
BANNED: snapshot → fill → snapshot → fill loops — that pattern adds 30+ seconds per form step.
BANNED: take_screenshot when take_snapshot would answer the question — screenshot is for visual content only (images, charts). Everything else: take_snapshot or evaluate_script.
```

**Real cost of ignoring these**: a single extra take_screenshot call timed out for 60 seconds in a real run. Sequential fill() calls added 25+ seconds on a 5-field form. These are not style preferences — they are measured time losses.

---

# AGENT PLAYBOOK — 2026-06-01 (LIVE VERIFIED)

> Every technique below was executed for real in a single session. Times are actual. The account is prahaladreddy80@gmail.com / LinkedIn logged in.

---

## RULE 0 — Speed laws

- **NEVER take_screenshot twice without at least 3 tool calls in between.** You already have the image — use it. A second consecutive screenshot wastes 60+ seconds if BrowserOS is under load.
- **NEVER do snapshot → fill → snapshot → fill for multi-field forms.** Use ONE evaluate_script that fills all text fields + triggers React events in a single call. Saves 25–30s per form step.
- **NEVER take_snapshot after every click** — only snapshot when you need new element IDs. After a form navigation click, snapshot once, then fill everything before snapshotting again.
- **Build URLs directly** whenever possible. Avoid click chains through navigation.
- **Parallelize**: fire independent tool calls in the same message (LinkedIn + Gmail simultaneously).
- **`search_dom("input[type=file]")` → `backendNodeId` → `upload_file(backendNodeId)`** is the only working file upload path. Hidden inputs never appear in `take_snapshot`.
- **LinkedIn Easy Apply uses Shadow DOM** — `document.getElementById()` and `document.querySelector()` both return nothing from main document context. Always traverse shadow roots (see RULE 1 below).
- **`evaluate_script` for text inputs, `select_option` tool for `<select>`** — the native setter trick works perfectly for text inputs inside shadow DOM. For `<select>` elements, use the `select_option` tool with the visible text (no leading/trailing spaces); the shadow DOM setter returns wrong state for selects.
- **Location combobox is a typeahead, not a select** — use `fill(element, text)` → wait for dropdown → `click(option)`. Never try to set it with evaluate_script.
- **IIFE-wrap evaluate_script when calling it multiple times on the same page** — if you run `let sr = ...` in one call and then run the same variable name again, you get `SyntaxError: Identifier 'sr' has already been declared`. Fix: wrap every evaluate_script body in `(function(){ ... })()` so variable declarations are scoped. Cost: zero. Skip this and you'll hit silent failures on the second call.

---

## RULE 1 — LinkedIn Shadow DOM pattern (CRITICAL)

LinkedIn's Easy Apply modal renders inside a Shadow DOM component. `document.getElementById` and `document.querySelectorAll` from the main frame find nothing. Always use this traversal:

```js
// Find the shadow root containing the Easy Apply form
let sr = null;
for(const el of document.querySelectorAll('*')) {
  if(el.shadowRoot) {
    const inp = el.shadowRoot.querySelectorAll('input.artdeco-text-input--input');
    if(inp.length >= 1) { sr = el.shadowRoot; break; }
  }
}
// sr is now the shadow root — query everything through it
const inputs = sr.querySelectorAll('input.artdeco-text-input--input');
const selects = sr.querySelectorAll('select');
```

**Reliable selectors inside the shadow root:**
- Text inputs: `input.artdeco-text-input--input`
- Selects: `select` (use `select_option` tool, not evaluate_script setter)
- Buttons: `button` filtered by textContent
- Checkboxes: `input[type="checkbox"]`

**Native setter pattern for text inputs (works inside shadow DOM):**
```js
function setInput(el, val){
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
  setter.call(el, val);
  el.dispatchEvent(new Event('input',{bubbles:true}));
  el.dispatchEvent(new Event('change',{bubbles:true}));
}
```

**Why the native setter**: React intercepts `.value = x` assignments. Setting `.value` directly via the prototype descriptor bypasses React's synthetic event system and forces the component to re-render with the new value.

**Do NOT use `select_option` via evaluate_script** — the shadow DOM setter for `<select>` doesn't reliably register with React. Use the `select_option` tool (element ID from snapshot) with the visible text value (no padding spaces).

**Snapshot element IDs automatically pierce shadow DOM** — `take_snapshot` returns element IDs like `[12017]` that the browseros tools (`fill`, `select_option`, `click`) resolve correctly even when the element lives inside a shadow root. You only need the RULE 1 evaluate_script traversal when you're writing raw JS (e.g., bulk-filling 3+ fields with the native setter). For single-field interactions, just use the snapshot ID directly — no shadow DOM traversal needed.

---

## ⛔ REMINDER BEFORE YOU START ANY WORKFLOW

Before executing any step below, commit to this:
- Each form step = ONE snapshot (to get IDs) + ONE evaluate_script (to fill all fields) + ONE click (Continue). Not more.
- If you already took a screenshot this turn, DO NOT take another one. Use take_snapshot or evaluate_script instead.
- If you have 3+ text fields to fill, write one evaluate_script with the native setter for all of them. Do not call fill() repeatedly.

---

## WORKFLOW 1 — LinkedIn Easy Apply (target: under 60 seconds)

**Data you need pre-loaded**: phone number, resume path, job title for experience field.

```
Step 1 — Navigate to Easy Apply search
  navigate_page → https://www.linkedin.com/jobs/search/?keywords=AI+Agent+Engineer&location=India&f_WT=2&f_AL=true
  (f_WT=2 = remote, f_AL=true = Easy Apply only)

Step 2 — Get job links without clicking
  get_page_links(page)
  → extract all href matching /jobs/view/\d+/ 
  → pick the best match

Step 3 — Open job and click Easy Apply
  navigate_page to jobs/view/{id}
  take_snapshot → find button "Easy Apply to ..."
  click(Easy Apply button)

Step 4 — Fill phone + location, then advance
  IMPORTANT: Phone/name/email are usually pre-filled from LinkedIn profile. Only missing field is Location.
  
  fill(location_combobox_element, 'Bangalore')
  → Dropdown appears with suggestions
  click(option "Bengaluru, Karnataka, India")
  click(Continue button)
  
  NOTE: Location field is a typeahead combobox (not a select). Do NOT use evaluate_script for it.
  The combobox element ID comes from take_snapshot — look for combobox "Location (city) *"

Step 5 — Resume already pre-selected (usually)
  LinkedIn pre-populates the last uploaded resume. Check take_snapshot for
  "Download resume [filename]" — if present, just click Continue.
  
  If not pre-selected:
    search_dom(page, "input[type=file]") → get backendNodeId
    upload_file(page, element=backendNodeId, files=["C:\\...\\practice_resume_prahalad_test.pdf"])
  
  click(Continue)

Step 6 — Work experience (fill tool for text, select_option for dropdowns)
  fill(title_element, 'AI/ML Engineer')
  fill(company_element, 'Kairos Computer')
  click(checkbox "I currently work here")   ← removes "To" date fields
  select_option(month_from_element, 'January')
  select_option(year_from_element, '2024')
  click(Save button)
  click(Continue button)

Step 7 — Custom questions (ONE evaluate_script via shadow DOM)
  Use RULE 1 shadow DOM pattern to fill all text inputs in one call.
  Use select_option tool (by element ID from snapshot) for any <select> fields.
  click(Continue / Review your application button)

Step 8 — Submit
  take_snapshot → find "Submit application" button
  click(Submit button)
  → Post-submit screen shows "Update profile / Not now" — click "Not now"
```

**TOTAL: ~12-15 tool calls (more steps than expected due to custom questions per job).**

**Key failure modes:**
- `document.querySelector` finds nothing in Easy Apply form → Shadow DOM. Use RULE 1 pattern.
- evaluate_script for `<select>` doesn't register with React → use `select_option` tool instead
- Location field not accepting typed value → It's a typeahead; must fill() then click() the suggestion
- Phone field not filling → use `id*="phoneNumber-nationalNumber"` selector (only if not pre-filled)
- `backendNodeId` changes each page load — always re-run `search_dom` before `upload_file`
- Some jobs have 2 rounds of custom questions before the Review screen — just keep filling + continuing

---

## WORKFLOW 2 — Gmail cold outreach (target: under 10 seconds)

**The fastest possible approach — zero snapshot/fill loops.**

```
Step 1 — Open pre-filled compose via URL
  new_page(background=true):
    https://mail.google.com/mail/u/0/?view=cm
      &to=EMAIL_URL_ENCODED
      &su=SUBJECT_URL_ENCODED
      &body=BODY_URL_ENCODED

Step 2 — Snapshot compose (one call)
  take_snapshot → find Send button (label: "Send ‪(Ctrl-Enter)‬")

Step 3 — Send
  click(Send button)
```

**TOTAL: 3 tool calls. ~10 seconds.**

**Notes:**
- `mail.google.com/mail/u/0/` = prahaladreddy80@gmail.com (verified logged in)
- URL-encode the body: newlines = `%0A`, spaces = `+`, @ = `%40`
- The compose opens fully pre-filled. No fill/type calls needed.
- If Gmail shows account selector, click prahaladreddy80 link then retry.

---

## WORKFLOW 3 — Hiring post harvesting (target: under 15 seconds)

**Single page, two tool calls, gets all emails + profile URLs.**

```
Step 1 — Navigate to content search
  navigate_page:
    https://www.linkedin.com/search/results/content/
      ?keywords=%22we%27re+hiring%22+%22AI+agent%22
      &sortBy=date_posted

Step 2 — Extract everything in one call
  get_page_links(page)
  → filter results:
    - mailto: links → real recruiter emails
    - linkedin.com/in/ links → profile URLs
    - Post text from evaluate_script(document.body.innerText.slice(0,6000)) if needed

Step 3 — Navigate to recruiter profile
  navigate_page to linkedin.com/in/{slug}/
  get_page_links → email in contact info OR visible in posts
```

**Emails found in one real run**: kanha@computronics.in, srividya@pranathiss.com, chandramohan@velkinz.in — all from one `get_page_links` call.

---

## WORKFLOW 4 — LinkedIn connection invite with note

**Connect buttons appear in search results, sometimes hidden under "More" on profiles.**

```
Step 1 — Search for target
  navigate_page: https://www.linkedin.com/search/results/people/?keywords=AI+recruiter+Bangalore

Step 2 — Click Connect from search results
  evaluate_script:
    const connects = Array.from(document.querySelectorAll('button')).filter(b=>/^connect$/i.test(b.textContent.trim()));
    connects[0]?.click();
    'clicked: ' + connects.length

Step 3 — Add note in modal
  take_snapshot → find "Add a note" button, click it
  take_snapshot → find note textarea
  fill(textarea, "Hi [Name], I saw your post about [role]. I build production AI agent systems (LangChain/LangGraph/RAG). Would love to connect.")
  
Step 4 — Send
  click(Send button)
```

**CRITICAL LIMITATION**: Account has 0 connections. ALL profiles are 3rd+.
- 3rd+ Message button → Premium paywall immediately
- Connect button may not appear on profile page for some 3rd+ accounts (Follow-only)
- **Workaround**: Use search results page — Connect buttons always visible there regardless of degree
- After connecting, wait for acceptance before DMing

---

## WORKFLOW 5 — LinkedIn DM (only works after connecting)

**DMs to 3rd+ connections require LinkedIn Premium (InMail). No bypass exists.**

```
For 1st/2nd connections:
  navigate_page: https://www.linkedin.com/in/{slug}/
  take_snapshot → click "Message" button (no paywall)
  take_snapshot → find contenteditable message box
  fill(message box, text)  OR  evaluate_script with textContent + input event
  take_snapshot → click Send (only enabled after text entered)

For 3rd+ connections:
  → Will show "Try Premium" modal. STOP. 
  → Fall back to Gmail outreach (Workflow 2) or connection invite (Workflow 4).

Messaging page compose:
  navigate_page: https://www.linkedin.com/messaging/
  click Compose button
  fill recipient search → select → fill message → send
  (Still blocked by Premium for 3rd+ recipients)
```

---

## WORKFLOW 6 — File upload (the hard part, now solved)

**Hidden file inputs don't appear in `take_snapshot`. Always use `search_dom` + `backendNodeId`.**

```
Step 1 — Find the hidden input
  search_dom(page, "input[type=file]")
  → returns: { backendNodeId: 28334, attributes: {accept: "...pdf...", class: "hidden"} }

Step 2 — Upload directly using backendNodeId as element ID
  upload_file(page, element=28334, files=["C:\\full\\path\\to\\resume.pdf"])
  → Returns: { fileCount: 1 } = SUCCESS

Step 3 — Trigger UI update (LinkedIn needs this)
  evaluate_script: setTimeout(()=>{
    // Find and click the Continue button after upload registers
    Array.from(document.querySelectorAll('button')).find(b=>/continue/i.test(b.textContent))?.click();
  }, 800); 'done'
```

**This works for**: LinkedIn Easy Apply, Snaphunt ATS, any ATS with hidden file inputs.
**Gmail attach**: Same pattern — `search_dom("input[name='Filedata']")` → `upload_file(backendNodeId)`.

---

## WORKFLOW 7 — External ATS apply (e.g. Snaphunt)

```
Step 1 — From LinkedIn job, click "Apply on company website"
  take_snapshot → find "Apply on company website" button
  click it → opens new tab (use list_pages to get new pageId)

Step 2 — Fill ATS form in one evaluate_script
  evaluate_script on new page:
    function setVal(sel,val){
      const el=document.querySelector(sel);
      if(!el) return;
      const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
      s.call(el,val);el.dispatchEvent(new Event('input',{bubbles:true}));
    }
    setVal('input[name="firstName"]','Prahalad');
    setVal('input[name="lastName"]','Reddy');
    setVal('input[name="email"]','prahaladreddy80@gmail.com');
    setVal('input[name="phone"]','9876543210');

Step 3 — Upload CV via search_dom + upload_file (same pattern as Workflow 6)

Step 4 — Submit
  take_snapshot → find Submit/Apply button → click
```

**Warning**: Clicking "Apply on company website" on LinkedIn marks the job as "In progress" even before ATS submission. Treat it as a real side effect.

---

## KEY TOOL DECISION MATRIX

| Task | Best tool | Avoid |
|------|-----------|-------|
| Navigate to URL | `navigate_page` | Click chains |
| Fill 1 field | `fill(element, text)` | evaluate_script for simple inputs |
| Fill 3+ text inputs | `evaluate_script` with shadow DOM + native setter | snapshot → fill loop |
| Fill `<select>` dropdown | `select_option(element, visibleText)` | evaluate_script setter (React won't register) |
| Typeahead/combobox | `fill(element, text)` → `click(suggestion)` | evaluate_script, select_option |
| Extract links/emails | `get_page_links` | get_page_content |
| Extract text | `evaluate_script(body.innerText.slice(0,5000))` | take_screenshot |
| Find hidden file input | `search_dom("input[type=file]")` | take_snapshot |
| Upload file | `upload_file(backendNodeId, files=[...])` | DOM click tricks |
| Click button by name | `evaluate_script` with textContent search | snapshot if ID known |
| Check page state | `evaluate_script` | take_screenshot |
| Open compose/new tab | `new_page(url, background=true)` | navigate existing tab |
| Fields inside LinkedIn modal | Shadow DOM traversal (see RULE 1) | `document.getElementById`, `document.querySelector` |

---

## ⛔ FINAL ENFORCEMENT — READ THIS BEFORE EVERY TOOL CALL

Ask yourself before each call:

**"Am I about to take_screenshot?"**
→ Did I already take one this turn? If yes: STOP. Use take_snapshot or evaluate_script instead.
→ Do I actually need to see a visual image? If no: STOP. Use take_snapshot.

**"Am I about to call fill()?"**
→ Are there 2+ more text fields on this same form step? If yes: STOP. Write one evaluate_script with native setter for all of them.

**"Am I about to take_snapshot?"**
→ Did I just click a Continue/Next button and already have a snapshot from before? If yes: STOP. You already know what's on the form — fill it.

**"Am I looping snapshot → action → snapshot → action?"**
→ If yes: STOP. Batch the actions. One snapshot, all fills, one click.

**Measured costs from a real run:**
- 1 extra take_screenshot → 60 seconds lost (BrowserOS timeout)
- 5 sequential fill() calls instead of 1 evaluate_script → 25 seconds lost
- Snapshot after every click → 30+ seconds lost across a 10-step form
- Total avoidable waste: ~115 seconds out of a 306-second run

**Target: complete Easy Apply in under 90 seconds, under 20 tool calls.**