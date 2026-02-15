# User Story 1
As a user, I want to see which emails require immediate attention so that I do not miss important messages.

Explanation: This focuses on prioritization rather than full inbox processing.

T-shirt size: Medium

Sprint fit: Can be delivered as a basic priority flagging feature.

---

## Table of contents
- [Header](#header)
- [Architecture Diagram](#architecture-diagram)
- [Class Diagram](#class-diagram)
- [List of Classes](#list-of-classes)
- [State Diagrams](#state-diagrams)
- [Flow Chart](#flow-chart)
- [Development Risks and Failures](#development-risks-and-failures)
- [Technology Stack](#technology-stack)
- [APIs](#apis)
- [Public Interfaces](#public-interfaces)
- [Data Schemas](#data-schemas)
- [Security and Privacy](#security-and-privacy)
- [Risks to Completion](#risks-to-completion)

---
# Header
## Feature Name
Immediate-Attention Email Flagging

## One-Sentence Summary
Identify and visually flag emails that likely require immediate attention so users don’t miss important messages.

## Problem Statement
Users receive more email than they can triage in real time. Important messages (e.g., time-sensitive requests, urgent items, messages from key senders) can be buried, increasing response latency and the chance of missed deadlines.

## Goals
- Provide a priority indicator for messages that likely require immediate attention.
- Keep prioritization fast (near-instant display) and explainable (user can understand why something was flagged at a high level).
- Support an MVP delivery: basic signals and minimal configuration.

## Non-Goals (MVP)
- Full inbox smart sorting or automatic filing into folders.
- Drafting responses, summarizing threads, or performing complex email actions.
- Perfect classification accuracy; the system should be helpful, not authoritative.
- Replacing user-defined rules (e.g., Outlook rules); this feature complements them.

## Users & Primary Use Case
- Primary user: A person managing a busy inbox who wants a quick way to notice urgent items.
- Primary flow: User views inbox → system highlights likely-urgent emails → user opens/acts on flagged items first.

## Definitions & Terminology
- Email/Message: A single received email item.
- Priority Flag: A boolean or tiered indicator (e.g., High/Normal) shown in the UI.
- Immediate Attention: A message that is time-sensitive and/or high-importance based on signals (sender, keywords, deadlines, explicit importance markers, etc.).
- Signals: Inputs used to compute priority (headers, metadata, content tokens, user preferences).

## Assumptions
- Emails are accessible via an API or local data source with at least: sender, subject, timestamp, and body/preview.
- MVP can start with lightweight heuristics; ML-based scoring can be a later enhancement.
- The UI can display a small badge/icon/label without redesigning the entire inbox.

## Success Criteria
- Users can quickly identify which messages are flagged as needing attention.
- The prioritization logic runs reliably and does not noticeably slow down inbox rendering.
- Basic explainability is present (e.g., “flagged because: from VIP sender” or “contains urgent keyword”).
## Rationale
I think this generated Header is reasonable. The user story only requires managing the importance of emails, and full automation is not needed for now. The AI-generated Assumptions and Success Criteria also fairly meet my requirements.
## Chat Log
User: According to this content, you need to generate one section at a time, and I will tell you which section to generate, following the framework I provide. If in some parts you think there are multiple possible implementation approaches, you should include all of them and clearly describe their characteristics so that I can make a choice. The entire document should be fully written in Markdown, and for diagrams, you should use Mermaid.js.
LLM:
generate Header

I’m going to fill in the Header section in your spec (directly in the Markdown file), focusing on the user story’s goal—flagging emails that need immediate attention—plus scope, assumptions, and key definitions.

Edited
dev_spec_doc1.md+40-0
Updated the Header section in dev_spec_doc1.md with:

Feature name + one-sentence summary
Problem statement, goals, and MVP non-goals
Users/use case, terminology, assumptions
Success criteria
Tell me the next section you want generated (e.g., “Architecture Diagram”).

User: You should maintain my structure! Use section as the main heading, and everything else of yours should be considered a subsection.

LLM:
Got it — I’ll keep your existing top-level section headings (like # Header) unchanged, and put all my added content as ##/### subsections underneath them. I’m going to re-check the current file contents (since you undid), then re-insert the Header content in the correct structure.

Read dev_spec_doc1.md

Next I’ll add ## subsections under # Header only, without changing any other section headings.

Generating patch (61 lines) in dev_spec_doc1.md

Edited
dev_spec_doc1.md+40-0
Applied your structure rule in dev_spec_doc1.md:

Kept # Header as the main heading.
Added everything under it as ## subsections (no new # headings).
Which section should I generate next (e.g., Architecture Diagram)?
# Architecture Diagram
## Overview
This section shows where each component runs (client/server/cloud) and what data flows between them to produce an “Immediate Attention” flag and a short explanation.

## Selected Architecture
### Standalone Web App + Backend Scoring Service (cloud-assisted)
**Where it runs**
- **Client:** Standalone web app (browser) for inbox/triage UI.
- **Cloud:** Microsoft Identity Platform (Entra ID) for OAuth; Microsoft Graph for email access.
- **Server/Cloud:** Scoring API for priority evaluation and explainability.
- **External cloud:** LLM provider API used by the scoring API.
- **Optional storage:** Minimal user preferences (VIP list, keywords) and caching (message IDs → priorityFlag + reasons).

**Mermaid diagram**
```mermaid
flowchart LR
	subgraph Client
		Client_T[Client Web App Browser]
		UI[Inbox UI Badge Label]
		Web[OutlookPlus Web UI]
	end

	subgraph CloudMS
		CloudMS_T[Cloud Microsoft 365]
		IdP[Entra ID]
		Graph[Microsoft Graph API]
	end

	subgraph Server
		Server_T[Server OutlookPlus Services]
		ScoreAPI[Scoring API]
		Prefs[User Preferences Store]
		Cache[Score Cache]
	end

	subgraph LLMCloud
		LLMCloud_T[Cloud LLM Provider]
		LLM[LLM API]
	end

	UI <--> Web

	Web --> IdP
	IdP --> Web

	Web --> Graph
	Graph --> Web

	Web --> ScoreAPI
	ScoreAPI --> Prefs
	ScoreAPI --> Cache
	ScoreAPI --> LLM
	LLM --> ScoreAPI
	ScoreAPI --> Web

	Web --> UI
```

**Information flows**
- **Web app → Graph:** message retrieval (at minimum: sender, subject, received timestamp, importance header, and the email body main text).
- **Web app → Scoring API:** message metadata (e.g., `from`, `subject`, `receivedAt`, `importance`) plus the **email body main text** (`bodyText`) for scoring.
- **Scoring API → LLM provider:** prompt containing system instructions + a required output schema + extracted features + email body main text (and optionally user preferences).
- **LLM provider → Scoring API:** schema-conformant JSON decision output (e.g., `priorityFlag` and `reasons[]`) which is then validated server-side.
- **Scoring API → Web app:** `priorityFlag` (High/Normal) and `reasons[]` (e.g., “From VIP sender”, “Contains ‘ASAP’”, “Meeting within 24h”).
- **Prefs/Cache:** store only what’s required for MVP (e.g., VIP senders list, user keywords, and cached scoring results keyed by `(apiKey, messageId)` or an equivalent server-known namespace).

**Characteristics**
- Pros: Centralized logic, consistent behavior across devices, strong semantic understanding via LLM, easier to iterate prompts/model choice later.
- Cons: More moving parts; privacy concerns because the email main text is sent to the backend/LLM; LLM cost + latency; must handle unreliable outputs (require structured responses + validation).

## API Data Contract (MVP, Explicit)
### Score Request (Web → Backend)
Required fields:
- `messageId`
- `from`
- `subject`
- `receivedAt`
- `importance`
- `bodyText` (full email main text)

### Score Response (Backend → Web)
Required fields:
- `messageId`
- `priorityFlag` (exactly one of: `High`, `Normal`)
- `reasons` (array of 1–3 short strings)

Optional fields (only when debug/telemetry is enabled; web UI must not depend on them):
None (MVP returns only the required fields).

### Backend Response Example (MVP)
```json
{
	"messageId": "AAMkAGI2T...",
	"priorityFlag": "High",
	"reasons": [
		"Mentions a deadline (tomorrow)",
		"Asks for a reply"
	]
}
```
## Rationale
The LLM provides several options: one is as an Outlook add-in, another is completely local. However, Icannot be certain about Outlook’s openness, and as an add-in it may be subject to Outlook’s permission restrictions. A fully local development approach would require spending excessive effort on relatively less important aspects. Therefore, I explicitly told the LLM that Iwill use a web app as the frontend and a backend for computation. LLM also believes that sending the email content to us raises privacy concerns, but Imust assess the importance based on the email content itself. Therefore, I requested LLM that Iwill use the full text.
## Chat log
User:You’re set on using the backend, so I’ll tighten the wording in the “Minimal Data Contract” to make it backend-specific (no more “if used” / “or compute”).

LLM: Updated the wording to match your decision to use a backend in dev_spec_doc1.md.

“The UI should receive (or compute)” → now explicitly “web UI should receive from the backend”
“If a backend is used…” → now stated as a requirement (features-first, optional short preview snippet)
Tell me the next section to generate: “Class Diagram”?

User:I will use the main text

LLM:I’ll update the Architecture Diagram wording/flows to reflect that the backend scoring will use the email’s main body text (not just a preview snippet), and I’ll tighten the privacy note accordingly.

Updated the selected “Web + Backend” architecture to use the email main body text.

Mermaid diagram now labels Graph returning body (main text) and the scoring request as metadata + main text in dev_spec_doc1.md.
Information flows now state the backend receives the email body main text (not a preview snippet).
Privacy note now reflects sending main text (minimize, truncate, no attachments).

# Class Diagram
## Scope
This class diagram focuses on the MVP components needed for: (1) fetching email content in the web UI, (2) sending a scoring request to the backend, and (3) returning a priority flag plus human-readable reasons.

## Layered (Controller → Service → Stores)
**Characteristics**
- Clear separation of concerns, easy to implement quickly.
- Works well with a REST backend and LLM-based scoring.
- Easy to add caching and preference persistence.

```mermaid
classDiagram
	direction LR

	class InboxPage {
		+renderEmailList()
		+showPriorityBadge(messageId)
	}

	class WebAuthService {
		+signIn()
		+getAccessToken(): string
	}

	class GraphEmailService {
		+listInboxMessages(): EmailMessage[]
		+getMessageBody(messageId): string
	}

	class GraphApiClient {
		+get(path, token): any
	}
	<<external>> GraphApiClient

	class ScoringApiClient {
		+scoreEmail(req: ScoreRequest): ScoreResponse
	}

	class ScoringController {
		+POST /api/score(req): ScoreResponse
	}

	class ScoringService {
		+score(req: ScoreRequest): ScoreResponse
	}

	class FeatureExtractor {
		+extract(req: ScoreRequest): FeatureVector
	}

	class PromptBuilder {
		+build(features: FeatureVector, bodyText: string, prefs: UserPreferences): LlmPrompt
	}

	class LlmClient {
		+complete(prompt: LlmPrompt): LlmResult
	}

	class LlmProviderApi {
		+chatCompletions(request): any
	}
	<<external>> LlmProviderApi

	class LlmResponseParser {
		+parse(result: LlmResult): PriorityDecision
	}

	class OutputValidator {
		+validate(decision: PriorityDecision): bool
		+fallback(): PriorityDecision
	}

	class PreferencesRepository {
		+getUserPrefs(userId): UserPreferences
	}

	class ScoreCache {
		+get(cacheKey): ScoreResponse?
		+set(cacheKey, resp: ScoreResponse, ttlSec)
	}

	class EmailMessage {
		+id: string
		+from: string
		+subject: string
		+receivedAt: string
		+importance: string
		+bodyText: string
	}

	class ScoreRequest {
		+messageId: string
		+from: string
		+subject: string
		+receivedAt: string
		+importance: string
		+bodyText: string
	}

	class ScoreResponse {
		+messageId: string
		+priorityFlag: string
		+reasons: string[]
	}

	class PriorityDecision {
		+priorityFlag: string
		+reasons: string[]
	}

	class LlmPrompt {
		+system: string
		+user: string
		+schema: string
	}

	class LlmResult {
		+rawText: string
		+rawJson: any
	}

	class FeatureVector {
		+isFromVip: bool
		+hasUrgentKeywords: bool
		+mentionsDeadline: bool
		+isHighImportance: bool
	}

	class UserPreferences {
		+vipSenders: string[]
		+urgentKeywords: string[]
	}

	InboxPage --> WebAuthService : uses
	InboxPage --> GraphEmailService : loads emails
	GraphEmailService --> GraphApiClient : calls
	InboxPage --> ScoringApiClient : requests scores

	ScoringApiClient --> ScoringController : HTTP
	ScoringController --> ScoringService : delegates
	ScoringService --> ScoreCache : cache
	ScoringService --> PreferencesRepository : prefs
	ScoringService --> FeatureExtractor : features
	ScoringService --> PromptBuilder : prompt
	ScoringService --> LlmClient : LLM call
	LlmClient --> LlmProviderApi : calls
	ScoringService --> LlmResponseParser : parse
	ScoringService --> OutputValidator : validate

	GraphEmailService ..> EmailMessage : returns
	ScoringApiClient ..> ScoreRequest : sends
	ScoringApiClient ..> ScoreResponse : receives
	FeatureExtractor ..> FeatureVector : produces
	PreferencesRepository ..> UserPreferences : returns
```
## Notes
- The DTOs shown here (`ScoreRequest`, `ScoreResponse`) are the source of truth and must match the later `# APIs` and `# Data Schemas` sections.

### LLM Flow (end-to-end)
- `GraphEmailService` fetches the email body main text.
- `ScoringService` runs `FeatureExtractor`, then `PromptBuilder`.
- `LlmClient` calls `LlmProviderApi` and returns `LlmResult`.
- `LlmResponseParser` converts the raw model output into a `PriorityDecision`.
- `OutputValidator` enforces constraints (e.g., required fields present, `reasons[]` length 1–3); if validation fails it returns `fallback()`.
## Rationale
LLM gave me two options: one is the standard layered approach, and the other is a processing-centric approach that treats filters and the LLM as core components. Ichose the first, conventional method, as it aligns better with normal development workflows and practices and is easier to implement.
## Chat Log
User:now ,generate Class Diagram

LLM:I’ll inspect the current area around # Class Diagram, then I’ll insert a Mermaid classDiagram (with two implementation-style options) directly under that heading without touching other sections.

User:Generated the Class Diagram section in dev_spec_doc1.md under # Class Diagram.

LLM:Added two Mermaid classDiagram options:
Layered (Controller → Service → Stores) for a fast MVP
Domain-centric (Policy/Rule objects) for extensibility
Included short characteristics + notes so you can pick the structure that matches how you want to implement.
Say “generate List of Classes” next and I’ll turn the chosen diagram into a concrete class list (with responsibilities/fields/methods).
# List of Classes

## Overview
This section enumerates the core classes shown in the selected layered design and describes what each class does, where it runs (web vs backend), and its main methods/data.

## Web (Client) Classes

### InboxPage (Web UI)
- **Responsibility:** Render the inbox/triage UI and display the priority badge + short reasons returned by the backend.
- **Key methods:** `renderEmailList()`, `showPriorityBadge(messageId)`
- **Collaborators:** `WebAuthService`, `GraphEmailService`, `ScoringApiClient`

### WebAuthService (Web UI)
- **Responsibility:** Handle user sign-in and token acquisition for Microsoft Graph.
- **Key methods:** `signIn()`, `getAccessToken(): string`
- **Key data:** access token (and session state depending on auth approach).

### GraphEmailService (Web UI)
- **Responsibility:** Fetch inbox message metadata and email body main text from Microsoft Graph.
- **Key methods:** `listInboxMessages(): EmailMessage[]`, `getMessageBody(messageId): string`
- **Collaborators:** `GraphApiClient`

### GraphApiClient (External wrapper used by Web UI)
- **Responsibility:** Thin wrapper around Microsoft Graph HTTP calls.
- **Key methods:** `get(path, token): any`
- **Notes:** Integration boundary for rate limiting/429 handling and retries.

### ScoringApiClient (Web UI)
- **Responsibility:** Call the backend scoring endpoint and return a `ScoreResponse`.
- **Key methods:** `scoreEmail(req: ScoreRequest): ScoreResponse`
- **Notes:** Should attach a client-generated correlation ID when possible.

## Backend (Server) Classes

### ScoringController (Backend)
- **Responsibility:** HTTP entrypoint for scoring requests (e.g., `POST /api/score`). Validates request shape, authenticates/authorizes, and delegates to `ScoringService`.
- **Key methods:** `POST /api/score(req): ScoreResponse`

### ScoringService (Backend)
- **Responsibility:** Orchestrate caching, preference lookup, feature extraction, LLM prompting, response parsing, validation, and final response shaping.
- **Key methods:** `score(req: ScoreRequest): ScoreResponse`
- **Typical flow:**
	1) Cache check (`ScoreCache`) → 2) prefs (`PreferencesRepository`) → 3) features (`FeatureExtractor`) → 4) prompt (`PromptBuilder`) → 5) LLM call (`LlmClient`) → 6) parse (`LlmResponseParser`) → 7) validate/fallback (`OutputValidator`) → 8) cache + return.

### FeatureExtractor (Backend)
- **Responsibility:** Convert `ScoreRequest` into a compact `FeatureVector` used to guide the LLM.
- **Key methods:** `extract(req: ScoreRequest): FeatureVector`

### PromptBuilder (Backend)
- **Responsibility:** Build an LLM prompt containing (a) system instructions, (b) required JSON output schema/format, (c) extracted features, and (d) the email body main text.
- **Key methods:** `build(features: FeatureVector, bodyText: string, prefs: UserPreferences): LlmPrompt`

### LlmClient (Backend)
- **Responsibility:** Execute the LLM provider request (timeouts/retries as appropriate) and return an `LlmResult` plus provider metadata.
- **Key methods:** `complete(prompt: LlmPrompt): LlmResult`
- **Collaborators:** `LlmProviderApi`

### LlmProviderApi (External integration used by Backend)
- **Responsibility:** Provider-specific API surface (e.g., chat-completions endpoint).
- **Key methods:** `chatCompletions(request): any`

### LlmResponseParser (Backend)
- **Responsibility:** Convert raw model output into a normalized `PriorityDecision`.
- **Key methods:** `parse(result: LlmResult): PriorityDecision`

### OutputValidator (Backend)
- **Responsibility:** Enforce constraints (required fields, allowed values, length limits) and return a safe fallback when the model output is invalid.
- **Key methods:** `validate(decision: PriorityDecision): bool`, `fallback(): PriorityDecision`

### PreferencesRepository (Backend)
- **Responsibility:** Load per-user preferences used for scoring guidance.
- **Key methods:** `getUserPrefs(userId): UserPreferences`

### ScoreCache (Backend)
- **Responsibility:** Cache scoring results to reduce LLM calls and improve latency.
- **Key methods:** `get(cacheKey): ScoreResponse?`, `set(cacheKey, resp: ScoreResponse, ttlSec)`

## Shared Data / DTO Classes

### EmailMessage (DTO)
- **Responsibility:** Canonical message representation used in the web UI.
- **Key fields:** `id`, `from`, `subject`, `receivedAt`, `importance`, `bodyText`

### ScoreRequest (DTO)
- **Responsibility:** Request payload sent from web UI to backend.
- **Key fields (MVP):** `messageId`, `from`, `subject`, `receivedAt`, `importance`, `bodyText`

### ScoreResponse (DTO)
- **Responsibility:** Response payload returned from backend to web UI.
- **Required fields (MVP):** `messageId`, `priorityFlag`, `reasons[]`


### FeatureVector (DTO)
- **Responsibility:** Compact feature summary used as LLM context.
- **Key fields:** `isFromVip`, `hasUrgentKeywords`, `mentionsDeadline`, `isHighImportance`

### UserPreferences (DTO)
- **Responsibility:** User-configurable inputs that influence scoring.
- **Key fields:** `vipSenders[]`, `urgentKeywords[]`

### LlmPrompt (DTO)
- **Responsibility:** Provider-agnostic prompt container.
- **Key fields:** `system`, `user`, `schema`

### LlmResult (DTO)
- **Responsibility:** Provider-agnostic raw model output.
- **Key fields:** `rawText`, `rawJson`

### PriorityDecision (Domain DTO)
- **Responsibility:** Internal normalized decision produced by parsing/validation.
- **Key fields:** `priorityFlag`, `reasons[]`
## Rationale
I think these arrangements are reasonable: the frontend and backend are separated, and some data is shared, which meets my requirements.
## Chat Log

User:generate # List of Classes
LLM:
I’ll add a clear, implementation-oriented class catalog under # List of Classes, based on your chosen layered + LLM backend design, and insert it before # State Diagrams without changing any other sections.

I’m going to re-read the exact lines around # List of Classes so I can apply the patch with the correct context (looks like the file changed slightly).

Added the complete “List of Classes” section under dev_spec_doc1.md right below # List of Classes.

Clearly separated Web (client) vs Backend (server) classes
For each class: responsibility + key methods + important notes
Included the shared DTOs used by the web↔backend API and the LLM pipeline (LlmPrompt, LlmResult, PriorityDecision)
Tell me the next section to generate: “State Diagrams” or “Flow Chart”?
# State Diagrams

## Overview
These state diagrams describe the MVP runtime behavior for (1) the web inbox UI and (2) the backend LLM-based scoring pipeline.

## Web UI: Inbox Scoring Lifecycle
```mermaid
stateDiagram-v2
	[*] --> SignedOut

	SignedOut --> Authenticating: user clicks Sign in
	Authenticating --> SignedIn: token acquired
	Authenticating --> AuthFailed: auth error
	AuthFailed --> SignedOut: user retries/cancels

	SignedIn --> LoadingInbox: load message list
	LoadingInbox --> InboxReady: messages loaded
	LoadingInbox --> InboxLoadFailed: Graph/API error
	InboxLoadFailed --> LoadingInbox: retry

	InboxReady --> ScoringQueued: for each message, request /api/score
	ScoringQueued --> ScoringInProgress
	ScoringInProgress --> ScoredHigh: response priorityFlag=High
	ScoringInProgress --> ScoredNormal: response priorityFlag=Normal
	ScoringInProgress --> ScoreFailed: timeout/5xx/invalid response

	ScoreFailed --> ScoringQueued: retry (optional)
	ScoredHigh --> InboxReady: render badge + reasons
	ScoredNormal --> InboxReady: render no badge / normal

	InboxReady --> SignedOut: user signs out
```

## Backend: LLM Scoring Request Lifecycle
```mermaid
stateDiagram-v2
	[*] --> RequestReceived

	RequestReceived --> ValidatingRequest: schema/auth checks
	ValidatingRequest --> Rejected: invalid/unauthorized
	ValidatingRequest --> CacheLookup

	CacheLookup --> CacheHit: cached ScoreResponse
	CacheLookup --> CacheMiss
	CacheHit --> Responding

	CacheMiss --> LoadPreferences
	LoadPreferences --> ExtractFeatures
	ExtractFeatures --> BuildPrompt

	BuildPrompt --> CallLLM
	CallLLM --> LlmTimeout: timeout
	CallLLM --> LlmError: provider error
	CallLLM --> LlmReturned

	LlmReturned --> ParseModelOutput
	ParseModelOutput --> ValidationFailed: not schema-conformant
	ParseModelOutput --> DecisionReady

	ValidationFailed --> FallbackDecision
	LlmTimeout --> FallbackDecision
	LlmError --> FallbackDecision

	FallbackDecision --> Responding
	DecisionReady --> WriteCache
	WriteCache --> Responding

	Responding --> [*]
	Rejected --> [*]
```

## Notes
- The backend should treat LLM output as untrusted until parsed + validated.
- The fallback path should still return a safe `priorityFlag` and a short reason (e.g., “Unable to score right now”).
## Rationale 
Ichose this approach to keep the frontend and backend as separate as possible to ensure maintainability. Ialso use a fallback mechanism to ensure the system returns a safe priority and prevents serious errors.
## Chat Log 
generate # State Diagrams

I’ll insert Mermaid state diagrams under # State Diagrams (web UI lifecycle + backend LLM scoring lifecycle) and keep everything else unchanged.

Added the “State Diagrams” section content in dev_spec_doc1.md.

Web UI state diagram: sign-in → load inbox → per-message scoring → render badge/reasons (with retry/error states)
Backend state diagram: validate → cache → prefs/features → prompt → LLM call → parse/validate → fallback or cache+respond
Notes emphasize “LLM output is untrusted until validated” and a safe fallback behavior
Next section to generate: “Flow Chart”?

# Flow Chart

## Overview
This flow chart describes the MVP end-to-end runtime flow for the selected architecture (Option A: Web App + Backend + LLM scoring). It focuses on the critical path and the minimum required failure handling.

## End-to-End Flow (Option A: LLM Scoring)
```mermaid
flowchart TD
	A[User opens web app inbox] --> B{Signed in?}
	B -- No --> C[OAuth sign-in via Entra ID]
	C --> D{Token acquired?}
	D -- No --> E[Show auth error + allow retry]
	D -- Yes --> F[Call Microsoft Graph: list inbox messages]
	B -- Yes --> F

	F --> G{Graph success?}
	G -- No --> H[Show load error + retry]
	G -- Yes --> I[For each message: fetch body main text]

	I --> J[Build ScoreRequest: metadata + bodyText]
	J --> K[POST /api/score to backend]

	K --> L{Backend response valid?}
	L -- No --> M[Mark as Normal + reason: Unable to score]
	L -- Yes --> N{priorityFlag}
	N -- High --> O[Render High badge + reasons]
	N -- Normal --> P[Render Normal (no badge) + optional reasons]

	O --> Q[Inbox ready]
	P --> Q
	M --> Q
```

## Step-by-step (MVP)
1) User opens the inbox page.
2) Web app signs in via Entra ID (if not already signed in) and obtains an access token.
3) Web app calls Microsoft Graph to load message metadata.
4) Web app fetches the email body main text for each message (MVP uses full main text).
5) Web app sends `ScoreRequest` to backend `/api/score` (metadata + `bodyText`).
6) Backend validates the request, checks cache, loads user prefs, extracts features, builds a prompt, calls LLM, parses + validates output.
7) Backend returns `ScoreResponse` with `priorityFlag` and `reasons[]`.
8) Web app renders the priority badge/label and short reasons in the inbox UI.

## Failure Handling (MVP, Explicit)
- **Auth failure:** show error + allow retry; do not load inbox without token.
- **Graph failure:** show load error + allow retry; do not request scoring without message data.
- **Backend/LLM failure or invalid output:** backend returns a safe fallback `ScoreResponse` (e.g., `priorityFlag=Normal` with `reasons=["Unable to score right now"]`). The web UI must not crash.
## Rationale:
I found that VS Code provides an option feature. I required it to ask for my opinion before generating content. First, it asked about the scope of the flow chart. I required it to put all the information into one chart so that it would be more intuitive. Second, it asked whether it should generate only the current solution. The answer was the current solution. Finally, it asked whether the chart should be very detailed or focused on the MVP.
## Chat Log:
User: generate Flow Chat, if you have option, ask me before generate
LLM:I can generate the # Flow Chart section in a few different (non-vague) ways. Before I write it, tell me which option you want so the doc stays consistent with your chosen architecture.
Which flow chart(s) should I generate under # Flow Chart?
End-to-end (Web → Graph → Backend → Decision → UI)
- One chart showing the whole user-visible runtime flow
Should the flow chart cover multiple architecture options (A/B/C) or only the selected one?
Only selected Option A (LLM scoring)
- Simplest, matches current MVP direction
How detailed should the flow chart be?
MVP
- ~10–15 steps; just key decisions and error handling
Asked 3 questions (Scope, Options, Detail)

Which flow chart(s) should I generate under # Flow Chart?
End-to-end (Web → Graph → Backend → Decision → UI)
- One chart showing the whole user-visible runtime flow
Should the flow chart cover multiple architecture options (A/B/C) or only the selected one?
Only selected Option A (LLM scoring)
- Simplest, matches current MVP direction
How detailed should the flow chart be?
MVP
- ~10–15 steps; just key decisions and error handling
Generating the Flow Chart section now (end-to-end, Option A only, MVP detail), inserted under the existing # Flow Chart heading.

Added the # Flow Chart content in dev_spec_doc1.md as you chose:

End-to-end flow only
Option A only (Web + Backend + LLM scoring)
MVP detail level
It includes a Mermaid flowchart, a short step-by-step list, and explicit MVP failure handling behavior.

Want me to generate # Development Risks and Failures next (and if so, do you want options A/B/C covered there too)?
# Development Risks and Failures

## Scope
This section covers development risks for the selected MVP architecture (Option A: Web App + Backend + LLM scoring using full email body main text).

## Risk Register (MVP)
| Risk | Impact | Likelihood | Failure Mode / Symptom | Mitigation (MVP) |
|---|---:|---:|---|---|
| Entra ID / OAuth misconfiguration | H | M | Users cannot sign in; tokens missing scopes; Graph calls fail 401/403 | Start with one tenant + one app registration; document required scopes; add clear auth error UI; log correlation IDs |
| Microsoft Graph throttling / rate limits | M | M | 429 responses; slow inbox load; partial message list | Implement basic retry with backoff; reduce calls by batching/paging; cache message bodies short-term; defer body fetch until needed |
| Fetching full email body is slow/expensive | M | M | Inbox feels laggy; too many network calls | Fetch metadata first; fetch body in parallel with a cap; show loading indicators; cache bodies per session |
| Backend latency (LLM call) | H | M | Bad UX (delayed badges); timeouts | Add server timeout budget; return fallback quickly on timeout; cache ScoreResponse by messageId; keep reasons short |
| LLM output not valid JSON / schema | H | M | Parser fails; missing fields; reasons too long | Enforce output schema in prompt; parse defensively; validate and apply `fallback()`; keep strict allowed values (`High`/`Normal`) |
| LLM inconsistent decisions (non-determinism) | M | M | Same email gets different scores across runs | Cache responses by messageId; fix temperature low; include stable prompt; record model/version for debugging |
| Privacy risk: sending email body text to backend/LLM provider | H | M | Compliance concerns; user distrust | Minimize transmitted content (no attachments); redact obvious PII where feasible; restrict logs (do not log bodyText); document data handling in `# Security and Privacy` |
| Secret/API key leakage | H | L | LLM key exposed in client bundle or logs | Keep provider keys server-side only; use environment variables; never return secrets to web client |
| Prompt injection / malicious content in email body | H | M | Model follows attacker instructions; returns unsafe output | Treat email body as untrusted; use strong system instructions; constrain output schema; ignore any instructions in email text; validate output |
| Incorrect / misleading “reasons[]” explanations | M | M | Reasons don’t match flagged state; user loses trust | Require 1–3 concise reasons; validate reason length; allow generic fallback reason; optionally include rule-based reasons for obvious signals |
| Cache key mistakes / stale cache | M | M | Wrong score shown for a different message; outdated reasons | Cache by a stable key (at minimum `messageId`); for MVP with shared API key, include the API key (or another server-known namespace) in the cache key; include TTL |
| Backend auth/authorization gap | H | M | Unauthorized clients call scoring API; malicious spam requests drain quota | Validate `X-API-Key`; restrict network access (VPN/campus/IP allowlist) for MVP; rate-limit; plan upgrade to Entra token validation for per-user identity |
| Error handling gaps in UI | M | M | UI crashes or renders broken badges | Always render a default state; treat missing response as `Normal`; show non-blocking error banner |

## Acceptance Criteria (Risk Controls)
- System continues to render inbox even if Graph, backend, or LLM fails.
- Backend always returns a schema-valid `ScoreResponse` (using fallback when necessary).
- No email `bodyText` is written to persistent logs by default.
## Rationale:
This time, it asked me three questions again, but they were all about whether the generated content should be formal or informal. I required it to be more formal so that it would meet professional standards. The generated content had no problems and covered multiple aspects that could be considered.
## Chat Log:
generate # Development Risks and Failures

I’ll add content under # Development Risks and Failures without changing other sections; quick question first because there are multiple valid ways to scope risks (selected Option A only vs all A/B/C).

Asked 3 questions (Coverage, Format, Rating)

For # Development Risks and Failures, should I cover only the selected architecture (Option A: LLM scoring) or include Option B/C risks too?
Only Option A (LLM scoring)
- Shortest; matches current selected approach
How do you want the risks presented?
Risk table (Risk / Impact / Likelihood / Mitigation)
- Most explicit and scannable
Do you want explicit severity ratings?
Yes: H/M/L for impact and likelihood
- More explicit for planning
Inserted # Development Risks and Failures content into dev_spec_doc1.md as you chose:

Coverage: Option A only (LLM scoring, full email body)
Format: risk register table
Ratings: explicit H/M/L for impact + likelihood
Next section is # Technology Stack. If you want options there too, I can ask “choose 1 stack” (e.g., Next.js full-stack vs React+Fastify vs React+FastAPI) before generating.

# Technology Stack

## Selected Stack (Explicit)
- **Frontend:** React (Vite) + TypeScript
- **Backend:** Python + FastAPI
- **Hosting:** NJIT HPC cluster server (self-hosted deployment)
- **LLM Provider:** Google Gemini (backend calls Gemini API)
- **Persistence (MVP):** No persistent database (in-memory cache only)

## Frontend (Web UI)
- **Runtime:** Modern browser
- **Framework:** React
- **Build tool:** Vite
- **Language:** TypeScript
- **HTTP client:** `fetch` (MVP)
- **Auth (Graph access):** Microsoft Identity Platform (Entra ID) OAuth with PKCE in the browser

## Backend (Scoring API)
- **Language:** Python
- **Framework:** FastAPI
- **ASGI server:** Uvicorn
- **API style:** REST (JSON) over HTTPS
- **Core responsibilities (MVP):**
	- Validate `ScoreRequest`
	- Cache `ScoreResponse` in memory (per-process)
	- Build prompt + call Gemini
	- Parse + validate model output; apply fallback response on error

## External Integrations
- **Microsoft Graph API:** fetch inbox metadata + full email body main text via delegated user auth.
- **Google Gemini API:** called from backend only (never from the browser); API key stored as server-side environment variable.

## Data & Caching (MVP)
- **Cache:** in-memory TTL cache inside the FastAPI process.
- **Explicit trade-off:** cache is lost on process restart; acceptable for MVP.

## Deployment (NJIT HPC)
- **Frontend build artifact:** static assets produced by Vite (`dist/`).
- **Backend service:** FastAPI started via Uvicorn.
- **TLS / routing:** use HPC-provided reverse proxy if available; otherwise run behind a campus gateway that terminates TLS.

## Configuration (Environment Variables)
- `GEMINI_API_KEY`
- `GRAPH_CLIENT_ID`
- `GRAPH_TENANT_ID` (or equivalent tenant configuration)
- `BACKEND_BASE_URL`
- `CACHE_TTL_SECONDS`

## Observability (MVP)
- **Logging:** structured backend logs; do not log email `bodyText`.
- **Tracing:** generate a `requestId` per scoring request for backend logs (not returned to the client in MVP).
## Rationale
This time, it asked which framework I wanted to use. Since our backend needs to call an LLM and I am more familiar with using Python for LLM integration, I chose React (Vite) + Python (FastAPI). Then I decided to deploy it on the NJIT HPC because I already have experience deploying websites there. Finally, it asked which LLM I should use. I chose Google Gemini because Google funded one of my research projects and provided us with credits.
## Chat Log

I’ll generate the # Technology Stack section next, but there are real implementation choices here (frontend/backend hosting, DB/cache, LLM provider), so I’ll ask you to pick explicitly before I write it.

Asked 4 questions (Stack, Host, Data, LLM)

Which core stack should I document for the MVP? (Choose 1)
Stack 3: React (Vite) + Python (FastAPI)
- Python backend; frontend separate
Where will you deploy the backend? (Choose 1)
NJIT HPC cluster server
Do you want persistence for MVP beyond in-memory cache? (Choose 1)
No persistent DB (in-memory cache only)
- Fastest MVP; cache lost on restart
Which LLM provider should the backend target? (Choose 1)
GOOGLE GEMINI
Got it: React+Vite frontend, FastAPI backend on NJIT HPC, in-memory cache only, and Google Gemini as the LLM. Next I’ll patch # Technology Stack with these exact choices and explicit versions/components.

Patch didn’t apply because that part of the file changed (context mismatch). I’m going to locate the exact # Technology Stack block and re-apply the insertion with the correct surrounding text.

Generated # Technology Stack in dev_spec_doc1.md using your selections:

React (Vite) + TypeScript frontend
Python FastAPI backend on NJIT HPC
Google Gemini for LLM scoring
In-memory TTL cache only (no DB)
Next section is # APIs. If you want options there (endpoint shape, auth method, batching vs per-message), tell me and I’ll ask before generating.
# APIs

## Overview
This section defines the MVP API surface for the system:
- **Internal API:** Web UI → Backend Scoring API (FastAPI on NJIT HPC)
- **External APIs:** Microsoft Graph (email retrieval) and Google Gemini (LLM scoring)

## Backend Scoring API (Internal)

### Authentication (MVP, Explicit)
- The backend requires a shared API key.
- The web UI must send header: `X-API-Key: <key>`
- The backend rejects missing/invalid keys with `401 Unauthorized`.

### Common Conventions
- **Base URL:** `https://<your-host>/api`
- **Content-Type:** `application/json`
- **Request IDs:** backend generates a server-side correlation ID for logs (not returned to client in MVP).

### `POST /api/score`
Scores one email message and returns a priority flag + short reasons.

**Headers**
- `Content-Type: application/json`
- `X-API-Key: <key>`

**Request body (JSON)**
```json
{
	"messageId": "string",
	"from": "string",
	"subject": "string",
	"receivedAt": "string",
	"importance": "string",
	"bodyText": "string"
}
```

**Response (200 OK, JSON)**
```json
{
	"messageId": "string",
	"priorityFlag": "High",
	"reasons": ["string", "string"]
}
```

**Response rules (MVP, Explicit)**
- `priorityFlag` must be exactly one of: `High`, `Normal`.
- `reasons` must contain 1–3 short strings.
- The backend must return a schema-valid response even on LLM failure (fallback path).

**Error responses (JSON)**
The backend returns:
- `400 Bad Request` for invalid JSON or missing fields
- `401 Unauthorized` for missing/invalid `X-API-Key`
- `429 Too Many Requests` if the backend rate-limits requests
- `500 Internal Server Error` only for unexpected failures (should be rare; prefer fallback response)

Error body shape:
```json
{
	"error": "string",
	"details": "string"
}
```

### `GET /api/health`
Health check endpoint for deployment validation.

**Response (200 OK, JSON)**
```json
{ "status": "ok" }
```

## Microsoft Graph API (External Dependency)
Used by the web UI to fetch:
- Inbox message metadata (sender, subject, timestamps, importance)
- Full email body main text

**Auth model (MVP):** delegated user auth via Entra ID OAuth (PKCE) in the browser.

## Google Gemini API (External Dependency)
Used by the backend scoring service to compute `priorityFlag` and `reasons[]`.

**Auth model (MVP):** API key stored server-side (environment variable `GEMINI_API_KEY`).
- The Gemini API key must never be exposed to the browser.
## Rationale
I chose `POST /api/score` per message as the simplest MVP to ensure development convenience. Iuse a shared API key to maintain a certain level of security without making the system too complex.
## Chat Log
I can generate the # APIs section, but there are a few concrete API design choices (batching and backend auth) that will change the endpoint list and request/response schemas—so I’ll ask you to pick before I write it.

Asked 4 questions (Scoring, Auth, BasePath, Debug)

How should the web app call the backend scoring API?
API 1: Single message scoring
- `POST /api/score` per message; simplest MVP
How should the backend API be protected? (MVP on NJIT HPC)
Auth 2: Shared API key
- Frontend sends `X-API-Key`; simple but less ideal
What base path should the backend use?
`/api` prefix
- e.g., `POST /api/score`
Should the API support a debug mode that returns `model`/`requestId`/`score`?
No
- Always return only required fields
I’m going to insert the concrete backend + external API definitions under # APIs next, matching your choices (single-message scoring, /api prefix, X-API-Key auth, no debug fields).

Added the # APIs section in dev_spec_doc1.md based on your selections:

Internal backend API: POST /api/score (single message), GET /api/health
Auth: X-API-Key required
No debug fields returned in MVP (only messageId, priorityFlag, reasons[])
External dependencies documented: Microsoft Graph (frontend, PKCE) and Google Gemini (backend, server-side API key)
Next is # Public Interfaces. If you want options there (e.g., “public interface = REST only” vs “REST + typed client SDK”), tell me and I’ll ask before generating.
# Public Interfaces

## Overview
This section defines all public interfaces that other components depend on:
- **Web UI (public entrypoints):** browser routes/pages
- **Backend (public service interface):** REST endpoints exposed by FastAPI
- **External dependencies (public interfaces outside our control):** Microsoft Graph + Google Gemini

## Web UI Routes (Public Entry Points)
- `GET /` — Inbox/triage page (loads messages, triggers scoring)
- `GET /login` — Sign-in entrypoint (redirects to Entra ID)
- `GET /logout` — Sign-out (clears local session state)

Notes (MVP):
- These are user-facing entrypoints; they are “public” in the sense that any user with the URL can access them.
- Access to email content still depends on successful Entra ID sign-in and Graph permissions.

## Backend REST Interface (FastAPI)

### Base
- **Base URL:** `https://<your-host>/api`
- **Auth:** `X-API-Key: <key>` required on all endpoints
- **Media type:** `application/json`

### Endpoint Summary (OpenAPI-aligned)

#### `POST /api/score`
- **Purpose:** Score one message and return a priority decision.
- **Consumes:** `application/json`
- **Produces:** `application/json`

Request schema: `ScoreRequest`
```json
{
	"messageId": "string",
	"from": "string",
	"subject": "string",
	"receivedAt": "string",
	"importance": "string",
	"bodyText": "string"
}
```

Response schema: `ScoreResponse`
```json
{
	"messageId": "string",
	"priorityFlag": "High",
	"reasons": ["string"]
}
```

Error schema: `ErrorResponse`
```json
{
	"error": "string",
	"details": "string"
}
```

Status codes:
- `200` — Success
- `400` — Invalid request
- `401` — Missing/invalid API key
- `429` — Rate limited
- `500` — Unexpected server error (MVP should prefer fallback response over 500)

#### `GET /api/health`
- **Purpose:** Health check.
- **Produces:** `application/json`

Response:
```json
{ "status": "ok" }
```

## External Public Interfaces (Dependencies)

### Microsoft Graph API
- **Used by:** Web UI
- **Purpose:** Fetch inbox message metadata and full email body main text.
- **Auth:** Entra ID delegated OAuth (PKCE in browser)
- **Key contract:** message metadata + body main text must be retrievable for scoring.

### Google Gemini API
- **Used by:** Backend
- **Purpose:** Convert email content into a `priorityFlag` + `reasons[]` decision.
- **Auth:** server-side API key (`GEMINI_API_KEY`)
- **Key contract:** backend validates and normalizes model output before returning a response.

## Non-Interfaces (Explicitly Out of Scope for MVP)
- No public SDK is published; frontend calls backend using `fetch`.
- No webhook/subscription interface for push notifications.
## Rationale
I chose three simple frontend routes and two backend endpoints as the minimal public interface to ensure development convenience. I also explicitly required it to document external dependencies in order to clearly describe failure handling.
## Chat Log

I’ll generate # Public Interfaces, but first I need your selection on what counts as “public” here (backend REST only vs also frontend routes + external Graph/Gemini), and whether to include an explicit OpenAPI contract.

Asked 3 questions (Scope, Contract, Clients)

What should be covered under # Public Interfaces?
All of the above
- Backend + frontend routes + Graph + Gemini
Should I include an explicit interface contract format?
OpenAPI summary (endpoints + schemas)
- Text summary aligned with OpenAPI; no huge spec dump
Should I document a generated client SDK as part of the public interface?
No SDK (MVP)
- Frontend calls with fetch; keep simple
Patch failed due to a small context mismatch; I’ll re-read the exact lines around # Public Interfaces and re-apply the insertion with the correct surrounding text.

Generated # Public Interfaces in dev_spec_doc1.md with what you selected:

Includes Web UI routes, Backend REST interface (OpenAPI-aligned summary), and external dependencies (Microsoft Graph + Google Gemini)
Explicitly states no SDK for MVP
Next section is # Data Schemas. If you want options there (e.g., strict enums vs flexible strings; JSON Schema vs example-only), tell me and I’ll ask before generating.
# Data Schemas

## Overview
This section defines the canonical data contracts used in the MVP. These schemas are written as **strict JSON Schema** (no extra fields allowed).

## Conventions (MVP, Explicit)
- **JSON Schema:** draft 2020-12
- **Timestamps:** `receivedAt` is an RFC 3339 / ISO 8601 date-time string (example: `2026-02-13T18:22:10Z`).
- **Strictness:** `additionalProperties: false` for all schemas.
- **Body text limit:** `bodyText` max length is **16000 characters** (backend truncates if longer).
- **Explainability limit:** `reasons` length is **1–3**.

## `ScoreRequest` (Web → Backend)
```json
{
	"$schema": "https://json-schema.org/draft/2020-12/schema",
	"$id": "ScoreRequest",
	"type": "object",
	"additionalProperties": false,
	"required": ["messageId", "from", "subject", "receivedAt", "importance", "bodyText"],
	"properties": {
		"messageId": { "type": "string", "minLength": 1 },
		"from": { "type": "string", "minLength": 1 },
		"subject": { "type": "string" },
		"receivedAt": { "type": "string", "format": "date-time" },
		"importance": { "type": "string", "minLength": 1 },
		"bodyText": { "type": "string", "minLength": 1, "maxLength": 16000 }
	}
}
```

## `ScoreResponse` (Backend → Web)
```json
{
	"$schema": "https://json-schema.org/draft/2020-12/schema",
	"$id": "ScoreResponse",
	"type": "object",
	"additionalProperties": false,
	"required": ["messageId", "priorityFlag", "reasons"],
	"properties": {
		"messageId": { "type": "string", "minLength": 1 },
		"priorityFlag": { "type": "string", "enum": ["High", "Normal"] },
		"reasons": {
			"type": "array",
			"minItems": 1,
			"maxItems": 3,
			"items": { "type": "string", "minLength": 1, "maxLength": 160 }
		}
	}
}
```

## `ErrorResponse` (Backend → Web)
```json
{
	"$schema": "https://json-schema.org/draft/2020-12/schema",
	"$id": "ErrorResponse",
	"type": "object",
	"additionalProperties": false,
	"required": ["error", "details"],
	"properties": {
		"error": { "type": "string", "minLength": 1 },
		"details": { "type": "string" }
	}
}
```

## `PriorityDecision` (Internal Domain DTO)
This is the normalized internal representation used after parsing/validating the LLM output.

```json
{
	"$schema": "https://json-schema.org/draft/2020-12/schema",
	"$id": "PriorityDecision",
	"type": "object",
	"additionalProperties": false,
	"required": ["priorityFlag", "reasons"],
	"properties": {
		"priorityFlag": { "type": "string", "enum": ["High", "Normal"] },
		"reasons": {
			"type": "array",
			"minItems": 1,
			"maxItems": 3,
			"items": { "type": "string", "minLength": 1, "maxLength": 160 }
		}
	}
}
```

## LLM Output Schema (Backend expects from Gemini)
The backend instructs the model to return JSON matching this schema. The backend treats the model output as untrusted until validated.

```json
{
	"$schema": "https://json-schema.org/draft/2020-12/schema",
	"$id": "LlmPriorityDecision",
	"type": "object",
	"additionalProperties": false,
	"required": ["priorityFlag", "reasons"],
	"properties": {
		"priorityFlag": { "type": "string", "enum": ["High", "Normal"] },
		"reasons": {
			"type": "array",
			"minItems": 1,
			"maxItems": 3,
			"items": { "type": "string", "minLength": 1, "maxLength": 160 }
		}
	}
}
```

## Validation Rules (MVP, Explicit)
- If the model output fails validation, the backend returns a fallback `ScoreResponse`:
	- `priorityFlag = "Normal"`
	- `reasons = ["Unable to score right now"]`
## Rationale
I chose JSON format to store the data because it is more general and I am more familiar with it. For the MVP, I selected 16,000 characters as a balanced default. I also chose 1–3 reasons, which are generally sufficient.
## Chat Log

generate # Data Schemas

I can generate # Data Schemas, but there are a few concrete schema choices (format + strictness + bodyText size limit) that affect the final definitions—so I’ll ask you to pick before I write it.

Asked 4 questions (Format, Strict, BodyLimit, Reasons)

What format should the Data Schemas be written in?
JSON Schema blocks (recommended)
- Concrete, language-agnostic; can be used for validation
How strict should the schemas be?
Strict
- `additionalProperties: false`; enums enforced; required fields explicit
Max size for `bodyText` sent to backend (MVP)?
16,000 chars
- Balanced default
Max number of `reasons[]` in `ScoreResponse`?
1–3 reasons
- Matches earlier MVP spec
Generated # Data Schemas in dev_spec_doc1.md using your choices:

Format: strict JSON Schema (draft 2020-12)
Strictness: additionalProperties: false
Limits: bodyText max 16000 chars; reasons[] 1–3
Included schemas for ScoreRequest, ScoreResponse, ErrorResponse, internal PriorityDecision, and the expected LLM output schema (Gemini)
Next section is # Security and Privacy. If you want options there (e.g., API-key-only vs JWT, logging redaction level, retention policy), tell me and I’ll ask before generating.
# Security and Privacy

## Overview
This section defines the MVP security and privacy requirements for a standalone web app that:
- Uses Entra ID OAuth (PKCE) to access Microsoft Graph in the browser.
- Sends **full email body main text** to a backend scoring API.
- Calls Google Gemini from the backend.

Security/privacy goals (MVP):
- Prevent unauthorized access to the backend scoring API.
- Prevent leakage of secrets (Gemini API key, internal API key).
- Minimize exposure of email content (especially `bodyText`) in logs and storage.
- Treat email content and LLM output as untrusted input.

## Data Classification (MVP)
- **Email content (`bodyText`, `subject`, `from`):** sensitive user data.
- **Access tokens (Graph):** highly sensitive secrets; must not be logged.
- **Backend secrets (`GEMINI_API_KEY`, backend `X-API-Key` value):** highly sensitive secrets.
- **Derived output (`priorityFlag`, `reasons[]`):** lower sensitivity, but may still reveal information about the email.

## Authentication & Authorization

### Web UI → Backend (MVP: Selected)
**Selected approach:** shared API key
- Web UI sends `X-API-Key: <key>` on backend calls.
- Backend rejects missing/invalid keys with `401`.

**Security notes (explicit):**
- The API key must be treated as a secret.
- If the web UI is purely static and publicly reachable, embedding a shared API key in the browser is not secure. For MVP, this is acceptable only if deployment is restricted (see “Network Controls”).

### Upgrade Options 
- Web UI sends an Entra ID access token / ID token to backend.
- Backend validates token signature + issuer + audience, and derives `userId` from token claims.
- Pros: no shared secret in browser; per-user identity.
- Cons: more setup (JWKS validation, app registration alignment).

## Network Controls (MVP)
Because the MVP uses a shared `X-API-Key`, apply at least one of the following controls:
- Restrict backend access to specific origins and enforce strict CORS (see below).
- Restrict backend access by IP/network (NJIT VPN / campus network / reverse proxy ACL).
- Do not expose the scoring API to the public internet if not required.

## Transport Security (MVP)
- All traffic must use HTTPS (TLS) end-to-end:
	- Browser ↔ Microsoft Graph: HTTPS
	- Browser ↔ Backend: HTTPS
	- Backend ↔ Gemini: HTTPS
- Do not allow plaintext HTTP in production.

## Secrets Management (MVP)
- `GEMINI_API_KEY` must exist only on the backend as an environment variable.
- Backend `X-API-Key` secret must be stored server-side (env var or HPC secret mechanism).
- Never commit secrets into the repository.
- Never return any secret to the web UI.

## Data Minimization & Handling

### Email Body Handling
- Backend accepts `bodyText` up to 16,000 characters (truncate beyond this limit).
- Do not send attachments to the backend/LLM in MVP.
- Do not persist `bodyText` to disk (no database in MVP).

### Logging Policy (MVP: Required)
- Backend logs must **never** include:
	- `bodyText`
	- Graph access tokens
	- Gemini API key
	- `X-API-Key` header value
- Allowed logging fields:
	- `requestId` (server-generated)
	- `messageId` (if not considered sensitive in your environment)
	- response status code
	- latency metrics (Graph fetch time, backend time, LLM time)
	- error codes (without sensitive payload)

### Retention (MVP: Required)
- In-memory cache only; cache is lost on restart.
- Cache TTL must be configurable (e.g., `CACHE_TTL_SECONDS`).
- Do not store email bodies in cache; cache only the final `ScoreResponse` keyed by `(apiKey, messageId)` for MVP.
	- Upgrade path: when the backend validates Entra ID tokens, key by `(userId, messageId)` derived from token claims.

## Input Safety (Email Content is Untrusted)
- Treat the email body as untrusted text.
- Prompt injection defense requirements:
	- System instructions explicitly state: ignore any instructions contained in the email body.
	- Output must be strict JSON matching the documented schema.
- Backend must validate the LLM output against schema and apply fallback on failure.

## LLM Provider Privacy (Gemini)
- The backend must not send more content than necessary:
	- include only `subject`, minimal metadata, and truncated `bodyText`.
- Do not include user secrets or tokens in prompts.
- Treat provider responses as untrusted until validated.

## CORS (MVP)
- Backend must implement CORS allow-listing.
- Allowed origin list must be explicit (no `*` in production).
- Allow only required methods/headers (`POST`, `GET`; `Content-Type`, `X-API-Key`).

## Abuse Prevention (MVP)
- Backend rate limits requests per source (IP or API key) to protect Gemini quota.
- Backend should return `429` when throttling.

## Privacy Notice (MVP)
The UI must display a clear statement that:
- The app reads email metadata and the email main body text to compute a priority flag.
- Email text is sent to the backend and then to Gemini for scoring.
- The system does not persist email body text in a database for MVP.
## Rationale
I chose to use shared API key authentication to protect the backend. I decided to enforce HTTPS everywhere and implement strict logging rules.
## Chat Log:

generate these two

Summarized conversation history

I’m going to (1) re-open the current dev_spec_doc1.md around # Security and Privacy / # Risks to Completion, then (2) insert fully-written Markdown content under those two headings (keeping the existing # ... headings unchanged).

Added both sections to dev_spec_doc1.md, directly under the existing headings, without introducing any new top-level # headings.

What I generated

Security and Privacy: MVP requirements for auth (X-API-Key), network controls, HTTPS, secrets handling, logging redaction rules (explicitly “never log bodyText”), retention/caching rules, prompt-injection handling, Gemini privacy constraints, CORS, rate limiting, and a clear UI privacy notice. Also includes explicit upgrade options (token validation / backend JWT) as “choose later”.
Risks to Completion: delivery-focused risk register (Impact/Likelihood H/M/L) + MVP completion criteria + explicit contingency scope-cuts if time is short.
Where

dev_spec_doc1.md
If you want, I can now generate the same two sections in dev_spec_doc3.md instead (your active editor file), but I didn’t change it because its content/layout differs and your headings for these sections are currently in dev_spec_doc1.md.
# Risks to Completion

## Overview
This section covers schedule and delivery risks (distinct from runtime security/engineering risks). Ratings use:
- **Impact:** H/M/L (how badly it affects delivery)
- **Likelihood:** H/M/L (how likely it is to occur)

## Risk Register (Delivery)
| Risk | Impact | Likelihood | Delivery Symptom | Mitigation / Plan |
|---|---:|---:|---|---|
| Entra ID / Graph permissions approval delays | H | M | Cannot obtain required Graph scopes; inbox cannot load in demo | Start app registration early; document scopes; prepare a demo tenant/user; keep a minimal scope list for MVP |
| Microsoft Graph email body retrieval complexity | H | M | Body missing/HTML-only; inconsistent parsing; time lost debugging | Prototype `body` retrieval early; define “main text” extraction rule (strip HTML); add a fallback when body is unavailable |
| Graph throttling during testing (429) | M | M | Testing blocked; inconsistent results | Implement retry/backoff early; reduce calls (cache metadata/bodies per session); test with small inbox |
| Gemini quota/credits limits or provider downtime | H | M | Scoring endpoint fails; cannot show “High/Normal” reliably | Add strict timeout + fallback response; cache results; prepare a “mock scoring” mode for local testing (not for production) |
| Backend deployment friction on NJIT HPC | H | M | Service not reachable; TLS/reverse proxy issues; port restrictions | Confirm hosting constraints early (ports, proxy, TLS); document deployment steps; keep backend simple (single FastAPI app) |
| CORS / browser-network issues | M | M | Frontend cannot call backend from browser | Configure CORS allow-list early; test with deployed URLs; keep headers minimal |
| Shared API key approach hard to secure in browser | H | M | Security review concerns; key leakage risk | Restrict backend network access for MVP; document limitations; plan upgrade to token validation (see Security section) |
| Performance: per-message scoring too slow | M | M | Inbox feels laggy; demo looks unresponsive | Parallelize with a cap; cache `ScoreResponse`; show UI loading state; keep reasons 1–3 |
| Integration drift between APIs and schemas | M | M | Frontend/backend mismatch; repeated rework | Treat `# Data Schemas` as canonical; validate requests/responses in backend; generate OpenAPI from FastAPI models |
| Limited time for testing and edge cases | M | H | Demo breaks on odd emails or network failures | Add basic happy-path + failure-path tests; implement fallback behavior everywhere; keep MVP scope small |

## Completion Criteria (MVP)
- Deployed web UI can sign in with Entra ID and list inbox messages.
- For at least a small set of messages, the system fetches body main text and returns a `priorityFlag` + `reasons[]` via backend.
- On failures (Graph/LLM/backend), the UI still renders and messages default to `Normal` with a safe reason.

## Contingency Plan (If Time Runs Short)
Explicit “scope cuts” that still preserve a working demo:
1) Score only when user clicks a message (instead of scoring every message in the list).
2) Score only the most recent N messages.
3) Use cached results only (skip LLM) for repeat runs during demo.
## Rationale
These risks may lead to unexpected issues during deployment and usage, so Iaddressed them in advance. High-risk items include Graph permission issues, Gemini quota limits, and HPC deployment problems. Ialso prepared anticipated mitigation measures for these risks.
## Chat Log:

generate these two

Summarized conversation history

I’m going to (1) re-open the current dev_spec_doc1.md around # Security and Privacy / # Risks to Completion, then (2) insert fully-written Markdown content under those two headings (keeping the existing # ... headings unchanged).

Added both sections to dev_spec_doc1.md, directly under the existing headings, without introducing any new top-level # headings.

What I generated

Security and Privacy: MVP requirements for auth (X-API-Key), network controls, HTTPS, secrets handling, logging redaction rules (explicitly “never log bodyText”), retention/caching rules, prompt-injection handling, Gemini privacy constraints, CORS, rate limiting, and a clear UI privacy notice. Also includes explicit upgrade options (token validation / backend JWT) as “choose later”.
Risks to Completion: delivery-focused risk register (Impact/Likelihood H/M/L) + MVP completion criteria + explicit contingency scope-cuts if time is short.
Where

dev_spec_doc1.md
If you want, I can now generate the same two sections in dev_spec_doc3.md instead (your active editor file), but I didn’t change it because its content/layout differs and your headings for these sections are currently in dev_spec_doc1.md.