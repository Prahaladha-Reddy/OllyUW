# BrowserOS Playbook: Fast LinkedIn Post-Based Job Applications

Audience: automation agents using BrowserOS
Purpose: find job opportunities posted as LinkedIn feed posts and apply through the fastest valid path.

This is candidate-agnostic and post-agnostic. Treat candidate details, resume path, compensation, location, links, and templates as runtime inputs.

---

## Core Principle

The agent's job is not to click through forms manually. The agent's job is to classify the application path and use the fastest reliable BrowserOS tool pattern for that path.

Use BrowserOS as follows:

- `navigate_page` / `new_page`: jump directly to URLs.
- `take_snapshot`: get element IDs before clicking or filling.
- `evaluate_script`: extract text, classify pages, bulk-fill forms.
- `get_page_links`: extract emails, profiles, job links, forms, ATS links.
- `search_dom`: find hidden file inputs.
- `upload_file`: attach resume/CV to hidden file inputs.
- `click` / `fill`: only for small interactions or final confirmation.

Avoid repeated `snapshot -> fill -> snapshot -> fill` loops.

---

## Inputs Required

Before starting, the agent should have:

```text
candidate_name:
candidate_email:
candidate_phone:
candidate_location:
resume_path:
preferred_roles:
core_skills:
current_ctc:
expected_ctc:
notice_period:
portfolio_or_github:
preferred_locations:
```

If a field is unknown, use a truthful neutral value only when appropriate:

```text
Open to discuss
NA
Immediate / Open to discuss
```

Never invent credentials, experience, employers, compensation, or eligibility.

---

## Search Strategy

Search broad role terms first. Do not search for application mechanics like `email resume DM`.

Good queries:

```text
AI Engineer
Gen AI Engineer
LLM Engineer
Founding AI Engineer
Agentic AI Engineer
RAG Engineer
Machine Learning Engineer
Python AI Engineer
```

LinkedIn flow:

```text
1. navigate_page:
   https://www.linkedin.com/search/results/all/?keywords=ROLE_QUERY

2. take_snapshot

3. click "Posts"

4. inspect Top Match:
   evaluate_script(document.body.innerText.slice(0,12000))
   get_page_links(page)

5. inspect Latest:
   click Sort/Latest if available
   evaluate_script(document.body.innerText.slice(0,12000))
   get_page_links(page)
```

Why:

- Top Match often surfaces real hiring posts.
- Latest is fresher but noisier.
- Role-only search finds posts that would be missed by `"email resume"` style searches.

---

## Lead Classification

For each post, classify before acting.

Valid signals:

```text
hiring
we are hiring
open role
job opening
immediate hiring
apply here
send resume
share CV
DM me
View job
```

Application path types:

```text
email
google_form
external_ats
linkedin_easy_apply
linkedin_view_job
dm_or_connect
profile_mining_needed
skip
```

Skip when:

```text
candidate OpenToWork post
not a hiring post
advice/commentary/course/training
role mismatch
requires false screening answers
closed with no alternate application path
```

---

## Fast Extraction

Run these together whenever a search page or post page loads:

```text
get_page_links(page)
evaluate_script(document.body.innerText.slice(0,12000))
```

Extract structured signals:

```js
(function(){
  const text = document.body.innerText;
  return JSON.stringify({
    url: location.href,
    emails: [...new Set(text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/ig) || [])],
    phones: [...new Set(text.match(/(?:\+?\d[\d\s().-]{7,}\d)/g) || [])],
    chunks: text.split(/Feed post\n|About the job\n/).slice(1).map(x => x.slice(0,1800))
  }, null, 2);
})()
```

Use `get_page_links` for:

```text
mailto links
linkedin.com/jobs/view links
linkedin.com/in profile links
forms.gle / docs.google.com/forms links
company career links
ATS links
lnkd.in redirect links
```

---

## Decision Tree

```text
if email exists:
  use Email Workflow

else if Google Form exists:
  use Google Form Workflow

else if external ATS exists:
  use Generic Form/ATS Workflow

else if LinkedIn View Job exists:
  open job
  if Easy Apply and role fits:
    use Easy Apply workflow
  else:
    inspect job description for email/form/external link

else if post says DM:
  try Message
  if blocked by Premium/InMail:
    send connection request with note

else if recruiter/founder profile exists:
  open profile
  inspect Contact info and Activity for email/form/link
  fallback to connect note

else:
  skip and log reason
```

---

## Email Workflow

Fast path:

```text
1. new_page Gmail compose URL with to/subject/body prefilled.
2. search_dom("input[type=file]")
3. upload_file(backendNodeId, [resume_path])
4. take_snapshot
5. click Send
6. verify "Message sent"
```

Gmail compose URL:

```text
https://mail.google.com/mail/u/0/?view=cm&to=ENCODED_EMAIL&su=ENCODED_SUBJECT&body=ENCODED_BODY
```

Keep the email short:

```text
Hi NAME,

I saw your post for ROLE. I am interested in the opportunity.

Relevant background: SKILLS_SUMMARY.

I have attached my resume for your consideration.

Regards,
CANDIDATE_NAME
```

If the post requests fields, include exactly those fields.

---

## Google Form Workflow

Fast path:

```text
1. Open form.
2. Inspect once.
3. Bulk-fill all normal controls with one evaluate_script.
4. Click upload/add file.
5. search_dom("input[type=file]")
6. upload_file(backendNodeId, [resume_path])
7. take_snapshot to verify.
8. click Submit.
9. verify success text.
```

Google Forms usually structure each question as:

```text
[role="listitem"]
```

Controls:

```text
text inputs: input[type=text], textarea
radio: [role=radio]
checkbox: [role=checkbox]
dropdown: [role=listbox] then [role=option]
file: hidden input[type=file] after clicking upload button
```

Reusable bulk-fill skeleton:

```js
(function(){
  const data = {
    name: 'CANDIDATE_NAME',
    email: 'CANDIDATE_EMAIL',
    phone: 'CANDIDATE_PHONE',
    location: 'CANDIDATE_LOCATION',
    skills: 'CORE_SKILLS',
    notice: 'NOTICE_PERIOD',
    currentCtc: 'CURRENT_CTC',
    expectedCtc: 'EXPECTED_CTC'
  };

  const norm = s => (s||'').replace(/\s+/g,' ').trim().toLowerCase();
  const rows = [...document.querySelectorAll('[role="listitem"]')];
  const rowBy = label => rows.find(r => norm(r.innerText).includes(norm(label)));

  function setNative(el, val){
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(el, val);
    el.dispatchEvent(new Event('input', {bubbles:true}));
    el.dispatchEvent(new Event('change', {bubbles:true}));
  }

  function text(label, val){
    const r = rowBy(label); if(!r) return 'missing text: '+label;
    const el = r.querySelector('input[type="text"], input[type="email"], input[type="tel"], textarea');
    if(!el) return 'no text control: '+label;
    setNative(el, val);
    return 'filled text: '+label;
  }

  function choice(label, val, role){
    const r = rowBy(label); if(!r) return 'missing choice: '+label;
    const opts = [...r.querySelectorAll(`[role="${role}"]`)];
    const el = opts.find(o => norm(o.getAttribute('aria-label') || o.innerText || o.dataset.value).includes(norm(val)));
    if(!el) return 'missing option: '+label+'='+val;
    if(el.getAttribute('aria-checked') !== 'true') el.click();
    return 'selected '+role+': '+label+'='+val;
  }

  function dropdown(label, val){
    const r = rowBy(label); if(!r) return 'missing dropdown: '+label;
    const lb = r.querySelector('[role="listbox"]'); if(!lb) return 'no listbox: '+label;
    lb.click();
    const opts = [...document.querySelectorAll('[role="option"]')];
    const el = opts.find(o => norm(o.innerText || o.dataset.value).includes(norm(val)));
    if(!el) return 'missing dropdown option: '+label+'='+val;
    el.click();
    return 'selected dropdown: '+label+'='+val;
  }

  const out = [];
  out.push(text('name', data.name));
  out.push(text('email', data.email));
  out.push(text('phone', data.phone));
  out.push(text('location', data.location));
  out.push(text('skill', data.skills));
  out.push(text('notice', data.notice));
  out.push(text('current ctc', data.currentCtc));
  out.push(text('expected ctc', data.expectedCtc));

  return JSON.stringify(out, null, 2);
})()
```

Adapt labels and values per form. The script should report missing fields so the agent can decide whether to fill them manually or revise the label map.

Important:

- Prefer synchronous scripts. Async scripts may fail with promise collection errors.
- After bulk fill, verify once with `take_snapshot`.
- If the form has required custom questions, answer truthfully or stop.

---

## Generic ATS/Form Workflow

For non-Google forms:

```text
1. evaluate_script to inspect all inputs/selects/textareas/buttons.
2. Build a field map by label/name/placeholder.
3. Bulk-fill text fields with native setter.
4. Use BrowserOS select/click or script for dropdowns/radios.
5. search_dom("input[type=file]") and upload_file.
6. Verify required fields.
7. Submit.
```

Inspection script:

```js
(function(){
  return JSON.stringify([...document.querySelectorAll('input, textarea, select, button')].map((el,i)=>({
    i,
    tag: el.tagName,
    type: el.type,
    name: el.name,
    id: el.id,
    placeholder: el.placeholder,
    aria: el.getAttribute('aria-label'),
    text: el.innerText?.slice(0,80),
    value: el.value
  })), null, 2).slice(0,12000);
})()
```

Bulk text setter:

```js
function setInput(el, val){
  const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
  setter.call(el, val);
  el.dispatchEvent(new Event('input', {bubbles:true}));
  el.dispatchEvent(new Event('change', {bubbles:true}));
}
```

---

## LinkedIn View Job Workflow

When a post has `View job`:

```text
1. Open job.
2. Read top state:
   - Easy Apply
   - Apply on company website
   - No longer accepting applications
3. Read job description for hidden email/form/apply link.
4. Choose path:
   - Easy Apply if fit
   - external link/form if present
   - skip if closed and no alternate path
```

Do not stop at `No longer accepting applications`. Some posts still include active forms or emails in the description.

Skip when screening questions require false answers.

---

## LinkedIn DM / Connect Workflow

Use only when no email/form/apply link exists and post asks for DM.

```text
1. Open profile.
2. Click Message.
3. If composer opens: send concise role-specific message.
4. If Premium/InMail wall opens:
   - Dismiss
   - Click Connect/Invite
   - Add note
   - Send
```

Connection note:

```text
Hi NAME, saw your ROLE post. I have experience with RELEVANT_SKILLS. Would like to connect and share my resume.
```

Keep under 300 characters.

---

## Recruiter Profile Mining

Use when a post says `DM or email` but email is not visible.

```text
1. Open profile.
2. Click Contact info.
3. get_page_links + body text.
4. If no email, inspect Activity/recent posts.
5. Extract emails/forms from activity.
6. Use email/form if found, otherwise connect note.
```

---

## File Upload Pattern

Hidden file inputs rarely appear in `take_snapshot`.

Use:

```text
search_dom("input[type=file]")
upload_file(backendNodeId, [absolute_resume_path])
```

If no file input exists:

```text
click upload/add file button
search_dom("input[type=file]")
upload_file(...)
```

Always verify attachment appears before submitting.

---

## Verification

Every application must end with one of:

```text
Message sent
Your response has been recorded
Thank you for your interest
Application submitted
Submitted
Connection request sent
```

If no confirmation appears, log it as incomplete.

---

## Lead Log

Use this structure:

```text
date:
query:
post_url:
company:
role:
application_type:
target_url_or_email:
status:
confirmation:
skip_reason:
notes:
```

---

## Fast Agent Loop

```text
for role_query in preferred_roles:
  open LinkedIn role search
  click Posts
  inspect Top Match
  inspect Latest
  extract links + text

  for each candidate post:
    classify
    choose fastest path
    apply with path-specific workflow
    verify
    log result
```

The fastest paths, in order:

```text
email in post -> Gmail URL compose + upload_file
Google Form -> bulk evaluate_script + upload_file
external ATS -> bulk field map + upload_file
LinkedIn Easy Apply -> only if fit
DM/connect -> only when no direct application path exists
```

