# BrowserOS Field Notes

Date: 2026-06-01
Workspace: `C:\Users\bored\Documents\olive_assignment\browser_eval`

## Operating Rule

For real account actions, especially job applications, messages, email sends, profile edits, purchases, or bookings, the agent can research, navigate, draft, and prefill. It should stop before final submission or any irreversible account action and ask for explicit confirmation.

## Baseline From Local Files

- `tasks.json` contains WebVoyager-style browser tasks across search, GitHub, maps, flights, dictionary, recipes, Apple, arXiv, BBC, Hugging Face, and Wolfram Alpha.
- `subagent.py` uses BrowserOS MCP through a MiMo vision model. It converts MCP tools into OpenAI-style tool schemas and logs every tool call.
- Existing useful constraints in `subagent.py`:
  - Page IDs are the leading numbers from `list_pages`, not browser tab IDs.
  - Screenshots are expensive and capped at 3 per task.
  - `take_snapshot` and `get_page_content` should be preferred when text structure is enough.
  - BrowserOS appends extra context to tool output; stripping it keeps model context cleaner.

## Live Technique Log

### 2026-06-01 12:00 IST - Setup

- Scope corrected to only `browser_eval`; ignore the rest of `olive_assignment`.
- Created this notes file as the running log for techniques, failures, and improvements.
- Initial hypothesis: fastest workflow is not pure visual browsing. Use:
  1. `new_page` or `navigate_page` to reach the target directly.
  2. `take_snapshot` for interactive element IDs.
  3. `get_page_content` or `get_page_links` for extraction-heavy pages.
  4. `evaluate_script` only when BrowserOS element snapshots miss hidden state or page metadata.
  5. Ask user before final submit/send/apply actions.

### 2026-06-01 12:05 IST - Google Sample Task

Task: Find the initial release date for `Guardians of the Galaxy Vol. 3`.

What worked:

- Direct Google search URL was fastest:
  `https://www.google.com/search?q=Guardians+of+the+Galaxy+Vol.+3+initial+release+date`
- `take_snapshot` showed result structure and confirmed the page loaded.
- `evaluate_script` with `document.body.innerText.slice(0, 3000)` extracted the answer immediately.

Answer found:

- Google result text says the movie premiered at Disneyland Paris on April 22, 2023 and was released in U.S. theaters on May 5, 2023.

Technique note:

- For search-answer tasks, avoid clicking result pages first. Direct search plus body text extraction is usually enough.
- `get_page_content` can write large output to a temp file, which is less convenient for quick iteration. `evaluate_script(document.body.innerText...)` is faster when the answer is visible in rendered text.

### 2026-06-01 12:12 IST - Naukri Job Discovery Flow

Task: Use Google/Naukri to find AI agent jobs, especially remote roles.

What worked:

- Google search with `site:naukri.com AI agent engineer remote India Naukri` quickly surfaced the right Naukri URL patterns.
- `get_page_links` on Google results returned clean direct links, including:
  - `https://www.naukri.com/ai-agent-jobs`
  - `https://www.naukri.com/ai-agent-jobs-in-remote`
  - individual `job-listings-*` URLs.
- Direct URL `https://www.naukri.com/ai-agent-jobs-in-remote` was better than trying to click the Remote checkbox on the generic listing page.
- `evaluate_script(document.body.innerText.slice(...))` extracted structured listing text cleanly.
- Clicking the job card sometimes needs the larger clickable container, not only the title link. On Naukri, clicking the text title once did nothing; clicking the enclosing clickable result opened the job in a new page.
- `Continue with Google` on the job detail page moved past the login gate and exposed logged-in controls.

Useful Naukri observations:

- Remote AI agent listing page showed `1 - 20 of 130`.
- Example listing opened: `AI Agent Engineer`, `COGNIFYR.CO`, `3 - 8 years`, `Remote`, `100+ applicants`, posted `3+ weeks ago`.
- Full job detail was extractable as text. Must-have requirements included Python, LLM prompting, LangChain/LangGraph/CrewAI/AutoGen, RAG, vector databases, and agent frameworks.
- Logged-in controls appeared: `Save` and `Apply on company site`.

Safety/side-effect rule confirmed:

- Stop before `Apply on company site`, `Save`, recruiter messages, or application submission unless the user explicitly confirms that exact action.

Better technique replacing earlier idea:

- Earlier idea: click filters manually on the page.
- Better technique: infer and navigate direct Naukri URL patterns such as `*-jobs-in-remote`, then extract body text. Reason: filters are clickable but not always stateful in snapshots, and direct URLs are faster and more reliable.

### 2026-06-01 12:25 IST - LinkedIn Job Discovery and Easy Apply Boundary

Task: Find remote AI agent / ML jobs on LinkedIn and test how far automation can safely go.

What worked:

- Direct LinkedIn search URL:
  `https://www.linkedin.com/jobs/search/?keywords=AI%20Agent%20Engineer&location=India&f_WT=2`
- `f_WT=2` applies the Remote work-type filter.
- `evaluate_script(document.body.innerText.slice(...))` gave a quick summary of search results:
  - `AI Automation Engineer (Remote)` - Hire Feed - India Remote
  - `AI/ML Engineer (Python-based) (Freelancer)` - Deccan AI Experts - India Remote
  - `Machine Learning Engineer | Remote` - Crossing Hurdles - APJ Remote - `$30/hr - $100/hr` - Easy Apply
  - `Software Engineer - Remote (AI)` - Generative Futures - Easy Apply
  - `AI Prompt Engineer II` - Pearl - Easy Apply
  - `Generative AI Engineer` - Firstsource - Easy Apply
- `get_page_links` on the LinkedIn search page returned direct `jobs/view/{id}` links, which is better than relying on the split-pane detail view.
- Opening `https://www.linkedin.com/jobs/view/4418247644/` produced a stable standalone job page.

LinkedIn Easy Apply boundary:

- Clicking `Easy Apply` immediately opened a modal with prefilled first name, last name, phone country code, phone number, and email.
- This is useful for mapping the flow, but it is also a high-side-effect zone.
- Stop at the first Easy Apply modal unless the user explicitly confirms continuing.
- If the modal is opened only for inspection, close it with `Dismiss`, then choose `Discard`, not `Save`.

LinkedIn quirks:

- BrowserOS `scroll` timed out on one LinkedIn detail page with a CDP `Input.dispatchMouseEvent` timeout.
- The standalone job page had limited scroll height at first; direct job links were more stable than the search split pane.
- A click intended for `Show more` navigated to the company jobs page. For LinkedIn, prefer extracting from text and direct URLs before clicking ambiguous inline controls.

Better technique replacing earlier idea:

- Earlier idea: use LinkedIn split-pane search results and click visible cards.
- Better technique: use `get_page_links` to collect stable `jobs/view/{id}` URLs, open standalone pages, then inspect. Reason: split panes and inline details mutate element IDs and can lose detail context.

### 2026-06-01 12:35 IST - Cambridge Dictionary Sample

Task: Find pronunciation, definition, and example for `serendipity`.

What worked:

- Direct URL:
  `https://dictionary.cambridge.org/dictionary/english/serendipity`
- `take_snapshot` showed pronunciation audio buttons and page structure.
- `evaluate_script(document.body.innerText.slice(0, 2500))` extracted definition and examples cleanly.

Answer found:

- UK pronunciation was available on the page; ASCII approximation: `ser-uhn-DIP-uh-tee`.
- US pronunciation was available on the page; ASCII approximation: `ser-uhn-DIP-uh-tee`.
- Definition: finding interesting or valuable things by chance.
- Example: `There is a real element of serendipity in archaeology.`

Technique note:

- Dictionary/reference pages are ideal for direct canonical URLs plus rendered text extraction.
- Cookie/privacy overlays may appear in snapshot, but text extraction still worked without accepting cookies.

## Current Best Workflow

1. Start with a direct URL or construct a likely canonical search URL.
2. Run `take_snapshot` once to verify page state and capture interactive IDs.
3. Use `evaluate_script(document.body.innerText.slice(...))` for fast extraction.
4. Use `get_page_links` when search results or job boards contain many links.
5. Prefer opening stable direct detail URLs instead of clicking through dynamic result panes.
6. Use screenshots only when text extraction cannot reveal visual state.
7. For account workflows, define the stopping point before acting:
   - OK: search, inspect, extract, draft, prefill if reversible.
   - Stop: apply, save, send, message, follow, subscribe, buy, book, profile edit, or any final confirmation.

### 2026-06-01 12:50 IST - Gmail Real Compose Flow

Task: Use the logged-in Gmail account to test a real compose workflow without sending.

What worked:

- Active Gmail page was `https://mail.google.com/mail/u/0/#inbox?compose=new`.
- `take_snapshot` eventually exposed the compose dialog fields:
  - `To recipients` combobox
  - `Subject` textbox
  - `Message Body` textbox
  - `Send` button
  - `Attach files` button
  - `Discard draft` button
- Filling `To recipients`, pressing `Enter`, then filling subject and body worked.
- Gmail autosaved the draft immediately; the Drafts count increased.
- Cleanup worked by clicking `Discard draft`; Drafts count returned to its previous value and Gmail showed an `Undo` link.

Safety boundary:

- Do not click `Send`, `Ctrl+Enter`, scheduled send, confidential mode save, or any external recipient action without explicit confirmation.
- Draft creation itself is a real account side effect. If a draft is created only for practice, discard it before moving on unless the user asks to keep it.

Attachment experiment:

- `search_dom` found hidden Gmail inputs matching `input[type=file]`, including one with `name="Filedata"`.
- Attempting `upload_file` with the `search_dom` node id failed: BrowserOS reported that the node was not a file input element.
- Clicking Gmail's visible paperclip did not expose a usable file input element in the snapshot.

Technique note:

- For Gmail compose, snapshot IDs are reliable for text fields and buttons, but attachment is not solved by `search_dom` alone.
- Better next approach for attachments: use sites whose file inputs appear directly in the accessibility snapshot, or find a BrowserOS-specific way to map DOM nodes to upload targets. Do not assume a DOM `nodeId` can be passed as an element id.

### 2026-06-01 12:55 IST - Google Flights Booking-Style Flow

Task: Inspect a real flight search / booking-style site without booking.

What worked:

- `https://www.google.com/travel/flights` opened logged into the Google account and used India/INR defaults.
- Snapshot exposed high-level flight controls:
  - trip type
  - passenger count
  - seating class
  - origin
  - destination
  - departure and return dates
- Google Flights immediately surfaced real suggested routes from Hyderabad, including Hyderabad to Bengaluru from `₹8,672`, operated by IndiGo, Jun 4 to Jun 10, nonstop.

What did not work cleanly:

- The origin/destination controls are ARIA comboboxes, but simple `fill` + `Enter` did not change their visible state.
- Clicking a suggested flight button did not navigate in the observed state.

Technique note:

- Google Flights is good for extracting travel options and prices from rendered text, but its core search widgets are not plain text inputs.
- For booking-style automation, define the stop boundary before opening partner/airline checkout. Search and compare are safe; booking, payment, passenger identity submission, and price tracking are side effects.

### 2026-06-01 12:58 IST - X.com Login Boundary

Task: Check whether X.com DM automation can start from current browser state.

Result:

- `https://x.com/messages` redirected to the login/onboarding flow.
- Snapshot exposed `Continue with phone`, `Continue with Apple`, and `Email or username`.
- No logged-in session was available in BrowserOS for X.com.

Technique note:

- X.com cannot be meaningfully automated for DMs/posts until login is complete.
- Do not create or change account credentials during an automation run. Pause at login unless the user provides the needed credentials or completes it manually.

### 2026-06-01 13:00 IST - LinkedIn Messaging Flow

Task: Inspect real LinkedIn messaging and DM compose without sending.

What worked:

- `https://www.linkedin.com/messaging/` opened logged in.
- Snapshot exposed:
  - message search
  - conversation list
  - compose new message
  - recipient combobox
  - suggested recipients
  - message textbox
  - image/file attach buttons
  - disabled Send button
- BrowserOS `click` on the compose button did not visibly change state on first tries, but a JS click through `evaluate_script` opened the new-message compose route.

Safety boundary:

- No recipient was selected because the user did not name one.
- The Send button stayed disabled without a recipient, which makes no-recipient compose a useful low-risk way to map the UI.
- Do not select a real recipient or send a DM without explicit instruction naming the recipient and message.

Technique note:

- LinkedIn messaging snapshots are much cleaner than Gmail for discovering social-message controls.
- If a normal click reports success but state does not change, `evaluate_script` can trigger a direct button click. Verify immediately with a new snapshot.

### 2026-06-01 13:03 IST - Connector vs Browser Login

Task: Compare live browser login with BrowserOS connected-app API actions.

What worked:

- `get_category_actions` showed useful connector actions:
  - Gmail: draft, send, read, search, modify, delete, attachments, contacts
  - LinkedIn: get profile info, create post, format post, share URL
  - Google Drive: file tree, shared drive, trash
  - Google Calendar: create, list, update, delete events and attendees
- `get_action_details` is useful before execution. It showed that `gmail_draft_email` requires `to`, `subject`, and `body`, and that `linkedin_get_profile_info` is read-only.

Important finding:

- Browser login and connector OAuth are separate.
- The browser was logged into LinkedIn, but `execute_action` for `linkedin_get_profile_info` returned `401 Unauthorized`.
- `handle_auth_failure` returned an OAuth authorization URL for the LinkedIn connector.

Safety rule:

- Do not complete connector OAuth grants without explicit user approval. OAuth grants can give broad API access even if the browser UI is already logged in.
- Connector write actions are faster than UI automation but riskier because they bypass final-review screens.

### 2026-06-01 13:08 IST - Real Download / Save Flow

Task: Download or save a real PDF from arXiv.

What worked:

- `https://arxiv.org/abs/1706.03762` exposed `View PDF`, `HTML`, `TeX Source`, citation links, and author links in the snapshot.
- `download_file` on the `View PDF` link timed out after 60 seconds.
- Directly opening `https://arxiv.org/pdf/1706.03762` and then using `save_pdf` succeeded.
- Saved file:
  `C:\Users\bored\Documents\olive_assignment\browser_eval\downloads\attention_is_all_you_need_browseros_saved.pdf`

Technique note:

- For PDFs, `download_file` is not always the best path. It may wait for a browser download event that never fires when the site renders the PDF inline.
- Better technique: navigate directly to the PDF URL and call `save_pdf`.
- Verify filesystem results with a shell `Get-ChildItem` check after saving.
