---
order: 2
title: Chat
---

# Chat Interface

## The Chat Screen

| Area | Purpose |
|------|---------|
| **Left sidebar**  | Conversation history, new chat button, feature shortcuts |
| **Centre panel**  | Active conversation |
| **Top-right**     | Account menu — profile, password, logout |
| **Right sidebar** | Sources panel — can be opened once sources are generated |

---

## Managing Conversations

**Start a new conversation** — click <span class="ui-btn"><img src="/icons/chat.svg" class="icon-img" alt=""> New Chat</span> at the top of the left sidebar. Each conversation is isolated; context does not carry over between sessions.

**Rename a conversation** — double-click a conversation entry in the sidebar, type the new name, and press **Enter** to save.

**Delete a conversation** — hover over the conversation entry and click the <img src="/icons/bin.svg" class="icon-img" alt="delete"> icon that appears. Confirm the prompt to delete permanently.

> [!WARNING]
> Deleted conversations cannot be restored. Copy any content you need to keep before deleting.

---

## Two Types of Responses

**General AI response** — hestIA draws on its training data. No citations are shown. Use this for drafting, explaining, translating, or brainstorming tasks that do not require company-specific information.

**Collection-grounded response** — when your question matches passages in your organisation's indexed document collections, hestIA retrieves those passages and composes its answer from them. The response includes **inline citation badges** — click any badge to open the Sources panel.

> [!WARNING]
> hestIA may still produce inaccurate answers even when citing documents. Always verify important claims against the source passage shown in the Sources panel.

---

## Citation Chips

When hestIA draws on a document collection, it inserts **citation chips** directly into its response — small inline tags showing a truncated document or section name:


**Clicking a chip** opens an inline popup directly below it showing the retrieved passage. If the chip covers multiple passages (indicated by a **· +1** counter), use the pagination arrows inside the popup to step through them.

**The "X sources" button** at the bottom of a reply opens the full **Sources panel** on the right, listing all cited sources at once. Close it with the **×** button at the top of the panel.

---

## The Sources Panel

Each source card in the panel shows:

| Field | What it tells you |
|-------|------------------|
| **Document name** | The filename of the source (e.g. `3_POL_CodeConduct_v1.5`) |
| **Title** | The document's descriptive title (e.g. `Code of Conduct for data and IT users`) |
| **Header path** | The section hierarchy where the passage was found, e.g. `Organizational security › Username and passwords` |
| **Passage** | An excerpt of the retrieved text — click **show more** to expand the full passage |

> [!TIP]
> Use the **header path** to navigate directly to the right section in the source document — it tells you exactly where in a large file the passage was found, without having to search manually.

---

## Attaching Files

Click the <img src="/icons/plus-circle.svg" class="icon-img" alt="plus"> plus icon in the message input bar to attach a file or just drag-and-drop. The file is read within the current session only and is not permanently indexed.

<br>

**Supported formats:**
 
**PDF · DOCX · XLSX / XLSM · PPTX · TXT · CSV · JSON · Markdown**


<br>


---

## Tips for Better Answers

**Be specific.** Vague questions produce vague answers.

| Instead of… | Try… |
|-------------|------|
| What are the travel rules? | What is the reimbursement limit for business travel to Germany? |
| Summarise this policy. | Summarise the key obligations in section 3 of the data retention policy. |
| Is this allowed? | Is it permitted to use a personal laptop for processing client data under our BYOD policy? |

**Ask in the document language.** Retrieval works best when your question matches the language of the indexed documents. If your policy library is in French, ask in French.


**Rephrase if the answer is too vague.** Different wording retrieves different passages. Try synonyms or add more context if the first response is unsatisfying.

**Break complex tasks into steps.** Guide hestIA through a multi-step task one message at a time rather than asking for everything at once — each step benefits from the context built in the previous one.
